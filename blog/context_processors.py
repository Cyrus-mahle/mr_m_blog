from django.conf import settings


def site_info(request):
    return {
        "site": {
            "name": settings.SITE_NAME,
            "tagline": settings.SITE_TAGLINE,
            "founder": settings.FOUNDER_NAME,
            "author": settings.AUTHOR_NAME,
            "developer": settings.DEVELOPER_NAME,
            "developer_title": settings.DEVELOPER_TITLE,
        }
    }