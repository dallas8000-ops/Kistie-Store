"""Core URL and permission tests.

Synthetic credentials exist only for the ephemeral test database and are not deployment secrets.

When running tests, Django may print WARNING/traceback lines for expected ``403 Forbidden``
responses (admin gate, staff dashboard). Those lines are normal; the tests still pass if the
suite ends with OK.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from decimal import Decimal
import json
from django.test import TestCase
from django.urls import reverse

from inventory.models import Category, Product

# Values used only in test POST payloads / create_user calls (not production).
_PW_SIGNUP = 'StrongPass123!'
_PW_PORTAL_STAFF = 'StrongPortalStaff123!'
_PW_PORTAL_SUPER = 'StrongPortalSu123!'
_PW_BUYER = 'StrongBuyer123!'
_PW_GATE_BUYER = 'StrongBuyerGate123!'
_PW_GATE_PORTAL = 'StrongPortalGate123!'
_PW_GATE_STAFF = 'StrongStaffGate123!'
_PW_GATE_SUPER = 'StrongSuperGate123!'


class AuthRouteSmokeTests(TestCase):
    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_staff_login_page_loads(self):
        response = self.client.get(reverse('staff_login'))
        self.assertEqual(response.status_code, 200)

    def test_signup_page_loads(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)

    def test_signup_creates_user_and_redirects(self):
        response = self.client.post(
            reverse('signup'),
            data={
                'username': 'newuser',
                'password1': _PW_SIGNUP,
                'password2': _PW_SIGNUP,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(get_user_model().objects.filter(username='newuser').count(), 1)


class HealthEndpointTests(TestCase):
    def test_health_json(self):
        response = self.client.get(f"{reverse('health')}?format=json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
        self.assertEqual(response.json()['service'], 'kistie-store')


class ShopRedirectTests(TestCase):
    def test_home_redirects_to_shop(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('shop'))

    def test_catalog_redirects_to_shop(self):
        response = self.client.get(reverse('catalog'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('shop'))

    def test_legacy_inventory_url_redirects_to_shop(self):
        response = self.client.get('/inventory/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('shop'))

    def test_catalog_redirect_preserves_querystring(self):
        response = self.client.get(reverse('catalog'), {'category': '1', 'currency': 'EUR'})
        self.assertEqual(response.status_code, 302)
        location = response.headers.get('Location', '')
        self.assertIn('/shop/', location)
        self.assertIn('category=1', location)
        self.assertIn('currency=EUR', location)


class ShopPageTests(TestCase):
    """Canonical storefront is ``core/shop.html`` (not a separate inventory/catalog page)."""

    def test_shop_renders_with_shop_template(self):
        response = self.client.get(reverse('shop'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/shop.html')

    def test_shop_ajax_returns_json_fragment(self):
        response = self.client.get(
            reverse('shop'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('html', data)
        self.assertIn('total_items', data)

    def test_shop_search_filters_by_vest_keyword(self):
        cat = Category.objects.create(name='Outerwear', description='')
        Product.objects.create(
            name='Navy Check Vest',
            description='Smart layering piece',
            price_usd=Decimal('80.00'),
            price_ugx=Decimal('0'),
            category=cat,
            stock_quantity=2,
            sizes='40',
            color='navy',
        )
        Product.objects.create(
            name='Summer Sandals',
            description='Beach shoes',
            price_usd=Decimal('40.00'),
            price_ugx=Decimal('0'),
            category=cat,
            stock_quantity=2,
            sizes='38',
        )
        response = self.client.get(reverse('shop'), {'q': 'vest'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Navy Check Vest')
        self.assertNotContains(response, 'Summer Sandals')


class ProductDetailPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Dresses', description='')
        cls.product = Product.objects.create(
            name='Test Emerald Dress',
            description='A lovely dress for testing.',
            price_usd=Decimal('99.00'),
            price_ugx=Decimal('0'),
            category=cls.category,
            stock_quantity=5,
            sizes='38,40',
        )

    def test_product_detail_by_slug(self):
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/product_detail.html')
        self.assertContains(response, self.product.name)
        self.assertContains(response, 'application/ld+json')

    def test_product_detail_404_unknown_slug(self):
        response = self.client.get(reverse('product_detail', args=['no-such-product']))
        self.assertEqual(response.status_code, 404)

    def test_add_to_cart_returns_to_pdp_when_next_set(self):
        url = reverse('product_detail', args=[self.product.slug])
        response = self.client.post(
            reverse('add_to_cart', args=[self.product.id]),
            data={'size': '38', 'quantity': 1, 'next': url},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, url)


class FitRecommendationApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Dresses', description='')
        cls.product = Product.objects.create(
            name='Fit Test Dress',
            description='A test dress for AI fit recommendations.',
            price_usd=Decimal('110.00'),
            price_ugx=Decimal('0'),
            category=cls.category,
            stock_quantity=7,
            sizes='36,38,40,42',
        )
        Product.objects.create(
            name='Matching Wrap Top',
            description='Bundle candidate.',
            price_usd=Decimal('35.00'),
            price_ugx=Decimal('0'),
            category=cls.category,
            stock_quantity=4,
            sizes='38,40',
        )

    def test_fit_recommend_returns_risk_and_size(self):
        response = self.client.post(
            reverse('api_fit_recommend'),
            data=json.dumps({
                'product_id': self.product.id,
                'bust': 90,
                'waist': 72,
                'hips': 98,
                'usual_size': '38',
                'fit_preference': 'regular',
                'occasion': 'office',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['product_id'], self.product.id)
        self.assertIn(payload['return_risk'], ('low', 'medium', 'high'))
        self.assertTrue(payload['recommended_size'])
        self.assertIn('why', payload)
        self.assertGreaterEqual(len(payload['bundle_suggestions']), 1)

    def test_fit_recommend_requires_context(self):
        response = self.client.post(
            reverse('api_fit_recommend'),
            data=json.dumps({'product_id': self.product.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())


class StaffDashboardPermissionTests(TestCase):
    """Staff dashboard uses ``access_staff_dashboard`` — not Django ``is_staff`` (admin login)."""

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.perm = Permission.objects.get(
            content_type__app_label='core',
            codename='access_staff_dashboard',
        )
        cls.shop_staff = user_model.objects.create_user('portal_staff', password=_PW_PORTAL_STAFF)
        cls.shop_staff.user_permissions.add(cls.perm)
        cls.superuser = user_model.objects.create_superuser(
            'portal_super',
            'portal_super@test.example',
            _PW_PORTAL_SUPER,
        )
        cls.regular = user_model.objects.create_user('portal_buyer', password=_PW_BUYER)

    def test_staff_dashboard_redirects_when_anonymous(self):
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_staff_dashboard_forbidden_without_permission(self):
        self.client.force_login(self.regular)
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_staff_dashboard_ok_with_permission_not_admin_staff_flag(self):
        self.assertFalse(self.shop_staff.is_staff)
        self.client.force_login(self.shop_staff)
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_staff_dashboard_ok_for_superuser(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_staff_login_redirects_portal_user_to_dashboard(self):
        response = self.client.post(
            reverse('staff_login'),
            {'username': 'portal_staff', 'password': _PW_PORTAL_STAFF},
        )
        self.assertRedirects(response, reverse('staff_dashboard'), fetch_redirect_response=False)
        self.assertIsNotNone(self.client.session.get('_auth_user_id'))

    def test_staff_login_rejects_shopper_without_logging_in(self):
        response = self.client.post(
            reverse('staff_login'),
            {'username': 'portal_buyer', 'password': _PW_BUYER},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.session.get('_auth_user_id'))

    def test_staff_login_skipped_when_already_portal_user(self):
        self.client.force_login(self.shop_staff)
        response = self.client.get(reverse('staff_login'))
        self.assertRedirects(response, reverse('staff_dashboard'), fetch_redirect_response=False)


class AdminSuperuserOnlyMiddlewareTests(TestCase):
    """Non-superusers must not use ``/admin/`` even if ``is_staff`` or portal permission."""

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.regular = user_model.objects.create_user('adm_gate_buyer', password=_PW_GATE_BUYER)
        perm = Permission.objects.get(
            content_type__app_label='core',
            codename='access_staff_dashboard',
        )
        cls.portal_only = user_model.objects.create_user('adm_gate_portal', password=_PW_GATE_PORTAL)
        cls.portal_only.user_permissions.add(perm)
        cls.django_staff = user_model.objects.create_user(
            'adm_gate_django_staff',
            password=_PW_GATE_STAFF,
            is_staff=True,
        )
        cls.superuser = user_model.objects.create_superuser(
            'adm_gate_super',
            'adm_gate_super@test.example',
            _PW_GATE_SUPER,
        )

    def test_anonymous_admin_request_not_blocked_by_middleware(self):
        response = self.client.get('/admin/')
        self.assertIn(response.status_code, (301, 302))

    def test_portal_staff_get_admin_forbidden(self):
        self.client.force_login(self.portal_only)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 403)

    def test_is_staff_user_get_admin_forbidden(self):
        self.client.force_login(self.django_staff)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 403)

    def test_superuser_admin_allowed(self):
        self.client.force_login(self.superuser)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)


class AiUtilsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Tops', description='')

    def test_parse_measurements_from_text_uses_llm(self):
        from unittest.mock import patch
        from core.ai_utils import parse_measurements_from_text

        with patch('core.ai_utils.chat_complete', return_value='{"bust": 88, "waist": 68, "hips": 96}'):
            with self.settings(OPENAI_API_KEY='test-key'):
                parsed = parse_measurements_from_text('I am roughly 88 around chest, 68 waist, 96 hips')
        self.assertEqual(parsed['bust'], 88.0)
        self.assertEqual(parsed['waist'], 68.0)
        self.assertEqual(parsed['hips'], 96.0)

    def test_classify_inquiry_keyword_fallback(self):
        from core.ai_utils import classify_inquiry

        with self.settings(OPENAI_API_KEY='', GEMINI_API_KEY=''):
            tag = classify_inquiry('Bulk wedding order', 'We need 40 dresses')
        self.assertEqual(tag, 'bulk_order')

    def test_recommend_size_enhances_note_when_ai_configured(self):
        from unittest.mock import patch
        from core.ai_utils import recommend_size

        with patch('core.ai_utils.enhance_size_recommendation', return_value='EU 38 fits you well — try 40 if you prefer room.'):
            with self.settings(OPENAI_API_KEY='test-key'):
                result = recommend_size(90, 70, 98)
        self.assertEqual(result['size'], '38')
        self.assertIn('EU 38', result['note'])

    def test_recommend_size_eu_mapping_regression_grid(self):
        from core.ai_utils import recommend_size

        # Lock core baseline behavior so table edits don't silently drift sizes.
        cases = [
            ((90, 70, 98), '38'),
            ((88, 70, 96), '38'),
            ((92, 74, 100), '40'),
            ((84, 66, 92), '36'),
        ]

        for (bust, waist, hips), expected in cases:
            rec = recommend_size(bust, waist, hips, use_ai_note=False)
            self.assertEqual(rec['size'], expected)


class ChatApiTests(TestCase):
    def test_chat_prefers_llm_when_configured(self):
        from unittest.mock import patch

        with patch('core.ai_utils.chat_complete', return_value='Hello from Kistie AI!'):
            with self.settings(OPENAI_API_KEY='test-key'):
                response = self.client.post(
                    reverse('api_chat'),
                    data=json.dumps({'message': 'hello there'}),
                    content_type='application/json',
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reply'], 'Hello from Kistie AI!')

    def test_chat_measurement_parsing_via_llm(self):
        from unittest.mock import patch

        with patch('core.ai_utils.parse_measurements_from_text', return_value={'bust': 90.0, 'waist': 70.0, 'hips': 98.0}):
            with patch('core.ai_utils.enhance_size_recommendation', return_value='EU 38 is your best match.'):
                with self.settings(OPENAI_API_KEY='test-key'):
                    response = self.client.post(
                        reverse('api_chat'),
                        data=json.dumps({'message': 'what size am I? chest ninety waist seventy hips ninety eight'}),
                        content_type='application/json',
                    )
        self.assertEqual(response.status_code, 200)
        self.assertIn('EU 38', response.json()['reply'])


class SizeRecommendApiTests(TestCase):
    def test_size_recommend_returns_enhanced_note(self):
        from unittest.mock import patch

        with patch('core.ai_utils.enhance_size_recommendation', return_value='Try EU 38 for a classic fit.'):
            with self.settings(OPENAI_API_KEY='test-key'):
                response = self.client.post(
                    reverse('api_size_recommend'),
                    data=json.dumps({'bust': 90, 'waist': 70, 'hips': 98}),
                    content_type='application/json',
                )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['size'], '38')
        self.assertEqual(payload['note'], 'Try EU 38 for a classic fit.')
