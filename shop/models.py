from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count, Q
from django.urls import reverse
from django.utils.text import slugify

from .imaging import optimise


class SiteConfig(models.Model):
    """Single row of store settings, editable from the admin."""

    store_name = models.CharField(max_length=80, default="Lala Sarees")
    tagline = models.CharField(max_length=160, default="Premium sarees for every occasion")
    phone1 = models.CharField(max_length=15, default="9211420021")
    phone2 = models.CharField(max_length=15, default="9638527410", blank=True)
    whatsapp = models.CharField(max_length=15, default="9211420021", blank=True, help_text="Number for the WhatsApp chat button")
    email = models.EmailField(blank=True)
    address = models.TextField(default="P Road, Kanpur, Uttar Pradesh")
    gstin = models.CharField("Store GSTIN", max_length=15, blank=True)
    state_code = models.CharField("Store state code", max_length=2, default="09", help_text="09 = Uttar Pradesh. Same-state orders get CGST+SGST, others IGST.")

    free_shipping_above = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("2999"))
    shipping_local = models.DecimalField("Shipping within home state", max_digits=7, decimal_places=2, default=Decimal("60"))
    shipping_national = models.DecimalField("Shipping rest of India", max_digits=7, decimal_places=2, default=Decimal("120"))

    cod_enabled = models.BooleanField("Cash on delivery", default=True)
    cod_fee = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("50"))
    cod_max_amount = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("10000"))

    upi_id = models.CharField("UPI ID", max_length=80, blank=True, help_text="e.g. lalasarees@okhdfcbank. Leave blank to hide UPI QR payments.")
    upi_name = models.CharField("UPI payee name", max_length=80, default="Lala Sarees")
    bank_details = models.TextField(blank=True, help_text="Account name, number, IFSC, bank. Leave blank to hide bank transfer.")

    announcement = models.CharField(max_length=200, blank=True, default="Free shipping on orders above ₹2,999. Wholesale rates for verified businesses.")

    class Meta:
        verbose_name = "store settings"
        verbose_name_plural = "store settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Store settings"


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to="categories/", blank=True)
    image_position = models.CharField(max_length=30, default="50% 20%")
    description = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        optimise(self.image)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("category", args=[self.slug])

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True, category__is_active=True)

    def with_ratings(self):
        return self.annotate(
            avg_r=Avg("reviews__rating", filter=Q(reviews__is_approved=True)),
            cnt_r=Count("reviews", filter=Q(reviews__is_approved=True)),
        )


class Product(models.Model):
    OCCASIONS = [
        ("wedding", "Wedding"), ("party", "Party"), ("festive", "Festive"),
        ("office", "Office"), ("daily", "Everyday"), ("bridal", "Bridal"),
    ]

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    sku = models.CharField(max_length=40, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    occasion = models.CharField(max_length=10, choices=OCCASIONS, default="festive")
    fabric = models.CharField(max_length=80, blank=True)
    color = models.CharField(max_length=60, blank=True)
    description = models.TextField(blank=True)
    care = models.CharField("Care instructions", max_length=200, blank=True, default="Dry clean only.")
    includes = models.CharField(max_length=200, blank=True, default="Saree with stitched blouse piece")

    image = models.ImageField(upload_to="products/")
    image_position = models.CharField(max_length=30, default="50% 20%", help_text="Crop focus for thumbnails, e.g. '57% 50%'")

    price = models.DecimalField("Retail price (₹)", max_digits=9, decimal_places=2, validators=[MinValueValidator(1)])
    mrp = models.DecimalField("MRP (₹)", max_digits=9, decimal_places=2, null=True, blank=True)
    wholesale_price = models.DecimalField("Wholesale price (₹)", max_digits=9, decimal_places=2, null=True, blank=True)
    wholesale_min_qty = models.PositiveSmallIntegerField("Wholesale from qty", default=6)
    gst_rate = models.DecimalField("GST %", max_digits=4, decimal_places=2, default=Decimal("5"), help_text="Confirm the correct rate for the product with your CA.")
    hsn_code = models.CharField("HSN code", max_length=8, default="5407")

    stock = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:170] or "saree"
            slug, n = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        optimise(self.image)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.slug])

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def discount_percent(self):
        if self.mrp and self.mrp > self.price:
            return int((self.mrp - self.price) * 100 / self.mrp)
        return 0

    @property
    def avg_rating(self):
        if hasattr(self, "avg_r"):
            return round(self.avg_r or 0, 1)
        agg = self.reviews.filter(is_approved=True).aggregate(a=Avg("rating"))["a"]
        return round(agg or 0, 1)

    @property
    def review_count(self):
        if hasattr(self, "cnt_r"):
            return self.cnt_r
        return self.reviews.filter(is_approved=True).count()

    def is_wholesale_buyer(self, user):
        return bool(user and user.is_authenticated and user.wholesale_approved)

    def price_for(self, user, qty=1):
        """Return (unit_price, is_wholesale)."""
        if self.wholesale_price and self.is_wholesale_buyer(user) and qty >= self.wholesale_min_qty:
            return self.wholesale_price, True
        return self.price, False

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt = models.CharField(max_length=120, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        optimise(self.image)
        super().save(*args, **kwargs)


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=100, blank=True)
    comment = models.TextField(max_length=1500)
    image = models.ImageField(upload_to="reviews/", blank=True)
    verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        unique_together = [("product", "user")]

    def save(self, *args, **kwargs):
        optimise(self.image, max_side=1000)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product} - {self.rating}★ by {self.user}"


class Enquiry(models.Model):
    WHOLESALE, CONTACT = "wholesale", "contact"
    kind = models.CharField(max_length=10, choices=[(WHOLESALE, "Wholesale"), (CONTACT, "Contact")], default=CONTACT)
    name = models.CharField(max_length=100)
    business_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=10)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=80, blank=True)
    expected_qty = models.CharField("Monthly quantity", max_length=40, blank=True)
    message = models.TextField(max_length=2000)
    created = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created"]
        verbose_name_plural = "enquiries"

    def __str__(self):
        return f"{self.get_kind_display()} enquiry from {self.name}"
