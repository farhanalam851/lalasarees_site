from django.urls import path

from . import views

urlpatterns = [
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/quote/", views.checkout_quote, name="checkout_quote"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<str:number>/", views.order_detail, name="order_detail"),
    path("orders/<str:number>/thank-you/", views.order_thanks, name="order_thanks"),
    path("orders/<str:number>/cancel/", views.order_cancel, name="order_cancel"),
    path("orders/<str:number>/invoice/", views.invoice, name="invoice"),
    path("pay/<str:number>/razorpay/", views.razorpay_start, name="razorpay_start"),
    path("pay/razorpay/verify/", views.razorpay_verify, name="razorpay_verify"),
    path("pay/razorpay/webhook/", views.razorpay_webhook, name="razorpay_webhook"),
    path("pay/<str:number>/manual/", views.manual_payment, name="manual_payment"),
]
