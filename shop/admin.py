from django.contrib import admin

from .models import Category, Enquiry, Product, ProductImage, Review, SiteConfig


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    prepopulated_fields = {"slug": ("name",)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 2


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "wholesale_price", "stock", "is_active", "is_featured")
    list_editable = ("price", "stock", "is_active", "is_featured")
    list_filter = ("category", "occasion", "is_active", "is_featured")
    search_fields = ("name", "sku", "color", "fabric")
    inlines = [ProductImageInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "verified_purchase", "is_approved", "created")
    list_filter = ("is_approved", "rating", "verified_purchase")
    list_editable = ("is_approved",)


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "business_name", "phone", "kind", "created", "is_resolved")
    list_filter = ("kind", "is_resolved")
    list_editable = ("is_resolved",)
