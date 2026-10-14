import hashlib
import hmac
import io
import json
import re
from decimal import Decimal
from urllib.parse import quote

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.forms import GSTIN_RE, AddressForm
from accounts.models import Address
from accounts.states import STATE_NAMES
from shop.models import Product, SiteConfig

from . import notify
from .cart import Cart
from .models import Order, OrderItem
from .tax import compute


# ---------------------------------------------------------------- cart
def cart_view(request):
    cart = Cart(request)
    config = SiteConfig.get()
    totals = compute(cart.lines(), config.state_code, config)
    return render(request, "orders/cart.html", {"totals": totals})


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product.objects.active(), pk=pk)
    try:
        qty = max(1, int(request.POST.get("qty", 1)))
    except ValueError:
        qty = 1
    cart = Cart(request)
    current = int(cart.data.get(str(pk), 0))
    new_qty = min(current + qty, product.stock)
    if product.stock <= 0:
        messages.error(request, "Sorry, this saree is out of stock.")
        return redirect(product.get_absolute_url())
    cart.set(pk, new_qty)
    if new_qty < current + qty:
        messages.info(request, f"Only {product.stock} in stock. Quantity adjusted.")
    if request.POST.get("buy_now"):
        return redirect("checkout")
    messages.success(request, f"{product.name} added to your bag.")
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("cart")


@require_POST
def cart_update(request, pk):
    try:
        qty = int(request.POST.get("qty", 1))
    except ValueError:
        qty = 1
    Cart(request).set(pk, qty)
    return redirect("cart")


@require_POST
def cart_remove(request, pk):
    Cart(request).set(pk, 0)
    return redirect("cart")


# ------------------------------------------------------------ checkout
def available_methods(config, totals, user):
    methods = []
    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        methods.append(("razorpay", "Cards, UPI apps, netbanking", "Pay securely online with Razorpay."))
    if config.upi_id:
        methods.append(("upi", "Scan UPI QR", "Scan with any UPI app, then enter the UTR."))
    if config.bank_details:
        methods.append(("bank", "Bank transfer (NEFT / IMPS)", "Best for large wholesale orders."))
    has_wholesale = any(i["wholesale"] for i in totals["items"])
    if config.cod_enabled and not has_wholesale and totals["goods_total"] <= config.cod_max_amount:
        methods.append(("cod", f"Cash on delivery (+₹{config.cod_fee:,.0f})", f"Available up to ₹{config.cod_max_amount:,.0f}."))
    return methods


@login_required
def checkout(request):
    cart = Cart(request)
    config = SiteConfig.get()
    lines = cart.lines()
    if not lines:
        messages.info(request, "Your bag is empty.")
        return redirect("catalog")
    addresses = list(request.user.addresses.all())
    state = request.POST.get("state_code") if request.method == "POST" and request.POST.get("address_id") == "new" else None
    if request.method == "POST" and request.POST.get("address_id", "").isdigit():
        addr_obj = next((a for a in addresses if a.pk == int(request.POST["address_id"])), None)
        state = addr_obj.state_code if addr_obj else None
    state = state or (addresses[0].state_code if addresses else config.state_code)
    totals = compute(lines, state, config, request.POST.get("method"))
    methods = available_methods(config, totals, request.user)

    new_form = AddressForm(initial={"full_name": request.user.get_full_name(), "phone": request.user.phone})
    errors = []
    if request.method == "POST":
        method = request.POST.get("method")
        if method not in [m[0] for m in methods]:
            errors.append("Choose a payment method.")
        address = None
        aid = request.POST.get("address_id")
        if aid == "new" or not addresses:
            new_form = AddressForm(request.POST)
            if new_form.is_valid():
                address = new_form.save(commit=False)
                address.user = request.user
                address.is_default = not addresses
            else:
                errors.append("Please correct the delivery address.")
        elif aid and aid.isdigit():
            address = next((a for a in addresses if a.pk == int(aid)), None)
        if address is None and not errors:
            errors.append("Choose a delivery address.")
        gstin = (request.POST.get("gstin") or request.user.gstin or "").strip().upper()
        if gstin and not GSTIN_RE.match(gstin):
            errors.append("The GSTIN you entered is not valid.")
        if not errors:
            order = _create_order(request, cart, config, address, method, gstin)
            if order is None:
                return redirect("cart")
            return redirect(_next_step(order))
        for e in errors:
            messages.error(request, e)

    return render(request, "orders/checkout.html", {
        "addresses": addresses, "new_form": new_form, "totals": totals, "methods": methods,
        "selected_method": request.POST.get("method") or (methods[0][0] if methods else ""),
        "selected_address": request.POST.get("address_id") or (str(addresses[0].pk) if addresses else "new"),
        "gstin": request.POST.get("gstin") or request.user.gstin,
    })


@transaction.atomic
def _create_order(request, cart, config, address, method, gstin):
    # lock product rows so two buyers cannot take the last piece
    ids = [int(i) for i in cart.data.keys()]
    locked = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=ids, is_active=True)}
    lines = []
    for ln in cart.lines():
        p = locked.get(ln["product"].pk)
        if not p or p.stock < ln["qty"]:
            messages.error(request, f"{ln['product'].name} just went out of stock. Please review your bag.")
            return None
        ln["product"] = p
        lines.append(ln)
    if not lines:
        return None
    if address.pk is None:
        address.save()
    totals = compute(lines, address.state_code, config, method)
    user = request.user
    order = Order.objects.create(
        user=user, payment_method=method, is_wholesale=any(i["wholesale"] for i in totals["items"]),
        status=Order.PLACED if method == "cod" else Order.PENDING,
        ship_name=address.full_name, ship_phone=address.phone, ship_line1=address.line1, ship_line2=address.line2,
        ship_city=address.city, ship_state_code=address.state_code, ship_pincode=address.pincode,
        buyer_gstin=gstin, buyer_business=user.business_name,
        taxable_total=totals["taxable_total"], cgst=totals["cgst"], sgst=totals["sgst"], igst=totals["igst"],
        shipping_charge=totals["shipping"], cod_fee=totals["cod_fee"], total=totals["grand_total"],
        customer_note=(request.POST.get("note") or "")[:300],
    )
    for it in totals["items"]:
        p = it["product"]
        OrderItem.objects.create(
            order=order, product=p, name=p.name, sku=p.sku, hsn_code=p.hsn_code,
            image_url=p.image.url if p.image else "", qty=it["qty"], unit_price=it["unit_price"],
            is_wholesale_price=it["wholesale"], gst_rate=it["rate"], taxable_value=it["taxable"],
            gst_amount=it["gst"], line_total=it["gross"],
        )
        p.stock -= it["qty"]
        p.save(update_fields=["stock"])
    cart.clear()
    if method == "cod":
        notify.order_placed(order)
    return order


def _next_step(order):
    if order.payment_method == "razorpay":
        return f"/pay/{order.number}/razorpay/"
    if order.payment_method in ("upi", "bank"):
        return f"/pay/{order.number}/manual/"
    return f"/orders/{order.number}/thank-you/"


@login_required
def checkout_quote(request):
    """JSON price quote used by the checkout page when the address or payment method changes."""
    config = SiteConfig.get()
    state = request.GET.get("state", "")
    if state not in STATE_NAMES:
        state = config.state_code
    totals = compute(Cart(request).lines(), state, config, request.GET.get("method"))
    f = lambda v: f"{v:,.2f}"
    return JsonResponse({
        "goods": f(totals["goods_total"]), "shipping": "Free" if totals["shipping"] == 0 else "₹" + f(totals["shipping"]),
        "cod": f(totals["cod_fee"]), "has_cod": totals["cod_fee"] > 0, "gst": f(totals["gst_total"]), "total": f(totals["grand_total"]),
        "split": "IGST" if not totals["intra"] else "CGST + SGST",
    })


# ------------------------------------------------------------- orders
def _own_order(request, number):
    order = get_object_or_404(Order, number=number)
    if order.user_id != request.user.id and not request.user.is_staff:
        raise Http404
    return order


@login_required
def order_list(request):
    return render(request, "orders/order_list.html", {"orders": request.user.orders.prefetch_related("items")})


@login_required
def order_detail(request, number):
    order = _own_order(request, number)
    config = SiteConfig.get()
    return render(request, "orders/order_detail.html", {
        "order": order, "placed": request.GET.get("placed"),
        "bank_details": config.bank_details if order.payment_method == "bank" else "",
    })


@login_required
def order_thanks(request, number):
    order = _own_order(request, number)
    return render(request, "orders/thanks.html", {"order": order, "items": order.items.all()})


@login_required
@require_POST
def order_cancel(request, number):
    order = get_object_or_404(Order, number=number, user=request.user)
    if order.can_cancel:
        order.cancel()
        messages.success(request, f"Order {order.number} cancelled.")
    else:
        messages.error(request, "This order can no longer be cancelled online. Please call us.")
    return redirect("order_detail", number=number)


@login_required
def invoice(request, number):
    order = _own_order(request, number)
    if order.status in (Order.PENDING, Order.CANCELLED):
        raise Http404
    return render(request, "orders/invoice.html", {"order": order, "config": SiteConfig.get()})


# ------------------------------------------------------------ payments
def _pay_order(request, number, method):
    order = get_object_or_404(Order, number=number, user=request.user)
    if order.payment_method != method or not order.awaiting_payment_action:
        return None
    return order


@login_required
def razorpay_start(request, number):
    order = _pay_order(request, number, "razorpay")
    if order is None:
        return redirect("order_detail", number=number)
    if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
        messages.error(request, "Online payment is not configured. Please choose another method.")
        return redirect("order_detail", number=number)
    amount = int((order.total * 100).quantize(Decimal("1")))
    if not order.razorpay_order_id:
        try:
            r = requests.post(
                "https://api.razorpay.com/v1/orders",
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                json={"amount": amount, "currency": "INR", "receipt": order.number, "notes": {"order": order.number}},
                timeout=15,
            )
            r.raise_for_status()
            order.razorpay_order_id = r.json()["id"]
            order.save(update_fields=["razorpay_order_id"])
        except Exception:
            messages.error(request, "We could not reach the payment gateway. Please try again in a moment.")
            return redirect("order_detail", number=number)
    return render(request, "orders/pay_razorpay.html", {
        "order": order, "key_id": settings.RAZORPAY_KEY_ID, "amount": amount, "rzp_order_id": order.razorpay_order_id,
    })


@login_required
@require_POST
def razorpay_verify(request):
    pid = request.POST.get("razorpay_payment_id", "")
    oid = request.POST.get("razorpay_order_id", "")
    sig = request.POST.get("razorpay_signature", "")
    if not (oid and pid and sig and settings.RAZORPAY_KEY_SECRET):
        return HttpResponseBadRequest("invalid payment response")
    order = get_object_or_404(Order, razorpay_order_id=oid, user=request.user)
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        order.payment_status = "failed"
        order.save(update_fields=["payment_status"])
        messages.error(request, "Payment could not be verified. If money was deducted it will be refunded automatically.")
        return redirect("order_detail", number=order.number)
    order.mark_paid(razorpay_payment_id=pid)
    notify.order_placed(order)
    return redirect("order_thanks", number=order.number)


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """Set this URL in Razorpay Dashboard > Webhooks (events: payment.captured, order.paid)."""
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret:
        return HttpResponseBadRequest("webhook not configured")
    expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("X-Razorpay-Signature", "")):
        return HttpResponseBadRequest("bad signature")
    try:
        payload = json.loads(request.body)
        event = payload.get("event")
        if event in ("payment.captured", "order.paid"):
            entity = payload["payload"]["payment"]["entity"]
            rzp_oid = entity.get("order_id") or ""
            order = Order.objects.filter(razorpay_order_id=rzp_oid).first() if rzp_oid else None
            if order:
                order.mark_paid(razorpay_payment_id=entity.get("id", ""))
    except (KeyError, ValueError):
        return HttpResponseBadRequest("bad payload")
    return HttpResponse("ok")


def upi_link(config, order):
    return (f"upi://pay?pa={quote(config.upi_id)}&pn={quote(config.upi_name)}&am={order.total}"
            f"&cu=INR&tn={quote('Order ' + order.number)}&tr={order.number}")


def qr_svg(data):
    try:
        import qrcode
        import qrcode.image.svg
        img = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
        buf = io.BytesIO()
        img.save(buf)
        svg = buf.getvalue().decode()
        return svg[svg.find("<svg"):]
    except Exception:
        return ""


@login_required
def manual_payment(request, number):
    """UPI QR and bank-transfer: customer pays, enters UTR, staff verifies in the dashboard."""
    order = get_object_or_404(Order, number=number, user=request.user)
    if order.payment_method not in ("upi", "bank") or order.payment_status in ("paid", "verifying") or order.status == Order.CANCELLED:
        return redirect("order_detail", number=number)
    config = SiteConfig.get()
    if request.method == "POST":
        ref = re.sub(r"\s", "", request.POST.get("reference", ""))
        valid = re.fullmatch(r"\d{12}", ref) if order.payment_method == "upi" else re.fullmatch(r"[A-Za-z0-9]{6,30}", ref)
        if not valid:
            messages.error(request, "Enter the 12-digit UTR from your UPI app." if order.payment_method == "upi" else "Enter the transfer reference number.")
        elif Order.objects.filter(payment_reference=ref).exclude(pk=order.pk).exists():
            messages.error(request, "This reference is already used on another order. Please check it.")
        else:
            order.payment_reference = ref
            order.payment_status = "verifying"
            order.status = Order.PLACED
            order.save()
            notify.order_placed(order)
            messages.success(request, "Thanks. We will confirm your payment shortly, usually within a few hours.")
            return redirect("order_thanks", number=order.number)
    link = upi_link(config, order) if order.payment_method == "upi" else ""
    return render(request, "orders/pay_manual.html", {
        "order": order, "config": config, "upi_link": link, "qr": qr_svg(link) if link else "",
    })
