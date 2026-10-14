from django import forms

from orders.models import Order
from shop.models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ["slug", "created"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}


class OrderUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status", "payment_status", "courier", "tracking_id", "staff_note"]
        widgets = {"staff_note": forms.Textarea(attrs={"rows": 3})}
