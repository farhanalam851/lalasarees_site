from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.catalog, name="catalog"),
    path("category/<slug:slug>/", views.catalog, name="category"),
    path("saree/<slug:slug>/", views.product_detail, name="product_detail"),
    path("saree/<slug:slug>/review/", views.add_review, name="add_review"),
    path("wholesale/", views.enquiry, {"kind": "wholesale"}, name="wholesale"),
    path("contact/", views.enquiry, {"kind": "contact"}, name="contact"),
    path("thank-you/", views.thanks, name="thanks"),
    path("about/", TemplateView.as_view(template_name="pages/about.html"), name="about"),
    path("shipping-returns/", TemplateView.as_view(template_name="pages/shipping.html"), name="shipping_policy"),
    path("terms/", TemplateView.as_view(template_name="pages/terms.html"), name="terms"),
    path("privacy/", TemplateView.as_view(template_name="pages/privacy.html"), name="privacy"),
]
