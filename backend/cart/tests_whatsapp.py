from django.test import SimpleTestCase, override_settings

from cart.whatsapp import format_store_phone_display, store_whatsapp_number, whatsapp_url


class WhatsAppUrlTests(SimpleTestCase):
    @override_settings(WHATSAPP_STORE_NUMBER='0704757198')
    def test_local_number_normalizes_to_256(self):
        digits = store_whatsapp_number()
        self.assertEqual(digits, '256704757198')
        self.assertEqual(format_store_phone_display(digits), '+256 704 757 198')

    def test_url_without_message_has_no_empty_text_param(self):
        url = whatsapp_url('256704757198', '')
        self.assertIn('api.whatsapp.com/send/', url)
        self.assertIn('phone=256704757198', url)
        self.assertNotIn('text=', url)

    def test_url_with_message(self):
        url = whatsapp_url('256704757198', 'Hello')
        self.assertIn('text=Hello', url.replace('+', ' '))
