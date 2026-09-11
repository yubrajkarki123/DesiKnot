from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.core.validators import MaxValueValidator
from decimal import Decimal
from django.utils import timezone

import os

User = get_user_model()


# =========================
# IMAGE VALIDATION
# =========================
def validate_image_size(image):
    if image.size > 4 * 1024 * 1024:  # 4MB
        raise ValidationError("Image too large. Maximum size allowed is 4MB.")
def validate_profile_image(image):
    if image.size > 1 * 1024 * 1024:  # 1MB
        raise ValidationError("Profile image must be under 1MB")


# =========================
# USER PROFILE
# =========================
class UserProfile(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_OWNER = "owner"
    ROLE_CUSTOMER = "customer"

    ROLE_CHOICES = (
        (ROLE_ADMIN, "Admin"),
        (ROLE_OWNER, "Owner"),
        (ROLE_CUSTOMER, "Customer"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    phone = models.CharField(max_length=15, blank=True, null=True)

    profile_image = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
        validators=[validate_profile_image]
    )

    last_seen = models.DateTimeField(null=True, blank=True)

    def is_owner(self):
        return self.role == self.ROLE_OWNER

    def is_customer(self):
        return self.role == self.ROLE_CUSTOMER

    def __str__(self):
        return f"{self.user} ({self.role})"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


# =========================
# BUSINESS
# =========================
class Business(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="business")
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    latitude = models.FloatField(default=27.6732)
    longitude = models.FloatField(default=85.3240)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
#======================= Categories======================#

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class ProductType(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="types"
    )

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} - {self.name}"

# =========================
# PRODUCT
# =========================
class Product(models.Model):

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="products",
        null=True,
        blank=True
    )

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="products",
        null=True,
        blank=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products"
    )

    name = models.CharField(max_length=200)

    slug = models.SlugField(unique=True, null=True, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)

    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Leave empty if there is no discount."
    )

    description = models.TextField()

    image = models.ImageField(
        upload_to="products/",
        validators=[validate_image_size],
        blank=True,
        null=True
    )

    stock = models.PositiveIntegerField(default=0)

    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)


    def save(self, *args, **kwargs):
     if not self.slug:
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1

        while Product.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        self.slug = slug

     super().save(*args, **kwargs)

    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Owner's cost per unit — used for profit margin calculation"
    )

    @property
    def discounted_price(self):
        if self.sale_price:
            return self.sale_price
        return self.price

    @property
    def discount_percentage(self):
        if self.sale_price and self.sale_price < self.price:
            return round(((self.price - self.sale_price) / self.price) * 100)
        return 0

    @property
    def has_discount(self):
        return self.sale_price is not None and self.sale_price < self.price



class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    rating = models.PositiveIntegerField(
    validators=[MinValueValidator(1), MaxValueValidator(5)]
)
    
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')  # one review per user per product
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.rating}★ by {self.user.username}"   

    
# =========================
# PRODUCT IMAGES
# =========================
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="product_images/", validators=[validate_image_size])

    def __str__(self):
        return f"{self.product.name} Image"


# =========================
# CART
# =========================
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        return sum(item.total_price() for item in self.items.all())

    def __str__(self):
        return f"{self.user}'s Cart"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def total_price(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


# =========================
# ORDER
# =========================
class Order(models.Model):

    PAYMENT_METHODS = (
        ("cod", "Cash on Delivery"),
        ("qr", "QR Payment"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    PAYMENT_STATUS = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_paid = models.BooleanField(default=False)

    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default="pending")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    qr_screenshot = models.ImageField(
        upload_to="payment_qr/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def update_total(self):
        self.total_amount = sum(item.total_price() for item in self.items.all())
        self.save()

    def __str__(self):
        return f"Order #{self.id}"
    


# =========================
# CUSTOM ORDER
# =========================
class CustomOrder(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_READY = "ready"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_READY, "Ready"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="custom_orders")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_orders")

    agreed_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Set by owner once the custom order is quoted/approved"
    )

    kurtha_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    
    alt_phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=250)

    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    delivery_date = models.DateField(blank=True, null=True)

    order_details = models.TextField(blank=True, null=True)
    additional_instructions = models.TextField(blank=True, null=True)

    bust = models.CharField(max_length=20, blank=True, null=True)
    waist = models.CharField(max_length=20, blank=True, null=True)
    hip = models.CharField(max_length=20, blank=True, null=True)
    height = models.CharField(max_length=20, blank=True, null=True)

    reference_image = models.ImageField(
        upload_to='custom_orders/',
        null=True,
        blank=True,
        validators=[validate_image_size]
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    is_archived_by_user = models.BooleanField(default=False)
    is_deleted_by_owner = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kurtha_name}"

    @property
    def total_quantity(self):
        return self.quantity


# =========================
# CUSTOM ORDER IMAGES
# =========================
class CustomOrderImage(models.Model):
    custom_order = models.ForeignKey(CustomOrder, on_delete=models.CASCADE, related_name="images")

    image = models.ImageField(
        upload_to="custom_orders/",
        validators=[validate_image_size]
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.custom_order.kurtha_name}"


# =========================
# CHAT MESSAGE
# =========================
class Message(models.Model):
    custom_order = models.ForeignKey(CustomOrder, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)

    content = models.TextField(blank=True)

    image = models.ImageField(
        upload_to="chat_images/",
        blank=True,
        null=True,
        validators=[validate_image_size]
    )

    is_read = models.BooleanField(default=False)

    read_at = models.DateTimeField(blank=True, null=True)

    is_delivered = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["custom_order", "created_at"]),  # 🚀 faster chat loading
        ]

    def __str__(self):
        return f"{self.sender} -> Order {self.custom_order.id}"
    
# =========================
# SAFE FILE DELETE
# =========================
def safe_delete(file_field):
    if file_field:
        try:
            if os.path.isfile(file_field.path):
                os.remove(file_field.path)
        except Exception as e:
            print(f"File delete error: {e}")

@receiver(post_delete, sender=CustomOrderImage)
def delete_custom_order_image(sender, instance, **kwargs):
    safe_delete(instance.image)


@receiver(post_delete, sender=Message)
def delete_chat_image(sender, instance, **kwargs):
    safe_delete(instance.image)


@receiver(post_delete, sender=ProductImage)
def delete_product_image(sender, instance, **kwargs):
    safe_delete(instance.image)


class Notification(models.Model):
    TYPE_CHAT = "chat"
    TYPE_ORDER = "order"

    TYPE_CHOICES = (
        (TYPE_CHAT, "Chat"),
        (TYPE_ORDER, "Order"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    message = models.TextField()

    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_CHAT)

    custom_order = models.ForeignKey(
        CustomOrder,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    chat_message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


# Wishlist
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    seen = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
    
# ============ Notifications Orders =========== #

@receiver(post_save, sender=Order)
def notify_owner_new_order(sender, instance, created, **kwargs):
    if created:
        owner = None

        # try to find business owner from products in order
        first_item = instance.items.first()
        if first_item:
            product = first_item.product
            if product.business and product.business.owner:
                owner = product.business.owner

        if owner:
            Notification.objects.create(
                user=owner,
                message=f"New order #{instance.id} placed via {instance.payment_method.upper()}",
                notification_type="order",
                custom_order=None
            )


# =========================
# ORDER SYSTEM
# =========================
class Order(models.Model):
    DELIVERY_ZONES = (
        ("inside", "Inside Kathmandu Valley (Rs. 120)"),
        ("outside", "Outside Kathmandu Valley (Rs. 180)"),
    )

    PAYMENT_METHODS = (
        ("cod", "Cash on Delivery"),
        ("qr", "QR Payment"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending Approval"),
        ("approved", "Approved & Processing"),
        ("shipped", "Dispatched / In Transit"),
        ("completed", "Delivered & Closed"),
        ('refund_processing', 'Refund Processing'),            
        ('refunded', 'Refunded'),
    )


    PAYMENT_STATUS = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    address = models.TextField()
    delivery_zone = models.CharField(max_length=20, choices=DELIVERY_ZONES, default="inside")
    shipping_charge = models.DecimalField(max_digits=6, decimal_places=2, default=120.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default="pending")
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default="pending")

    qr_screenshot = models.ImageField(upload_to="payment_qr/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def update_total(self):
        import decimal
        # 1. Calculate subtotal of items
        subtotal = sum(item.total_price() for item in self.items.all())
        
        # 2. Force conversion of both numbers to decimal.Decimal to completely prevent type errors
        subtotal_decimal = decimal.Decimal(str(subtotal))
        shipping_decimal = decimal.Decimal(str(self.shipping_charge))
        
        # 3. Add them together safely and commit to database
        self.total_amount = subtotal_decimal + shipping_decimal
        self.save()


class OrderItem(models.Model):
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def total_price(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.product} ({self.quantity})"


@receiver(post_save, sender=Order)
def notify_order_status_changes(sender, instance, created, **kwargs):
    """
    Handles automatic notification cycles:
    1. Finds the store owner directly to alert them of new pending orders.
    2. Triggers an alert back to the customer when the status updates.
    """
    if created:
        # Look for the single owner by searching for a staff member 
        # or filtering your UserProfile role setup
        owner = User.objects.filter(is_staff=True).first()
        
        # Alternative fallback: if you use your profile roles strictly instead:
        # owner_profile = UserProfile.objects.filter(role="owner").first()
        # owner = owner_profile.user if owner_profile else None

        if owner:
            Notification.objects.create(
                user=owner,
                message=f"New Pending Order #DK-{instance.id} placed by {instance.user.username}. Action required.",
                notification_type="order"
            )
    else:
        Notification.objects.create(
            user=instance.user,
            message=f"Your order #DK-{instance.id} tracking state has been updated to: {instance.get_status_display()}.",
            notification_type="order"
        )

# Inside CustomOrder model, add this field:
agreed_price = models.DecimalField(
    max_digits=10, decimal_places=2, null=True, blank=True,
    help_text="Set by owner once the custom order is quoted/approved"
)


# Inside Product model, add this field:
cost_price = models.DecimalField(
    max_digits=10, decimal_places=2, null=True, blank=True,
    help_text="Owner's cost per unit — used for profit margin calculation"
)

# =========================
# EXPENSES
# =========================
class Expense(models.Model):
    CATEGORY_CHOICES = (
        ("materials", "Raw Materials"),
        ("wages", "Wages / Labor"),
        ("rent", "Rent"),
        ("utilities", "Utilities"),
        ("marketing", "Marketing"),
        ("misc", "Miscellaneous"),
    )

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expenses")
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="misc")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True, null=True)
    receipt = models.ImageField(upload_to="expenses/", blank=True, null=True)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.title} - Rs {self.amount}"
