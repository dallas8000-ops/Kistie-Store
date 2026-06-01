


from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from . import views

if settings.ENABLE_ADMIN:
    admin.site.site_header = 'Kistie Store'
    admin.site.site_title = 'Kistie Admin'
    admin.site.index_title = 'Store operations'

urlpatterns = [
    path('health/', views.health, name='health'),
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('shop/product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('contact/', views.contact, name='contact'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('staff/login/', views.staff_login_view, name='staff_login'),
    path('logout/', views.logout_view, name='logout'),
    path('about/', views.about, name='about'),
    path('terms/', views.terms_of_service, name='terms'),
    path('catalog/', views.catalog, name='catalog'),
    path('account/orders/', views.order_history, name='order_history'),
    path('order/track/', views.order_track, name='order_track'),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/audit-log/', views.admin_audit_log, name='admin_audit_log'),
    path('catalog/image/<path:image_name>/', views.catalog_image, name='catalog_image'),
    path('inventory/', views.legacy_inventory_redirect),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('api/internal/order-status/', views.pesapal_ipn_callback, name='pesapal_ipn_callback'),
    path('order/pesapal/callback/', views.pesapal_callback, name='pesapal_callback'),
    path('api/chat/', views.api_chat, name='api_chat'),
    path('api/size-recommend/', views.api_size_recommend, name='api_size_recommend'),
    path('api/fit-recommend/', views.api_fit_recommend, name='api_fit_recommend'),
    path('api/ai/describe/', views.api_ai_describe, name='api_ai_describe'),
    path('api/inventory/', include('inventory.urls')),
    path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.ENABLE_ADMIN:
    urlpatterns.append(path('admin/', admin.site.urls))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
