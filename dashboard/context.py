from accounts.models import User
from orders.models import Order
from shop.models import Enquiry


def counts(request):
    if not request.path.startswith("/dashboard/") or not request.user.is_staff:
        return {}
    path = request.path
    nav = "home"
    for key, frag in (("orders", "/orders/"), ("products", "/products/"), ("customers", "/customers/"), ("enquiries", "/enquiries/"), ("reviews", "/reviews/")):
        if frag in path:
            nav = key
    if nav == "orders" and request.GET.get("payment") == "verifying":
        nav = "verify"
    return {"nav": nav, "dash_counts": {
        "verify": Order.objects.filter(payment_status="verifying").count(),
        "ship": Order.objects.filter(status__in=["placed", "confirmed", "packed"]).count(),
        "wholesale": User.objects.filter(account_type="business", wholesale_approved=False).count(),
        "enquiries": Enquiry.objects.filter(is_resolved=False).count(),
    }}
