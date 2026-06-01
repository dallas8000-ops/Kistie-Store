from django.conf import settings


def feature_flags(_request):
    return {
        'ENABLE_ADMIN': settings.ENABLE_ADMIN,
        'instagram_url': getattr(settings, 'INSTAGRAM_PROFILE_URL', ''),
    }
