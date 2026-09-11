from django.contrib import admin

from .models import (
    UserProfile,
    Business,
    Product,
    ProductImage,
    Cart,
    CartItem,
    Order,
    OrderItem,
    CustomOrder,
    Message,
    Category,
    ProductType,
)

# =========================
# USER PROFILE
# =========================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone']
    search_fields = ['user__username', 'phone']
    list_filter = ['role']


# =========================
# BUSINESS
# =========================
@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'address']
    search_fields = ['name', 'address']
    list_filter = ['created_at']


# =========================
# PRODUCT IMAGE INLINE
# =========================
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ['image']
    can_delete = True


# =========================
# PRODUCT
# =========================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'is_available', 'business']
    search_fields = ['name', 'description']
    list_filter = ['is_available', 'business']
    inlines = [ProductImageInline]


# =========================
# PRODUCT IMAGE
# =========================
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product']


# =========================
# CART
# =========================
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity']


# =========================
# ORDER
# =========================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'user',
        'total_amount',
        'payment_method',
        'payment_status',
        'status',
        'created_at'
    ]

    list_filter = [
        'status',
        'payment_method',
        'payment_status'
    ]

    search_fields = ['user__username']

    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity']


# =========================
# MESSAGE INLINE
# =========================
class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False

    readonly_fields = (
        "sender",
        "content",
        "image",
        "created_at",
        "is_read",
    )

    fields = (
        "sender",
        "content",
        "image",
        "created_at",
        "is_read",
    )


# =========================
# CUSTOM ORDER
# =========================
@admin.register(CustomOrder)
class CustomOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'kurtha_name',
        'user',
        'owner',
        'status',
        'quantity',
        'created_at'
    ]

    list_filter = ['status']
    search_fields = [
        'kurtha_name',
        'user__username',
        'owner__username'
    ]

    inlines = [MessageInline]


# =========================
# MESSAGE
# =========================
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'custom_order',
        'sender',
        'short_message',
        'is_read',
        'created_at',
    )

    search_fields = (
        'sender__username',
        'content',
        'custom_order__kurtha_name',
    )

    list_filter = (
        'is_read',
        'created_at',
    )

    readonly_fields = (
        'custom_order',
        'sender',
        'content',
        'image',
        'is_read',
        'created_at',
    )

    def short_message(self, obj):
        if obj.content:
            return obj.content[:80]
        return "(Image Only)"

    short_message.short_description = "Message"


# =========================
# CATEGORY
# =========================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']
    prepopulated_fields = {"slug": ("name",)}


# =========================
# PRODUCT TYPE
# =========================
@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category']
    search_fields = ['name']
    list_filter = ['category']