from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from accounts.states import STATE_NAMES


class Order(models.Model):
    PENDING, PLACED, CONFIRMED, PACKED, SHIPPED, DELIVERED, CANCELLED = (
        "pending_payment", "placed", "confirmed", "packed", "shipped", "delivered", "cancelled",
    )
    STATUSES = [
        (PENDING, "Awaiting payment"), (PLACED, "Placed"), (CONFIRMED, "Confirmed"), (PACKED, "Packed"),
        (SHIPPED, "Shipped"), (DELIVERED, "Delivered"), (CANCELLED, "Cancelled"),
    ]
    METHODS = [("razorpay", "Card / UPI / Netbanking (Razorpay)"), ("upi", "UPI QR"), ("bank", "Bank transfer (NEFT/IMPS)"), ("cod", "Cash on delivery")]
    PAY_STATUSES = [("unpaid", "Unpaid"), ("verifying", "Verifying"), ("paid", "Paid"), ("failed", "Failed"), ("refund_due", "Refund due"), ("refunded", "Refunded")]

    number = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUSES, default=PENDING)
    payment_method = models.CharField(max_length=10, choices=METHODS)
    payment_status = models.CharField(max_length=12, choices=PAY_STATUSES, default="unpaid")
    is_wholesale = models.BooleanField(default=False)

    ship_name = models.CharField(max_length=120)
    ship_phone = models.CharField(max_length=10)
    ship_line1 = models.CharField(max_length=200)
    ship_line2 = models.CharField(max_length=200, blank=True)
    ship_city = models.CharField(max_length=80)
    ship_state_code = models.CharField(max_length=2)
    ship_pincode = models.CharField(max_length=6)
    buyer_gstin = models.CharField(max_length=15, blank=True)
    buyer_business = models.CharField(max_length=150, blank=True)

    taxable_total = models.DecimalField(max_digits=11, decimal_places=2, default=0)
    cgst = models.DecimalField(max_digits=11, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=11, decimal_places=2, default=0)
    igst = models.DecimalField(max_digits=11, decimal_places=2, default=0)
    shipping_charge = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    cod_fee = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=11, decimal_places=2, default=0)

    courier = models.CharField(max_length=60, blank=True)
    tracking_id = models.CharField(max_length=60, blank=True)
    staff_note = models.TextField(blank=True)
    customer_note = models.CharField(max_length=300, blank=True)

    razorpay_order_id = models.CharField(max_length=40, blank=True)
    razorpay_payment_id = models.CharField(max_length=40, blank=True)
    payment_reference = models.CharField("UTR / reference", max_length=40, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f"LS{timezone.localdate():%y%m}{self.pk:05d}"
            super().save(update_fields=["number"])

    @property
    def ship_state_name(self):
        return STATE_NAMES.get(self.ship_state_code, "")

    @property
    def gst_total(self):
        return self.cgst + self.sgst + self.igst

    @property
    def is_intra_state(self):
        return self.igst == 0

    @property
    def can_cancel(self):
        return self.status in (self.PENDING, self.PLACED) and self.payment_status != "paid"

    @property
    def awaiting_payment_action(self):
        return self.status == self.PENDING and self.payment_status == "unpaid" and self.payment_method != "cod"

    def mark_paid(self, reference="", razorpay_payment_id=""):
        if self.payment_status == "paid":
            return
        self.payment_status = "paid"
        self.paid_at = timezone.now()
        if reference:
            self.payment_reference = reference
        if razorpay_payment_id:
            self.razorpay_payment_id = razorpay_payment_id
        if self.status in (self.PENDING, self.PLACED):
            self.status = self.CONFIRMED
        self.save()

    @transaction.atomic
    def cancel(self):
        if self.status == self.CANCELLED:
            return
        for item in self.items.select_related("product"):
            if item.product_id:
                item.product.__class__.objects.filter(pk=item.product_id).update(stock=models.F("stock") + item.qty)
        self.status = self.CANCELLED
        if self.payment_status == "paid":
            self.payment_status = "refund_due"
        self.save()

    def __str__(self):
        return self.number or f"Order #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("shop.Product", on_delete=models.SET_NULL, null=True, related_name="order_items")
    name = models.CharField(max_length=160)
    sku = models.CharField(max_length=40)
    hsn_code = models.CharField(max_length=8)
    image_url = models.CharField(max_length=300, blank=True)
    qty = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=9, decimal_places=2)
    is_wholesale_price = models.BooleanField(default=False)
    gst_rate = models.DecimalField(max_digits=4, decimal_places=2)
    taxable_value = models.DecimalField(max_digits=11, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=11, decimal_places=2)
    line_total = models.DecimalField(max_digits=11, decimal_places=2)

    def __str__(self):
        return f"{self.qty} x {self.name}"
