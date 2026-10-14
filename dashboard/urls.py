from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="dash_home"),
    path("orders/", views.orders, name="dash_orders"),
    path("orders/<str:number>/", views.order_detail, name="dash_order"),
    path("orders/<str:number>/payment/", views.order_verify_payment, name="dash_order_payment"),
    path("products/", views.products, name="dash_products"),
    path("products/new/", views.product_edit, name="dash_product_new"),
    path("products/<int:pk>/", views.product_edit, name="dash_product_edit"),
    path("products/<int:pk>/toggle/", views.product_toggle, name="dash_product_toggle"),
    path("customers/", views.customers, name="dash_customers"),
    path("customers/<int:pk>/wholesale/", views.customer_wholesale, name="dash_customer_wholesale"),
    path("enquiries/", views.enquiries, name="dash_enquiries"),
    path("enquiries/<int:pk>/resolve/", views.enquiry_resolve, name="dash_enquiry_resolve"),
    path("reviews/", views.reviews, name="dash_reviews"),
    path("reviews/<int:pk>/toggle/", views.review_toggle, name="dash_review_toggle"),
]
