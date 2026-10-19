import uuid
from django.conf import settings


def common(request):
    return {"operation_key": str(uuid.uuid4()), "demo_mode": settings.DEMO_MODE,
            "local_mail": settings.DEBUG and "filebased" in settings.EMAIL_BACKEND,
            "site_url": settings.SITE_URL}

