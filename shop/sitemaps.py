from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Category, Product


class Base(Sitemap):
    protocol = settings.SITEMAP_PROTOCOL


class StaticSitemap(Base):
    changefreq = "monthly"

    def items(self):
        return ["home", "catalog", "wholesale", "about", "contact", "shipping_policy", "terms", "privacy"]

    def location(self, name):
        return reverse(name)

    def priority(self, name):
        return 1.0 if name == "home" else 0.6


class CategorySitemap(Base):
    priority, changefreq = 0.8, "weekly"

    def items(self):
        return Category.objects.filter(is_active=True)


class ProductSitemap(Base):
    priority, changefreq = 0.9, "weekly"
    limit = 5000

    def items(self):
        return Product.objects.active().order_by("-created")

    def lastmod(self, obj):
        return obj.created
