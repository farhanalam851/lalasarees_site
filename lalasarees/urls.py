from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.templatetags.static import static as static_url
from django.urls import include, path
from django.views.generic import RedirectView

from shop import views as shop_views
from shop.sitemaps import CategorySitemap, ProductSitemap, StaticSitemap

sitemaps = {"pages": StaticSitemap, "categories": CategorySitemap, "products": ProductSitemap}

admin.site.site_header = "Lala Sarees admin"
admin.site.site_title = "Lala Sarees"
admin.site.index_title = "Store management"

urlpatterns = [
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", shop_views.robots_txt, name="robots"),
    path("healthz/", shop_views.healthz, name="healthz"),
    path("site.webmanifest", shop_views.webmanifest, name="webmanifest"),
    path("favicon.ico", RedirectView.as_view(url=static_url("favicon.ico"), permanent=True)),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("", include("orders.urls")),
    path("", include("shop.urls")),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "shop.views.error_404"
handler500 = "shop.views.error_500"
