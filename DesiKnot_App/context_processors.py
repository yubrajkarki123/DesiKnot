from .models import Message, Category, Wishlist, Notification
from django.db.models import Q


# =========================
# UNREAD CHAT MESSAGES
# =========================
def unread_messages_count(request):
    if not request.user.is_authenticated:
        return {}

    count = Message.objects.filter(
        is_read=False
    ).filter(
        Q(custom_order__user=request.user) |
        Q(custom_order__owner=request.user)
    ).exclude(sender=request.user).count()

    return {
        'unread_messages_count': count
    }


# =========================
# CATEGORIES
# =========================
def categories_processor(request):
    return {
        "categories": Category.objects.prefetch_related("types").all()
    }


# =========================
# WISHLIST COUNT 
# =========================
def wishlist_processor(request):
    if not request.user.is_authenticated:
        return {
            "wishlist_count": 0
        }

    count = Wishlist.objects.filter(user=request.user).count()

    return {
        "wishlist_count": count
    }


# =========================
# ORDER NOTIFICATIONS COUNT
# =========================
def order_notifications_count(request):
    if not request.user.is_authenticated:
        return {}

    count = Notification.objects.filter(
        user=request.user,
        notification_type='order',
        is_read=False
    ).count()

    return {
        'order_notifications_count': count
    }