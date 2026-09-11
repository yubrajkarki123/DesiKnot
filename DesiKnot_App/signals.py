from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, Notification

@receiver(post_save, sender=Order)
def notify_owner(sender, instance, created, **kwargs):
    if not created:
        return

    # You will later improve this logic
    Notification.objects.create(
        user=instance.user,  # temporary (we will fix owner mapping next step)
        message=f"🛒 New Order #{instance.id} placed",
        notification_type="order"
    )