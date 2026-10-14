from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import AddressForm, ProfileForm, RegisterForm
from .models import Address, User


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None, initial={"account_type": request.GET.get("type", User.RETAIL)})
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        if user.is_business:
            messages.success(request, "Welcome to Lala Sarees. We will verify your GSTIN and activate wholesale rates, usually within one working day.")
        else:
            messages.success(request, "Welcome to Lala Sarees. Your account is ready.")
        nxt = request.GET.get("next", "")
        if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
            return redirect(nxt)
        return redirect("home")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")
    return render(request, "accounts/profile.html", {"form": form, "addresses": request.user.addresses.all()})


@login_required
def address_edit(request, pk=None):
    instance = get_object_or_404(Address, pk=pk, user=request.user) if pk else None
    initial = {"full_name": request.user.get_full_name(), "phone": request.user.phone} if not instance else None
    form = AddressForm(request.POST or None, instance=instance, initial=initial)
    if request.method == "POST" and form.is_valid():
        addr = form.save(commit=False)
        addr.user = request.user
        if not request.user.addresses.exists():
            addr.is_default = True
        addr.save()
        messages.success(request, "Address saved.")
        return redirect(request.GET.get("next") or "profile")
    return render(request, "accounts/address_form.html", {"form": form, "editing": bool(instance)})


@login_required
@require_POST
def address_delete(request, pk):
    get_object_or_404(Address, pk=pk, user=request.user).delete()
    messages.success(request, "Address removed.")
    return redirect("profile")
