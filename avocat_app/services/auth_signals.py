# cabinet/services/auth_signals.py
from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from ..models import AuthToken

@receiver(user_logged_out)
def revoke_tokens_on_logout(sender, request, user, **kwargs):
    if user and user.is_authenticated:
        AuthToken.objects.filter(user=user, is_active=True).update(is_active=False)
