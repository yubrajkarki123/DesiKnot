# DesiKnot_App/urls.py

from django.urls import path
from . import views

urlpatterns = [

    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('logo-view/', views.logo_view, name='logo_view'),


    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),


    path('profile/', views.profile_view, name='profile'),

    path('profile/edit/', views.edit_profile, name='edit_profile'),

    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    path('cart/', views.cart, name='cart'),

    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),

    path('checkout/', views.checkout, name='checkout'),

    path('payment-qr/<int:order_id>/', views.payment_qr, name='payment_qr'),

    
    path('custom-order/step1/', views.custom_order_step1, name='custom_order_step1'),
    

    path('custom-order/step2/', views.custom_order_step2, name='custom_order_step2'),
    
    
    path('messages/', views.user_messages, name='user_messages'),
    
    
    path('dashboard/messages/', views.admin_messages, name='admin_messages'),

    
    path('chat/<int:order_id>/', views.order_chat, name='order_chat'),

    
    path('chat/<int:order_id>/send/', views.send_message, name='send_message'),

    path('category/<slug:slug>/', views.category_products, name='category_products'),


    path(
        'custom-order/<int:order_id>/update-status/',
        views.update_custom_order_status,
        name='update_custom_order_status'
    ),

    path('wishlist/', views.wishlist_view, name='wishlist'),

    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),

    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),

    path('my-orders/', views.my_orders, name='my_orders'),

    path('owner/orders/', views.owners_orders, name='owners_orders'),

    path(
        'owner/orders/<int:order_id>/update-status/',
        views.update_order_status,
        name='update_order_status'
    ),

    path('orders/cancel/<int:order_id>/', views.request_cancellation, name='request_cancellation'),

    path('orders/approve-cancel/<int:order_id>/', views.approve_cancellation, name='approve_cancellation'),

    path('orders/reject-cancel/<int:order_id>/', views.reject_cancellation, name='reject_cancellation'),
    
    path('orders/refund-done/<int:order_id>/', views.mark_refund_done, name='mark_refund_done'),

    path('owner/accounting/', views.accounting_dashboard, name='accounting_dashboard'),

    path('owner/accounting/ledger/', views.accounting_ledger, name='accounting_ledger'),

    path('owner/accounting/ledger/export/', views.export_ledger_excel, name='export_ledger_excel'),

    path('owner/expenses/', views.expense_list, name='expense_list'),

    path('owner/expenses/<int:expense_id>/delete/', views.expense_delete, name='expense_delete'),

    path('owner/user-activity/', views.user_activity_dashboard, name='user_activity_dashboard'),

    path('invoice/<int:order_id>/', views.download_invoice, name='download_invoice'),

]