from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from orders import notify
from orders.models import Order
from shop.models import Enquiry, Product, Review

from .forms import OrderUpdateForm, ProductForm

staff = staff_member_required(login_url="login")
REVENUE_Q = Q(payment_status="paid") & ~Q(status="cancelled")


@staff
def home(request):
    today = timezone.localdate()
    start30 = timezone.now() - timedelta(days=30)
    paid = Order.objects.filter(REVENUE_Q)
    days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        amt = paid.filter(created__date=d).aggregate(s=Sum("total"))["s"] or Decimal("0")
        days.append({"label": d.strftime("%a"), "amount": amt})
    peak = max([d["amount"] for d in days] + [Decimal("1")])
    for d in days:
        d["pct"] = int(d["amount"] * 100 / peak)
    ctx = {
        "orders_today": Order.objects.filter(created__date=today).exclude(status="pending_payment").count(),
        "revenue_30": paid.filter(created__gte=start30).aggregate(s=Sum("total"))["s"] or 0,
        "to_ship": Order.objects.filter(status__in=["placed", "confirmed", "packed"]).count(),
        "to_verify": Order.objects.filter(payment_status="verifying").count(),
        "wholesale_pending": User.objects.filter(account_type="business", wholesale_approved=False).count(),
        "open_enquiries": Enquiry.objects.filter(is_resolved=False).count(),
        "low_stock": Product.objects.filter(is_active=True, stock__lte=3).order_by("stock")[:6],
        "recent": Order.objects.exclude(status="pending_payment").select_related("user")[:8],
        "days": days,
        "customers": User.objects.filter(is_staff=False).count(),
    }
    return render(request, "dashboard/home.html", ctx)


@staff
def orders(request):
    qs = Order.objects.select_related("user")
    status = request.GET.get("status", "")
    pay = request.GET.get("payment", "")
    q = request.GET.get("q", "").strip()
    if status:
        qs = qs.filter(status=status)
    if pay:
        qs = qs.filter(payment_status=pay)
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(user__email__icontains=q) | Q(ship_name__icontains=q) | Q(ship_phone__icontains=q))
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "dashboard/orders.html", {
        "page": page, "status": status, "pay": pay, "q": q,
        "statuses": Order.STATUSES, "pay_statuses": Order.PAY_STATUSES,
    })


@staff
def order_detail(request, number):
    order = get_object_or_404(Order.objects.select_related("user"), number=number)
    form = OrderUpdateForm(request.POST or None, instance=order)
    if request.method == "POST" and form.is_valid():
        prev_status, prev_pay = Order.objects.values_list("status", "payment_status").get(pk=order.pk)
        updated = form.save(commit=False)
        if updated.status == "cancelled" and prev_status != "cancelled":
            updated.status = prev_status  # let cancel() do the restock + status change
            updated.save()
            updated.cancel()
        else:
            if updated.payment_status == "paid" and prev_pay != "paid":
                updated.paid_at = timezone.now()
            if updated.status == "delivered" and updated.payment_method == "cod":
                updated.payment_status = "paid"
                updated.paid_at = updated.paid_at or timezone.now()
            updated.save()
            if updated.status == "shipped" and prev_status != "shipped":
                notify.order_shipped(updated)
        messages.success(request, "Order updated.")
        return redirect("dash_order", number=number)
    return render(request, "dashboard/order_detail.html", {"order": order, "form": form})


@staff
@require_POST
def order_verify_payment(request, number):
    order = get_object_or_404(Order, number=number)
    if request.POST.get("action") == "approve":
        order.mark_paid()
        notify.order_placed(order)
        messages.success(request, f"Payment confirmed for {order.number}.")
    else:
        order.payment_status = "failed"
        order.payment_reference = ""
        order.status = Order.PENDING
        order.save()
        messages.info(request, "Payment marked as not received. The customer can try again.")
    return redirect("dash_order", number=number)


@staff
def products(request):
    q = request.GET.get("q", "").strip()
    qs = Product.objects.select_related("category")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "dashboard/products.html", {"page": page, "q": q})


@staff
def product_edit(request, pk=None):
    instance = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product saved.")
        return redirect("dash_products")
    return render(request, "dashboard/product_form.html", {"form": form, "product": instance})


@staff
@require_POST
def product_toggle(request, pk):
    p = get_object_or_404(Product, pk=pk)
    p.is_active = not p.is_active
    p.save(update_fields=["is_active"])
    return redirect("dash_products")


@staff
def customers(request):
    qs = User.objects.filter(is_staff=False).annotate(order_count=Count("orders"), spent=Sum("orders__total", filter=Q(orders__payment_status="paid")))
    if request.GET.get("filter") == "pending":
        qs = qs.filter(account_type="business", wholesale_approved=False)
    elif request.GET.get("filter") == "wholesale":
        qs = qs.filter(wholesale_approved=True)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(phone__icontains=q) | Q(business_name__icontains=q))
    page = Paginator(qs.order_by("-date_joined"), 20).get_page(request.GET.get("page"))
    return render(request, "dashboard/customers.html", {"page": page, "q": q, "filter": request.GET.get("filter", "")})


@staff
@require_POST
def customer_wholesale(request, pk):
    u = get_object_or_404(User, pk=pk)
    u.wholesale_approved = request.POST.get("approve") == "1"
    u.save(update_fields=["wholesale_approved"])
    messages.success(request, f"Wholesale {'approved' if u.wholesale_approved else 'removed'} for {u.email}.")
    return redirect(request.POST.get("next") or "dash_customers")


@staff
def enquiries(request):
    qs = Enquiry.objects.all()
    if request.GET.get("show") != "all":
        qs = qs.filter(is_resolved=False)
    return render(request, "dashboard/enquiries.html", {"enquiries": qs[:100], "show": request.GET.get("show", "")})


@staff
@require_POST
def enquiry_resolve(request, pk):
    Enquiry.objects.filter(pk=pk).update(is_resolved=True)
    return redirect("dash_enquiries")


@staff
def reviews(request):
    return render(request, "dashboard/reviews.html", {"reviews": Review.objects.select_related("product", "user")[:100]})


@staff
@require_POST
def review_toggle(request, pk):
    r = get_object_or_404(Review, pk=pk)
    r.is_approved = not r.is_approved
    r.save(update_fields=["is_approved"])
    return redirect("dash_reviews")
