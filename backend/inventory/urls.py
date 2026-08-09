
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet
from django.urls import path
from .payment_views import PaymentCheckoutGateway

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)

urlpatterns = router.urls + [
	path('pay/checkout/', PaymentCheckoutGateway.as_view(), name='pay-checkout'),
]
