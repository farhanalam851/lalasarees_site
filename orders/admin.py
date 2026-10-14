from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "name", "sku", "qty", "unit_price", "gst_rate", "taxable_value", "gst_amount", "line_total")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "status", "payment_method", "payment_status", "total", "created")
    list_filter = ("status", "payment_status", "payment_method", "is_wholesale")
    search_fields = ("number", "user__email", "ship_name", "ship_phone", "payment_reference")
    inlines = [OrderItemInline]
