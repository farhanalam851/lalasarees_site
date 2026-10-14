from django.conf import settings

from .models import Category, SiteConfig


def site(request):
    if request.path.startswith(("/admin/", "/static/", "/media/")):
        return {}
    cart = request.session.get("cart", {})
    return {
        "site": SiteConfig.get(),
        "nav_categories": Category.objects.filter(is_active=True),
        "GA_ID": settings.GA_MEASUREMENT_ID,
        "cart_count": sum(int(q) for q in cart.values()) if cart else 0,
    }
