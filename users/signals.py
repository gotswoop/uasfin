from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.conf import settings

from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

from .models import Password_Reset_Links, Actions

@receiver(user_logged_in)
def sig_user_logged_in(sender, user, request, **kwargs):
    # logger = logging.getLogger(__name__)
    # logger.info("user logged in: %s at %s" % (user, request.META['REMOTE_ADDR']))
    # Updating the user_password_reset_link table 
    url = 'https://' + request.get_host() + '/password-reset-confirm/'
    token = url + urlsafe_base64_encode(force_bytes(user.pk)).decode() + '/' + default_token_generator.make_token(user) + '/'
    updated_item, new_item = Password_Reset_Links.objects.update_or_create(
        user_id = user, username = user.username, defaults={"reset_token": token}
    )
    # TODO try this..
    new_item = Actions.objects.create(
        user_id = user, 
        user_ip = request.META['REMOTE_ADDR'],
        username = user.username,
        action = "login",
    )
    
@receiver(user_logged_out)
def sig_user_logged_out(sender, user, request, **kwargs):
    if not request.user.is_authenticated:
        return

    # TODO try this..
    new_item = Actions.objects.create(
        user_id = user, 
        user_ip = request.META['REMOTE_ADDR'],
        username = user.username,
        action = "logout",
    )