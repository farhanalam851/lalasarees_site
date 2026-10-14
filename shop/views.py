import json

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import EnquiryForm, ReviewForm
from .models import Category, Enquiry, Product, Review, SiteConfig

SORTS = {
    "new": ("-created", "Newest"),
    "price_asc": ("price", "Price: low to high"),
    "price_desc": ("-price", "Price: high to low"),
    "rating": ("-avg_r", "Top rated"),
}


def dumps_ld(obj):
    return json.dumps(obj).replace("</", "<\\/")


def local_business_ld(request):
    cfg = SiteConfig.get()
    base = f"{request.scheme}://{request.get_host()}"
    ld = {
        "@context": "https://schema.org", "@type": "ClothingStore", "name": cfg.store_name, "url": base + "/",
        "image": base + "/static/img/og-image.jpg", "telephone": "+91" + cfg.phone1,
        "address": {"@type": "PostalAddress", "streetAddress": "P Road", "addressLocality": "Kanpur",
                    "addressRegion": "Uttar Pradesh", "addressCountry": "IN"},
        "priceRange": "₹₹",
    }
    if cfg.email:
        ld["email"] = cfg.email
    return ld


def breadcrumb_ld(request, trail):
    base = f"{request.scheme}://{request.get_host()}"
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": name, "item": base + path} for i, (name, path) in enumerate(trail, 1)]}


def home(request):
    base = Product.objects.active().with_ratings().select_related("category")
    ctx = {
        "featured": base.filter(is_featured=True)[:8] or base[:8],
        "new_arrivals": base[:4],
        "categories": Category.objects.filter(is_active=True).annotate(n=Count("products", filter=Q(products__is_active=True)))[:6],
        "occasions": Product.OCCASIONS,
        "reviews": Review.objects.filter(is_approved=True, rating__gte=4).exclude(comment="").select_related("user", "product")[:3],
        "ld_json": dumps_ld(local_business_ld(request)),
    }
    return render(request, "shop/home.html", ctx)


def catalog(request, slug=None):
    qs = Product.objects.active().with_ratings().select_related("category")
    category = None
    if slug:
        category = get_object_or_404(Category, slug=slug, is_active=True)
        qs = qs.filter(category=category)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(fabric__icontains=q) | Q(color__icontains=q) | Q(sku__icontains=q) | Q(description__icontains=q))
    occasion = request.GET.get("occasion", "")
    if occasion in dict(Product.OCCASIONS):
        qs = qs.filter(occasion=occasion)
    for key, lookup in (("min", "price__gte"), ("max", "price__lte")):
        val = request.GET.get(key, "")
        if val.isdigit():
            qs = qs.filter(**{lookup: int(val)})
    if request.GET.get("in_stock") == "1":
        qs = qs.filter(stock__gt=0)
    sort = request.GET.get("sort", "new")
    if sort not in SORTS:
        sort = "new"
    qs = qs.order_by(SORTS[sort][0], "-created")
    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    filtered = bool(q or occasion or request.GET.get("min") or request.GET.get("max") or request.GET.get("in_stock") or request.GET.get("sort", "new") != "new")
    base_path = request.path
    trail = [("Home", "/"), ("Sarees", reverse("catalog"))] + ([(category.name, category.get_absolute_url())] if category else [])
    if category:
        title = f"{category.name} | Buy online, Kanpur | Lala Sarees"
        desc = (category.description or f"Shop {category.name.lower()} at Lala Sarees, P Road, Kanpur.") + " Retail and wholesale, GST invoice, UPI and COD."
    else:
        title = "Buy Sarees Online | Designer, Silk, Wedding | Lala Sarees"
        desc = "Browse ready-to-wear, designer, silk and wedding sarees from Lala Sarees, P Road, Kanpur. Retail and wholesale prices, GST invoice, UPI and COD."
    if q:
        title = f"Search results for {q} | Lala Sarees"
    return render(request, "shop/catalog.html", {
        "meta_title": title, "meta_desc": desc[:158], "noindex": filtered,
        "canonical": base_path + (f"?page={page.number}" if page.number > 1 and not filtered else ""),
        "ld_json": dumps_ld(breadcrumb_ld(request, trail)),
        "page": page, "category": category, "q": q, "occasion": occasion, "sort": sort,
        "sorts": [(k, v[1]) for k, v in SORTS.items()], "occasions": Product.OCCASIONS,
        "qs": params.urlencode(), "total": page.paginator.count,
        "min": request.GET.get("min", ""), "max": request.GET.get("max", ""),
        "in_stock": request.GET.get("in_stock") == "1",
    })


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.active().select_related("category"), slug=slug)
    reviews = product.reviews.filter(is_approved=True).select_related("user")
    dist = {i: 0 for i in range(5, 0, -1)}
    for r in reviews:
        dist[r.rating] += 1
    total = len(reviews)
    breakdown = [(star, n, int(n * 100 / total) if total else 0) for star, n in dist.items()]
    my_review = reviews.filter(user=request.user).first() if request.user.is_authenticated else None
    related = Product.objects.active().with_ratings().filter(category=product.category).exclude(pk=product.pk)[:4]
    gallery = [{"url": product.image.url, "alt": product.name}] + [{"url": i.image.url, "alt": i.alt or product.name} for i in product.images.all()]
    ld = {
        "@context": "https://schema.org", "@type": "Product", "name": product.name, "sku": product.sku,
        "image": [request.build_absolute_uri(g["url"]) for g in gallery], "description": product.description[:300],
        "brand": {"@type": "Brand", "name": "Lala Sarees"},
        "offers": {"@type": "Offer", "priceCurrency": "INR", "price": str(product.price),
                   "availability": "https://schema.org/InStock" if product.in_stock else "https://schema.org/OutOfStock"},
    }
    if total:
        ld["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": product.avg_rating, "reviewCount": total}
    trail = [("Home", "/"), ("Sarees", reverse("catalog")), (product.category.name, product.category.get_absolute_url()), (product.name, product.get_absolute_url())]
    return render(request, "shop/product_detail.html", {
        "meta_title": f"{product.name} | Lala Sarees, Kanpur",
        "meta_desc": f"Buy {product.name} online. {product.fabric} {product.color} saree at {product.price:.0f} rupees with GST invoice, UPI and COD. Lala Sarees, Kanpur."[:158],
        "og_image": request.build_absolute_uri(product.image.url), "og_type": "product",
        "product": product, "reviews": reviews, "total_reviews": total, "breakdown": breakdown,
        "form": ReviewForm(instance=my_review), "my_review": my_review, "related": related,
        "gallery": gallery, "ld_json": dumps_ld([ld, breadcrumb_ld(request, trail)]),
        "qty_options": range(1, min(product.stock, 10) + 1),
    })


@login_required
@require_POST
def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    existing = Review.objects.filter(product=product, user=request.user).first()
    form = ReviewForm(request.POST, request.FILES, instance=existing)
    if form.is_valid():
        review = form.save(commit=False)
        review.product, review.user = product, request.user
        OrderItem = apps.get_model("orders", "OrderItem")
        review.verified_purchase = OrderItem.objects.filter(
            order__user=request.user, product=product
        ).exclude(order__status__in=["cancelled", "pending_payment"]).exists()
        review.save()
        messages.success(request, "Thanks. Your review is live.")
    else:
        messages.error(request, "Please choose a star rating and write a short review.")
    return redirect(product.get_absolute_url() + "#reviews")


def enquiry(request, kind="contact"):
    initial = {}
    if request.user.is_authenticated:
        initial = {"name": request.user.get_full_name(), "phone": request.user.phone, "email": request.user.email,
                   "business_name": request.user.business_name}
    form = EnquiryForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.kind = kind
        obj.save()
        return redirect(f"{reverse('thanks')}?type={kind}")
    template = "pages/wholesale.html" if kind == "wholesale" else "pages/contact.html"
    return render(request, template, {"form": form})


def thanks(request):
    kind = request.GET.get("type", "contact")
    return render(request, "pages/thanks.html", {"kind": kind})


def robots_txt(request):
    base = f"{request.scheme}://{request.get_host()}"
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/", "Disallow: /dashboard/", "Disallow: /accounts/", "Disallow: /cart/",
        "Disallow: /checkout/", "Disallow: /orders/", "Disallow: /pay/", "Disallow: /thank-you/",
        "Disallow: /*?*q=", "Disallow: /*?*sort=",
        "",
        f"Sitemap: {base}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def webmanifest(request):
    return JsonResponse({
        "name": "Lala Sarees", "short_name": "Lala Sarees", "start_url": "/", "display": "standalone",
        "background_color": "#FCF8F7", "theme_color": "#0F3A41",
        "icons": [{"src": "/static/img/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/static/img/icons/icon-512.png", "sizes": "512x512", "type": "image/png"}],
    }, content_type="application/manifest+json")


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)


def healthz(request):
    """Deployment self-check: open /healthz/ after deploying. Reports booleans only, never secrets."""
    from django.conf import settings
    from django.db import connection
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        db = connection.vendor
    except Exception as exc:  # noqa: BLE001
        db = f"ERROR: {exc.__class__.__name__}"
    ok = not str(db).startswith("ERROR")
    resp = JsonResponse({"ok": ok, "database": db, "media_storage": settings.MEDIA_STORAGE_CONFIGURED,
                         "debug": settings.DEBUG}, status=200 if ok else 503)
    resp["Cache-Control"] = "no-store"
    resp["X-Robots-Tag"] = "noindex"
    return resp
