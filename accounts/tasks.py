from celery import shared_task
from django.utils import timezone
from .models import VerificationCode

@shared_task
def delete_verification_code(code_id):
    try:
        verification_code = VerificationCode.objects.get(id=code_id)
        # Optionally check if it’s really expired before deleting:
        if verification_code.expires_at <= timezone.now():
            verification_code.delete()
    except VerificationCode.DoesNotExist:
        pass
