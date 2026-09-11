from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.db.models import Q, Sum, Count, Prefetch, Max, F
from django.db.models import Case, IntegerField, Value, When
import requests
from django.http import JsonResponse,  HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Product, Notification, Category
from django.db.models.functions import Greatest
from .forms import CustomUserCreationForm
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .utils.recommender import get_similar_products
from .forms import ReviewForm
from .models import ProductReview
from .models import Wishlist
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse
from .models import Expense
import openpyxl
import json
from django.utils.safestring import mark_safe
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from io import BytesIO
from reportlab.platypus import Image
from django.contrib.staticfiles import finders
from PIL import Image as PILImage, ImageDraw



from .models import (
    Product, CustomOrder, Order, Cart, CartItem,
    UserProfile, OrderItem, Message, Business,
    CustomOrderImage
)

User = get_user_model()


# =========================
# HOME
# =========================
def home(request):
    products = Product.objects.filter(is_available=True).select_related('business')

    query = request.GET.get('q')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass

    sort = request.GET.get('sort')

    if sort == 'low':
        products = products.order_by('price')
    elif sort == 'high':
        products = products.order_by('-price')
    elif sort == 'new':
        products = products.order_by('-created_at')

    not_available = False
    if (min_price or max_price) and not products.exists():
        not_available = True

    return render(request, 'DesiKnot_App/home.html', {
        'products': products,
        'query': query,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
        'not_available': not_available,
    })


def about(request):
    return render(request, 'DesiKnot_App/about.html')


def logo_view(request):
    return render(request, 'DesiKnot_App/logo_view.html')


# =========================
# AUTH
# =========================
def register(request):
    form = CustomUserCreationForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully!")
            return redirect('login')
        messages.error(request, "Please correct the errors.")

    return render(request, 'DesiKnot_App/register.html', {'form': form})


def user_login(request):
    next_page = request.GET.get('next')

    if request.method == 'POST':
        next_page = request.POST.get('next')

        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )

        if user:
            login(request, user)
            
            return redirect(next_page or 'home')

        messages.error(request, "Invalid login credentials.")

    return render(request, 'DesiKnot_App/registration/login.html', {'next': next_page})


def user_logout(request):
    logout(request)
    return redirect('home')


# =========================
# PRODUCT DETAIL (PROFESSIONAL)
# =========================

def product_detail(request, slug):

    product = get_object_or_404(
        Product.objects.select_related('business'),
        slug=slug
    )

    # =========================
    # REVIEWS (FIXED LOCATION)
    # =========================

    reviews = product.reviews.select_related('user')

    avg_rating = reviews.aggregate(avg=Sum('rating'))['avg'] or 0
    review_count = reviews.count()

    if request.method == "POST" and request.user.is_authenticated:
        form = ReviewForm(request.POST)

        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            return redirect('product_detail', slug=product.slug)

    else:
        form = ReviewForm()

def product_detail(request, slug):

    product = get_object_or_404(
        Product,
        slug=slug
    )
    # =========================
    # RECOMMENDATION SYSTEM
    # =========================

    recommended_products = []

    try:
        all_products = list(
            Product.objects.filter(
                category=product.category,
                is_available=True
            ).exclude(
                id=product.id
            )
        )

        if all_products:

            product_data = []

            for p in all_products:

                business_name = (
                    p.business.name
                    if p.business
                    else ""
                )

                feature_text = " ".join([
                    str(p.name or ""),
                    str(p.description or ""),
                    str(business_name),
                    str(p.category or "")
                ])

                product_data.append(feature_text)

            current_business_name = (
                product.business.name
                if product.business
                else ""
            )

            current_product_text = " ".join([
                str(product.name or ""),
                str(product.description or ""),
                str(current_business_name),
                str(product.category or "")
            ])

            product_data.append(current_product_text)

            vectorizer = CountVectorizer(
                stop_words="english"
            )

            vectors = vectorizer.fit_transform(
                product_data
            )

            similarity = cosine_similarity(vectors)

            current_index = len(product_data) - 1

            similarity_scores = list(
                enumerate(
                    similarity[current_index][:-1]
                )
            )

            similarity_scores.sort(
                key=lambda x: x[1],
                reverse=True
            )

            top_indexes = [
                index
                for index, score in similarity_scores[:3]
            ]

            recommended_products = [
                all_products[index]
                for index in top_indexes
            ]

    except Exception as e:
        print("Recommendation Error:", e)
        recommended_products = []


    # =========================
    # RECENTLY VIEWED
    # =========================

    recently_viewed = request.session.get(
        "recently_viewed",
        []
    )

    if not isinstance(recently_viewed, list):
        recently_viewed = []

    if product.id in recently_viewed:
        recently_viewed.remove(product.id)

    recently_viewed.insert(0, product.id)

    request.session["recently_viewed"] = recently_viewed[:10]


    # =========================
    # RELATED PRODUCTS
    # =========================

    related_products = Product.objects.filter(
        business=product.business
    ).exclude(
        id=product.id
    )[:4]


    # =========================
    # RETURN PAGE
    # =========================

    return render(
        request,
        "DesiKnot_App/product_detail.html",
        {
            "product": product,
            "recommended_products": recommended_products,
            "related_products": related_products,
        }
    )

# =========================
# PROFILE
# =========================
@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST" and request.FILES.get("profile_image"):
        profile.profile_image = request.FILES["profile_image"]
        profile.save()
        return redirect("profile")

    return render(request, "DesiKnot_App/profile.html", {
        "user": request.user,
        "profile": profile
    })


@login_required
def edit_profile(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()

        profile.phone = request.POST.get('phone', '')

        if request.FILES.get('profile_image'):
            profile.profile_image = request.FILES['profile_image']

        profile.save()

        messages.success(request, "Profile updated successfully!")
        return redirect('profile')

    return render(request, 'DesiKnot_App/edit_profile.html', {
        'user': user,
        'profile': profile
    })


# =========================
# ORDERS 
# =========================
@login_required
def my_orders(request):
    Notification.objects.filter(
        user=request.user,
        notification_type='order',
        is_read=False
    ).update(is_read=True)

    orders = Order.objects.filter(user=request.user)\
    .prefetch_related('items__product')\
    .order_by('-updated_at')

    for order in orders:
        order.can_cancel = order.status in ['pending', 'approved']

    custom_orders = CustomOrder.objects.filter(user=request.user)\
        .prefetch_related('images')\
        .order_by('-created_at')

    return render(request, 'DesiKnot_App/my_orders.html', {
        'orders': orders,
        'custom_orders': custom_orders,
    })

# =========================
# CART
# =========================
@login_required
def cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product')

    if request.method == "POST":
        for key, value in request.POST.items():
            if key.startswith("quantity_"):
                product_id = key.split("_")[1]

                try:
                    quantity = int(value)
                except ValueError:
                    quantity = 1

                cart_item = CartItem.objects.get(
                    cart=cart,
                    product_id=product_id
                )
                cart_item.quantity = quantity
                cart_item.save()

        if request.POST.get("action") == "checkout":
            return redirect("checkout")

        messages.success(request, "Cart updated successfully!")
        return redirect("cart")

    # =========================
    # CALCULATE CART SUBTOTAL
    # =========================
    products_in_cart = []
    total = 0

    for item in items:
        subtotal = item.product.discounted_price * item.quantity

        products_in_cart.append({
            'product': item.product,
            'quantity': item.quantity,
            'subtotal': subtotal,
        })

        total += subtotal

    return render(request, 'DesiKnot_App/cart.html', {
        'products_in_cart': products_in_cart,
        'total': total
    })


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        item.quantity += 1

    item.save()
    return redirect('cart')

# =========================
# CHECKOUT
# =========================
@login_required
def checkout(request):

    cart, _ = Cart.objects.get_or_create(
        user=request.user
    )

    items = cart.items.select_related(
        'product'
    )

    if not items.exists():
        messages.error(
            request,
            "Your cart is empty."
        )
        return redirect('cart')

    items_with_subtotal = []
    total = 0

    for item in items:

        subtotal = (
    item.product.discounted_price * item.quantity
    )
        items_with_subtotal.append({
            'product': item.product,
            'quantity': item.quantity,
            'subtotal': subtotal,
        })

        total += subtotal

    # =========================
    # PLACE ORDER
    # =========================
    if request.method == 'POST':

        payment_method = request.POST.get(
            'payment_method',
            'cod'
        )

        delivery_zone = request.POST.get('delivery_zone', 'inside')
        shipping_charge = 180 if delivery_zone == 'outside' else 120



        order = Order.objects.create(
            user=request.user,
            payment_method=payment_method,
            status='pending',
            payment_status='pending'
        )

        # create order items
        for item in items:

            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity
            )

        order.update_total()

        # =========================
        # SEND NOTIFICATIONS
        # =========================
        payment_text = (
            "Cash on Delivery"
            if payment_method == "cod"
            else "QR Payment"
        )

        owner_profile = UserProfile.objects.filter(role='owner').first()

        if owner_profile:

            Notification.objects.create(
                user=owner_profile.user,
                message=(
                    f"🛒 New Order #{order.id} "
                    f"placed by "
                    f"{request.user.username} | "
                    f"Payment: {payment_text} | "
                    f"Total: Rs {order.total_amount}"
                ),
                notification_type="order"
            )
        
    

        # =========================
        # CASH ON DELIVERY
        # =========================

        if payment_method == "cod":

            return redirect(
                "payment_qr",
                order.id
            )

        # =========================
        # QR PAYMENT
        # =========================

        elif payment_method == "qr":

            return redirect(
                "payment_qr",
                order.id
            )

    return render(
        request,
        'DesiKnot_App/checkout.html',
        {
            'items': items_with_subtotal,
            'total': total
        }
    )

# =========================
# CUSTOM ORDER STEP 1
# =========================
@login_required
def custom_order_step1(request):
    if request.method == 'POST':
        request.session['custom_order'] = {
            key: request.POST.get(key)
            for key in request.POST
            if key != 'csrfmiddlewaretoken'
        }
        return redirect('custom_order_step2')

    return render(request, 'DesiKnot_App/custom_order_step1.html')

# =========================
# CUSTOM ORDER STEP 2
# =========================
@login_required
def custom_order_step2(request):
    if 'custom_order' not in request.session:
        return redirect('custom_order_step1')

    if request.method == 'POST':
        data = request.session['custom_order']

        owner_profile = UserProfile.objects.filter(role='owner').first()

        if not owner_profile:
            messages.error(request, "No owner found.")
            return redirect('home')

        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            quantity = 1

        custom_order = CustomOrder.objects.create(
            user=request.user,
            owner=owner_profile.user,

            kurtha_name=data.get('kurtha_name'),
            phone_number=data.get('phone_number'),
            alt_phone_number=data.get('alt_phone_number'),
            address=data.get('address'),

            quantity=quantity,

            bust=request.POST.get('bust'),
            waist=request.POST.get('waist'),
            hip=request.POST.get('hip'),
            height=request.POST.get('height'),

            delivery_date=request.POST.get('delivery_date'),
            order_details=request.POST.get('order_details'),
        )

        # SAVE IMAGES
        for img in request.FILES.getlist('images'):
            CustomOrderImage.objects.create(
                custom_order=custom_order,
                image=img
            )

        # CREATE FIRST MESSAGE
        Message.objects.create(
            custom_order=custom_order,
            sender=request.user,
            content="📝 New custom order placed.",
            is_read=False
        )

        request.session.pop('custom_order', None)

        return redirect('order_chat', custom_order.id)

    return render(request, 'DesiKnot_App/custom_order_step2.html')

# =========================
# CHAT VIEW (FIXED)
# =========================
@login_required
def order_chat(request, order_id):

    custom_order = get_object_or_404(
        CustomOrder.objects.prefetch_related('messages__sender', 'images'),
        id=order_id
    )

    if request.user != custom_order.user and request.user != custom_order.owner:
        return render(request, 'DesiKnot_App/not_authorized.html')

    custom_order.messages.filter(
        is_read=False
    ).exclude(sender_id=request.user.id).update(is_read=True)

    messages_qs = custom_order.messages.select_related('sender').order_by('created_at')

    context = {
        'custom_order': custom_order,
        'messages': messages_qs,
        'status_choices': CustomOrder.STATUS_CHOICES,
        'reference_images': custom_order.images.all()
    }

    if request.user == custom_order.owner:
        return render(request, 'DesiKnot_App/chat/admin_order_chat.html', context)
    else:
        return render(request, 'DesiKnot_App/chat/user_order_chat.html', context)

# =========================
# SEND MESSAGE 
# =========================
@login_required
def send_message(request, order_id):
    custom_order = get_object_or_404(CustomOrder, id=order_id)

    if request.user not in [custom_order.user, custom_order.owner]:
        return redirect('home')

    if request.method == 'POST':
        content = request.POST.get('message', '').strip()
        image = request.FILES.get('image')

        if not content and not image:
            return redirect('order_chat', custom_order.id)

        msg = Message.objects.create(
            custom_order=custom_order,
            sender=request.user,
            content=content,
            image=image,
            is_read=False
        )

        if request.user == custom_order.user:
            receiver = custom_order.owner
        else:
            receiver = custom_order.user

        if receiver:
            Notification.objects.create(
                user=receiver,
                message=f"New message on Order #{custom_order.id}",
                notification_type="chat",
                custom_order=custom_order,
                chat_message=msg
            )

    return redirect('order_chat', custom_order.id)
# =========================
# STATUS UPDATE
# =========================
@login_required
def update_custom_order_status(request, order_id):
    custom_order = get_object_or_404(CustomOrder, id=order_id)

    if not getattr(getattr(request.user, "profile", None), "is_owner", lambda: False)():
        return render(request, 'DesiKnot_App/not_authorized.html')

    if request.method == "POST":
        new_status = request.POST.get("status")

        if new_status in dict(CustomOrder.STATUS_CHOICES):
            custom_order.status = new_status

            price = request.POST.get("agreed_price")
            if price:
                try:
                    custom_order.agreed_price = Decimal(price)
                except:
                    pass

            custom_order.save()

            Message.objects.create(
                custom_order=custom_order,
                sender=request.user,
                content=f"📢 Status updated to {new_status.upper()}",
                is_read=False
            )

    return redirect('order_chat', custom_order.id)

# USER MESSAGES

@login_required
def user_messages(request):

    orders = CustomOrder.objects.filter(
        Q(user=request.user) | Q(owner=request.user)
    ).select_related(
        'user', 'owner'
    ).prefetch_related(
        Prefetch(
            'messages',
            queryset=Message.objects.select_related('sender').order_by('created_at')
        )
    ).annotate(
        unread_count=Count(
            'messages',
            filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
        ),
        last_message_time=Max('messages__created_at')
    )

    query = request.GET.get('q')

    if query:

        orders = orders.annotate(

            relevance=Case(
                When(user__username__icontains=query, then=Value(3)),
                When(owner__username__icontains=query, then=Value(3)),
                When(address__icontains=query, then=Value(2)),
                When(id__icontains=query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).filter(
            Q(user__username__icontains=query) |
            Q(owner__username__icontains=query) |
            Q(address__icontains=query) |
            Q(id__icontains=query)
        ).order_by(
            '-relevance',          
            '-last_message_time',
            '-created_at'
        )

    else:
        orders = orders.order_by(
            '-last_message_time',
            '-created_at'
        )

    search_query = request.GET.get('search', '').strip()

    if search_query:
        users = users.filter(
            username__icontains=search_query
        )

    return render(request, 'DesiKnot_App/user_messages.html', {
        'orders': orders,
        'query': query
    })

# =========================
# ADMIN MESSAGES
# =========================

@login_required
def admin_messages(request):
    if not getattr(getattr(request.user, "profile", None), "is_owner", lambda: False)():
        return render(request, 'DesiKnot_App/not_authorized.html')

    search_query = request.GET.get('search', '').strip()

    messages_qs = Message.objects.select_related('sender').order_by('created_at')

    orders = CustomOrder.objects.filter(
        owner=request.user
    ).prefetch_related(
        Prefetch('messages', queryset=messages_qs)
    ).annotate(
        # count unread messages
        unread_count=Count(
            'messages',
            filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
        ),

        
        last_message_time=Max('messages__created_at')
    ).order_by(
        '-last_message_time',   # NEW messages come FIRST
        '-created_at'           # fallback
    )

    return render(request, 'DesiKnot_App/admin_messages.html', {
        'orders': orders
    })


    
#=============== Categories=================== #

def category_products(request, slug):
    category = Category.objects.get(slug=slug)
    products = Product.objects.filter(category=category)

    return render(request, "DesiKnot_App/category_products.html", {
        "category": category,
        "products": products
    })


# ============= Wishlist ==================

@login_required
def toggle_wishlist(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    wishlist_item = Wishlist.objects.filter(
        user=request.user,
        product=product
    ).first()

    if wishlist_item:

        wishlist_item.delete()

    else:

        Wishlist.objects.create(
            user=request.user,
            product=product,
            seen=False
        )

    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def wishlist_view(request):

    items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product')

    items.update(seen=True)

    return render(
        request,
        "DesiKnot_App/wishlist.html",
        {
            "items": items
        }
    )

def remove_from_cart(request, product_id):
    cart = Cart.objects.get(user=request.user)
    item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    item.delete()
    return redirect('cart')


#============ PAYMENT QR ======================#

@login_required
def payment_qr(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )


    if request.GET.get('skip') == '1':
        order.delete()
        messages.info(request, "Order cancelled. Continue shopping anytime.")
        return redirect("home")

    if request.method == "POST":

        if order.payment_status == "completed":
            messages.info(request, "This payment was already confirmed.")
            return redirect("my_orders")

        screenshot = request.FILES.get('qr_screenshot')
        if not screenshot:
            messages.error(request, "Please upload your payment screenshot before submitting.")
            return redirect("payment_qr", order_id=order.id)

        order.qr_screenshot = screenshot

        order.payment_status = "processing"
        order.status = "pending"
        order.save()

        CartItem.objects.filter(cart__user=request.user).delete()

        owner_profile = UserProfile.objects.filter(role='owner').first()

        if owner_profile:
            Notification.objects.create(
                user=owner_profile.user,
                message=(
                    f"📸 New QR Payment screenshot uploaded for Order #{order.id} "
                    f"by customer {request.user.username}. Needs your verification! | "
                    f"Total Amount: Rs {order.total_amount}"
                ),
                notification_type="order"
            )

        messages.success(
            request,
            "Payment proof submitted successfully! The owner will verify your receipt shortly."
        )
        return redirect("my_orders")

    context = {
        "order": order,
        "total_amount": order.total_amount,
    }

    return render(
        request,
        "DesiKnot_App/payment_qr.html",
        context
    )

@login_required
def owners_orders(request):
    if not getattr(getattr(request.user, "profile", None), "is_owner", lambda: False)():
        return HttpResponseForbidden("Not allowed")

    Notification.objects.filter(
        user=request.user,
        notification_type='order',
        is_read=False
    ).update(is_read=True)

    orders = Order.objects.all().prefetch_related('items__product', 'user').order_by('-updated_at')

    return render(request, 'DesiKnot_App/owners_orders.html', {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
        'pending_count': orders.filter(status='pending').count(),
        'cancel_request_count': orders.filter(status='cancellation_requested').count(),
        'completed_count': orders.filter(status='completed').count(),
    })

@login_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if not getattr(getattr(request.user, "profile", None), "is_owner", lambda: False)():
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        new_status = request.POST.get("status")

        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status

            order.save()
        else:
            messages.error(request, "Invalid status selected.")

    return redirect("owners_orders")



@login_required
def request_cancellation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status not in ['pending', 'approved']:
        messages.error(request, "This order can no longer be cancelled.")
        return redirect("my_orders")

    order.status = 'cancellation_requested'
    order.save()

    owner_profile = UserProfile.objects.filter(role='owner').first()
    if owner_profile:
        Notification.objects.create(
            user=owner_profile.user,
            message=(
                f"🚨 Order #{order.id} — Cancellation requested by "
                f"{request.user.username} | "
                f"Payment: {order.payment_method.upper()} | "
                f"Total: Rs {order.total_amount}"
            ),
            notification_type="order"
        )

    messages.success(request, "Cancellation requested. The owner will review it shortly.")
    return redirect("my_orders")


@login_required
def approve_cancellation(request, order_id):
    if not getattr(getattr(request.user, "profile", None), "is_owner", lambda: False)():
        return HttpResponseForbidden("Not allowed")

    order = get_object_or_404(Order, id=order_id)

    if order.status != 'cancellation_requested':
        messages.error(request, "No pending cancellation request for this order.")
        return redirect("owners_orders")

    order.status = 'refund_processing'
    order.save()

    Notification.objects.create(
        user=order.user,
        message=(
            f"💚 Your cancellation request for Order #DK-{order.id} has been approved! "
            f"Your refund of Rs {order.total_amount} will be sent to your eSewa wallet shortly. "
            f"Please allow up to 24 hours."
        ),
        notification_type="order"
    )

    messages.success(request, f"Order #{order.id} cancelled. Refund marked as processing. Customer notified.")
    return redirect("owners_orders")

@login_required
def reject_cancellation(request, order_id):
    if not getattr(getattr(request.user, "profile", None), "is_owner", lambda: False)():
        return HttpResponseForbidden("Not allowed")

    order = get_object_or_404(Order, id=order_id)

    if order.status != 'cancellation_requested':
        messages.error(request, "No pending cancellation request for this order.")
        return redirect("owners_orders")

    order.status = 'approved'
    order.save()

    Notification.objects.create(
        user=order.user,
        message=(
            f"❌ Your cancellation request for Order #{order.id} was rejected by the owner. "
            f"Your order is still active. Contact us if you have questions."
        ),
        notification_type="order"
    )

    messages.info(request, f"Cancellation for Order #{order.id} rejected. Order is active again.")
    return redirect("owners_orders")


@login_required
def mark_refund_done(request, order_id):
    if not getattr(getattr(request.user, "profile", None), "is_owner", lambda: False)():
        return HttpResponseForbidden("Not allowed")

    order = get_object_or_404(Order, id=order_id)

    if order.status != 'cancelled':
        messages.error(request, "Order must be cancelled before marking refund.")
        return redirect("owners_orders")

    order.status = 'refunded'
    order.save()

    Notification.objects.create(
        user=order.user,
        message=(
            f"💚 Your refund for Order #{order.id} has been processed via eSewa. "
            f"Please check your eSewa wallet. Contact us if you haven't received it."
        ),
        notification_type="order"
    )

    messages.success(request, f"Refund for Order #{order.id} marked as done. Customer notified.")
    return redirect("owners_orders")


# =========================
# ACCOUNTING HELPERS
# =========================
def _is_owner(user):
    return getattr(getattr(user, "profile", None), "is_owner", lambda: False)()


# =========================
# ACCOUNTING DASHBOARD
# =========================
@login_required
def accounting_dashboard(request):
    if not _is_owner(request.user):
        return HttpResponseForbidden("Not allowed")

    period = request.GET.get('period', 'month')
    today = timezone.now().date()

    if period == 'today':
        start_date = today
    elif period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
    else:  
        start_date = today.replace(day=1)

    orders = Order.objects.filter(
        created_at__date__gte=start_date,
    ).exclude(status__in=['cancelled', 'refunded'])

    order_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0

    custom_orders = CustomOrder.objects.filter(
        created_at__date__gte=start_date,
        agreed_price__isnull=False
    ).exclude(status='rejected')

    custom_revenue = custom_orders.aggregate(total=Sum('agreed_price'))['total'] or 0

    total_revenue = order_revenue + custom_revenue

    expenses = Expense.objects.filter(owner=request.user, date__gte=start_date)
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0

    net_profit = total_revenue - total_expenses

    pending_payment = Order.objects.filter(
        payment_status='pending'
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    refunded = Order.objects.filter(
        status='refunded',
        created_at__date__gte=start_date
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Chart data: daily revenue trend
    daily_orders = orders.annotate(day=TruncDate('created_at')).values('day').annotate(
        total=Sum('total_amount')
    ).order_by('day')

    chart_labels = [d['day'].strftime('%b %d') for d in daily_orders]
    chart_values = [float(d['total']) for d in daily_orders]

    context = {
        'period': period,
        'total_revenue': total_revenue,
        'order_revenue': order_revenue,
        'custom_revenue': custom_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'pending_payment': pending_payment,
        'refunded': refunded,
        'order_count': orders.count(),
        'custom_order_count': custom_orders.count(),
        'chart_labels': chart_labels,
        'chart_values': chart_values,
    }

    return render(request, 'DesiKnot_App/accounting_dashboard.html', context)


# =========================
# LEDGER 
# =========================
@login_required
def accounting_ledger(request):
    if not _is_owner(request.user):
        return HttpResponseForbidden("Not allowed")

    ledger = []

    for o in Order.objects.exclude(status__in=['cancelled']).select_related('user'):
        ledger.append({
            'date': o.created_at,
            'type': 'Order',
            'reference': f"#DK-{o.id}",
            'party': o.user.username,
            'amount': o.total_amount,
            'status': o.get_status_display(),
            'is_credit': True,
        })

    for c in CustomOrder.objects.filter(agreed_price__isnull=False).exclude(status='rejected').select_related('user'):
        ledger.append({
            'date': c.created_at,
            'type': 'Custom Order',
            'reference': f"CO-{c.id}",
            'party': c.user.username,
            'amount': c.agreed_price,
            'status': c.get_status_display(),
            'is_credit': True,
        })

    for e in Expense.objects.filter(owner=request.user):
        ledger.append({
            'date': e.date,
            'type': f'Expense ({e.get_category_display()})',
            'reference': e.title,
            'party': '-',
            'amount': e.amount,
            'status': '-',
            'is_credit': False,
        })

    def sort_key(entry):
        d = entry['date']
        if hasattr(d, 'date'):  # it's a datetime, convert to date
            return d.date()
        return d  # already a date

    ledger.sort(key=sort_key, reverse=True)
    
    return render(request, 'DesiKnot_App/accounting_ledger.html', {'ledger': ledger})


# =========================
# EXPENSES CRUD (minimal)
# =========================
@login_required
def expense_list(request):
    if not _is_owner(request.user):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        Expense.objects.create(
            owner=request.user,
            title=request.POST.get('title'),
            category=request.POST.get('category', 'misc'),
            amount=Decimal(request.POST.get('amount', 0)),
            note=request.POST.get('note', ''),
            date=request.POST.get('date') or timezone.now().date(),
            receipt=request.FILES.get('receipt')
        )
        messages.success(request, "Expense recorded.")
        return redirect('expense_list')

    expenses = Expense.objects.filter(owner=request.user)
    return render(request, 'DesiKnot_App/expense_list.html', {
        'expenses': expenses,
        'categories': Expense.CATEGORY_CHOICES,
    })


@login_required
def expense_delete(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, owner=request.user)
    expense.delete()
    messages.success(request, "Expense deleted.")
    return redirect('expense_list')


# =========================
# EXCEL EXPORT
# =========================
@login_required
def export_ledger_excel(request):
    if not _is_owner(request.user):
        return HttpResponseForbidden("Not allowed")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ledger"
    ws.append(["Date", "Type", "Reference", "Party", "Amount", "Status"])

    rows = []
    for o in Order.objects.exclude(status='cancelled'):
        rows.append([o.created_at.strftime('%Y-%m-%d'), "Order", f"DK-{o.id}", o.user.username, float(o.total_amount), o.status])
    for c in CustomOrder.objects.filter(agreed_price__isnull=False):
        rows.append([c.created_at.strftime('%Y-%m-%d'), "Custom Order", f"CO-{c.id}", c.user.username, float(c.agreed_price), c.status])
    for e in Expense.objects.filter(owner=request.user):
        rows.append([e.date.strftime('%Y-%m-%d'), "Expense", e.title, "-", -float(e.amount), "-"])

    rows.sort(key=lambda r: r[0], reverse=True)
    for r in rows:
        ws.append(r)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="desiknot_ledger.xlsx"'
    wb.save(response)
    return response


# =========================
# USER ACTIVITY DASHBOARD
# =========================
@login_required
def user_activity_dashboard(request):
    if not _is_owner(request.user):
        return HttpResponseForbidden("Not allowed")

    now = timezone.now()
    online_threshold = now - timedelta(minutes=5)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_users = User.objects.count()

    online_now = UserProfile.objects.filter(last_seen__gte=online_threshold).count()

    new_today = User.objects.filter(date_joined__gte=today_start).count()
    new_this_week = User.objects.filter(date_joined__gte=week_start).count()
    new_this_month = User.objects.filter(date_joined__gte=month_start).count()

    role_breakdown = UserProfile.objects.values('role').annotate(count=Count('id'))

    # Signup trend, last 30 days
    signup_trend = User.objects.filter(
        date_joined__gte=now - timedelta(days=30)
    ).annotate(day=TruncDate('date_joined')).values('day').annotate(
        count=Count('id')
    ).order_by('day')

    chart_labels = [s['day'].strftime('%b %d') for s in signup_trend]
    chart_values = [s['count'] for s in signup_trend]

    online_users = UserProfile.objects.filter(
        last_seen__gte=online_threshold
    ).select_related('user').order_by('-last_seen')

    recently_active = UserProfile.objects.filter(
        last_seen__gte=now - timedelta(hours=24),
        last_seen__lt=online_threshold
    ).select_related('user').order_by('-last_seen')[:20]

    for p in list(online_users) + list(recently_active):
        if p.user.is_superuser:
            p.display_role = 'admin'
        else:
            p.display_role = p.role

    context = {
        'total_users': total_users,
        'online_now': online_now,
        'new_today': new_today,
        'new_this_week': new_this_week,
        'new_this_month': new_this_month,
        'role_breakdown': role_breakdown,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'online_users': online_users,
        'recently_active': recently_active,
    }

    return render(request, 'DesiKnot_App/user_activity_dashboard.html', context)


# =========================
# CIRCULAR LOGO HELPER
# =========================
def _circular_logo_buffer(path, size=300):
    """
    Crops the source image to a square, masks it into a circle,
    and returns an in-memory PNG buffer with transparency —
    ready to drop into a ReportLab PDF.
    """
    im = PILImage.open(path).convert("RGBA")

    # Crop to a centered square first
    w, h = im.size
    min_side = min(w, h)
    left = (w - min_side) // 2
    top = (h - min_side) // 2
    im = im.crop((left, top, left + min_side, top + min_side))
    im = im.resize((size, size), PILImage.LANCZOS)

    # Circular mask
    mask = PILImage.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    im.putalpha(mask)

    buf = BytesIO()
    im.save(buf, format="PNG")
    buf.seek(0)
    return buf


# =========================
# PDF INVOICE
# =========================
@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    is_owner = _is_owner(request.user)
    if request.user != order.user and not is_owner:
        return HttpResponseForbidden("Not allowed")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm
    )

    EMERALD = colors.HexColor("#0D3626")
    GOLD = colors.HexColor("#C9A13B")
    MUTED = colors.HexColor("#5C6560")
    LIGHT_BG = colors.HexColor("#EEF4EF")

    styles = getSampleStyleSheet()
    brand_style = ParagraphStyle('Brand', parent=styles['Title'], fontName='Helvetica-Bold',
                                  fontSize=26, textColor=EMERALD, spaceAfter=0)
    tagline_style = ParagraphStyle('Tagline', parent=styles['Normal'], fontName='Helvetica-Oblique',
                                    fontSize=9, textColor=MUTED)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontName='Helvetica-Bold',
                                  fontSize=9, textColor=GOLD)
    value_style = ParagraphStyle('Value', parent=styles['Normal'], fontName='Helvetica',
                                  fontSize=10, textColor=colors.HexColor("#16241C"))
    invoice_title_style = ParagraphStyle('InvTitle', parent=styles['Normal'], fontName='Helvetica-Bold',
                                          fontSize=16, textColor=colors.white, alignment=TA_RIGHT)
    invoice_sub_style = ParagraphStyle('InvSub', parent=styles['Normal'], fontName='Helvetica',
                                        fontSize=10, textColor=colors.HexColor("#D7E4DC"), alignment=TA_RIGHT)

    elements = []

    # ---------- HEADER (with logo) ----------
    logo_path = finders.find('images/logo.JPG')

    if logo_path:
        circular_logo_buf = _circular_logo_buffer(logo_path)
        logo_img = Image(circular_logo_buf, width=15 * mm, height=15 * mm)
    else:
        logo_img = Paragraph("", tagline_style)  

    brand_block = Table([
        [logo_img, Paragraph("DesiKnot", brand_style)]
    ], colWidths=[18 * mm, 77 * mm])
    brand_block.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    header_table = Table([
        [brand_block, Paragraph("INVOICE", invoice_title_style)],
        [Paragraph("An Online Tailoring and Custom Fashion E-Commerce Platform", tagline_style),
         Paragraph(f"#DK-{order.id}", invoice_sub_style)],
    ], colWidths=[95 * mm, 77 * mm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), EMERALD),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 14),
        ('LEFTPADDING', (0, 0), (0, -1), 14),
        ('RIGHTPADDING', (1, 0), (1, -1), 14),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 14))

    # ---------- BILL TO / ORDER INFO ----------
    info_table = Table([
        [Paragraph("BILLED TO", label_style), Paragraph("ORDER DATE", label_style)],
        [Paragraph(order.user.get_full_name() or order.user.username, value_style),
         Paragraph(order.created_at.strftime('%B %d, %Y'), value_style)],
        [Paragraph(order.address or '-', value_style), Paragraph("PAYMENT METHOD", label_style)],
        [Paragraph("", value_style), Paragraph(order.get_payment_method_display(), value_style)],
    ], colWidths=[95 * mm, 77 * mm])
    info_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 18))

    # ---------- ITEMS TABLE ----------
    data = [["Product", "Qty", "Unit Price", "Subtotal"]]
    for item in order.items.select_related('product'):
        data.append([
            item.product.name,
            str(item.quantity),
            f"Rs {item.product.price:,.2f}",
            f"Rs {item.total_price():,.2f}",
        ])

    items_table = Table(data, colWidths=[85 * mm, 20 * mm, 33 * mm, 34 * mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), EMERALD),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, GOLD),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor("#E3E9E5")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 10))

    # ---------- TOTALS ----------
    subtotal = sum(item.total_price() for item in order.items.all())
    totals_data = [
        ["Subtotal", f"Rs {subtotal:,.2f}"],
        ["Shipping", f"Rs {order.shipping_charge:,.2f}"],
        ["Total", f"Rs {order.total_amount:,.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[142 * mm, 30 * mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 2), (-1, 2), 13),
        ('TEXTCOLOR', (0, 2), (-1, 2), EMERALD),
        ('LINEABOVE', (0, 2), (-1, 2), 1, EMERALD),
        ('TOPPADDING', (0, 2), (-1, 2), 8),
        ('TOPPADDING', (0, 0), (-1, 1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, 1), 4),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 24))

    status_style = ParagraphStyle('Status', parent=styles['Normal'], fontName='Helvetica-Bold',
                                   fontSize=10, textColor=EMERALD)
    elements.append(Paragraph(f"Order Status: {order.get_status_display()}  |  Payment Status: {order.get_payment_status_display()}", status_style))
    elements.append(Spacer(1, 30))

    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E3E9E5")))
    elements.append(Spacer(1, 8))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontName='Helvetica-Oblique',
                                   fontSize=8.5, textColor=MUTED, alignment=TA_CENTER)
    elements.append(Paragraph("Thank you for shopping with DesiKnot — Connecting tradition with modern fashion.", footer_style))

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="DesiKnot_Invoice_DK-{order.id}.pdf"'
    return response