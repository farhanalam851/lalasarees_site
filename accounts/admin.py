from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Address, User


@admin.register(User)
class LalaUserAdmin(UserAdmin):
    ordering = ("-date_joined",)
    list_display = ("email", "first_name", "phone", "account_type", "business_name", "wholesale_approved", "date_joined")
    list_filter = ("account_type", "wholesale_approved", "is_staff")
    search_fields = ("email", "first_name", "last_name", "phone", "business_name", "gstin")
    actions = ["approve_wholesale"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("first_name", "last_name", "phone")}),
        ("Business", {"fields": ("account_type", "business_name", "gstin", "wholesale_approved")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "first_name", "password1", "password2")}),)

    @admin.action(description="Approve selected as wholesale buyers")
    def approve_wholesale(self, request, queryset):
        queryset.update(wholesale_approved=True)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "city", "state_code", "pincode", "user")
    search_fields = ("full_name", "city", "pincode", "user__email")
