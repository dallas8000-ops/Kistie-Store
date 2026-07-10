from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from pages.models import ContactInquiry


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CONTACT_RECIPIENT_EMAIL='dallas8000@gmail.com',
    DEFAULT_FROM_EMAIL='noreply@kistie-store.test',
)
class ContactInquiryFlowTests(TestCase):
    """Contact form must persist inquiries and email the store inbox."""

    def test_contact_post_saves_inquiry_and_emails_recipient(self):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Test Shopper',
                'email': 'shopper@example.com',
                'subject': 'Sizing question',
                'message': 'Do you have this dress in size M?',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactInquiry.objects.count(), 1)
        inquiry = ContactInquiry.objects.get()
        self.assertEqual(inquiry.name, 'Test Shopper')
        self.assertEqual(inquiry.email, 'shopper@example.com')
        self.assertEqual(inquiry.subject, 'Sizing question')

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['dallas8000@gmail.com'])
        self.assertIn('Sizing question', sent.subject)
        self.assertIn('shopper@example.com', sent.body)
        self.assertIn('size M', sent.body)

    def test_contact_post_keeps_inquiry_when_email_fails(self):
        with patch('core.views.send_mail', side_effect=OSError('SMTP down')):
            response = self.client.post(
                reverse('contact'),
                {
                    'name': 'Retry Shopper',
                    'email': 'retry@example.com',
                    'subject': 'Still interested',
                    'message': 'Please call me back.',
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactInquiry.objects.count(), 1)
        self.assertEqual(ContactInquiry.objects.get().email, 'retry@example.com')
