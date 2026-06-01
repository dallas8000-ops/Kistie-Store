from django.conf import settings


def _instagram_handle(profile_url):
    url = (profile_url or '').rstrip('/')
    if 'instagram.com/' in url:
        return url.split('instagram.com/')[-1].split('?')[0] or 'Instagram'
    return 'Instagram'


def feature_flags(_request):
    profile_url = getattr(settings, 'INSTAGRAM_PROFILE_URL', '')
    return {
        'ENABLE_ADMIN': settings.ENABLE_ADMIN,
        'instagram_url': profile_url,
        'instagram_handle': _instagram_handle(profile_url),
    }
