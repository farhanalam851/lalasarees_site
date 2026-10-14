from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import EmailAuthForm

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html", authentication_form=EmailAuthForm, redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("addresses/add/", views.address_edit, name="address_add"),
    path("addresses/<int:pk>/edit/", views.address_edit, name="address_edit"),
    path("addresses/<int:pk>/delete/", views.address_delete, name="address_delete"),
    path("password/change/", auth_views.PasswordChangeView.as_view(template_name="accounts/password_change.html", success_url="/accounts/profile/"), name="password_change"),
    path("password/reset/", auth_views.PasswordResetView.as_view(template_name="accounts/password_reset.html", email_template_name="accounts/password_reset_email.txt", success_url="/accounts/password/reset/sent/"), name="password_reset"),
    path("password/reset/sent/", auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"), name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="accounts/password_reset_confirm.html", success_url="/accounts/login/"), name="password_reset_confirm"),
]
