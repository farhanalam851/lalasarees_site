from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .states import STATES, STATE_NAMES


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    RETAIL, BUSINESS = "retail", "business"
    ACCOUNT_TYPES = [(RETAIL, "Individual buyer"), (BUSINESS, "Business / reseller")]

    username = None
    email = models.EmailField("email address", unique=True)
    phone = models.CharField(max_length=10, blank=True)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default=RETAIL)
    business_name = models.CharField(max_length=150, blank=True)
    gstin = models.CharField("GSTIN", max_length=15, blank=True)
    wholesale_approved = models.BooleanField(
        default=False, help_text="Tick after verifying the business. Unlocks wholesale prices."
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]
    objects = UserManager()

    @property
    def is_business(self):
        return self.account_type == self.BUSINESS

    @property
    def display_name(self):
        return self.first_name or self.email.split("@")[0]

    def __str__(self):
        return self.email


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=10)
    line1 = models.CharField("Address line 1", max_length=200)
    line2 = models.CharField("Address line 2", max_length=200, blank=True)
    city = models.CharField(max_length=80)
    state_code = models.CharField("State", max_length=2, choices=STATES, default="09")
    pincode = models.CharField(max_length=6)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "-id"]
        verbose_name_plural = "addresses"

    @property
    def state_name(self):
        return STATE_NAMES.get(self.state_code, "")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)

    def __str__(self):
        return f"{self.full_name}, {self.city} {self.pincode}"
