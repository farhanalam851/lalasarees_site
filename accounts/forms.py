import re

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from .models import Address, User

PHONE_RE = re.compile(r"^[6-9]\d{9}$")
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$")
PIN_RE = re.compile(r"^[1-9]\d{5}$")


def clean_phone_value(value):
    value = re.sub(r"\D", "", value or "")
    if value.startswith("91") and len(value) == 12:
        value = value[2:]
    if not PHONE_RE.match(value):
        raise forms.ValidationError("Enter a valid 10-digit mobile number.")
    return value


class EmailAuthForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}))

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "account_type", "business_name", "gstin"]
        widgets = {"account_type": forms.RadioSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["phone"].required = True
        self.fields["account_type"].initial = User.RETAIL
        self.fields["gstin"].help_text = "Required for wholesale rates. 15 characters."

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists. Try logging in.")
        return email

    def clean_phone(self):
        return clean_phone_value(self.cleaned_data.get("phone"))

    def clean_gstin(self):
        g = (self.cleaned_data.get("gstin") or "").strip().upper()
        if g and not GSTIN_RE.match(g):
            raise forms.ValidationError("Enter a valid 15-character GSTIN.")
        return g

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        elif data.get("password1"):
            try:
                password_validation.validate_password(data["password1"])
            except forms.ValidationError as e:
                self.add_error("password1", e)
        if data.get("account_type") == User.BUSINESS and not data.get("business_name"):
            self.add_error("business_name", "Enter your shop / business name.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "business_name", "gstin"]

    def clean_phone(self):
        return clean_phone_value(self.cleaned_data.get("phone"))

    def clean_gstin(self):
        g = (self.cleaned_data.get("gstin") or "").strip().upper()
        if g and not GSTIN_RE.match(g):
            raise forms.ValidationError("Enter a valid 15-character GSTIN.")
        return g


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["full_name", "phone", "line1", "line2", "city", "state_code", "pincode", "is_default"]

    def clean_phone(self):
        return clean_phone_value(self.cleaned_data.get("phone"))

    def clean_pincode(self):
        p = (self.cleaned_data.get("pincode") or "").strip()
        if not PIN_RE.match(p):
            raise forms.ValidationError("Enter a valid 6-digit PIN code.")
        return p
