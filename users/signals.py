from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.conf import settings

from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

from users.models import Password_Reset_Links
from fin.models import User_Actions
from django.contrib.auth.models import User

@receiver(user_logged_in)
def sig_user_logged_in(sender, user, request, **kwargs):
	# Updating the user_password_reset_link table 
	# url = ('https://' if request.is_secure() else 'http://') + request.get_host() + '/password-reset-confirm/'
	url = '/password-reset-confirm/'
	token = url + urlsafe_base64_encode(force_bytes(user.pk)) + '/' + default_token_generator.make_token(user) + '/'
	updated_item, new_item = Password_Reset_Links.objects.update_or_create(
		user_id = user, username = user.username, defaults={"reset_token": token}
	)
	# TODO try this..
	new_item = User_Actions.objects.create(
		user_id = user, 
		user_ip = request.META['REMOTE_ADDR'],
		action = "login",
	)
    
@receiver(user_logged_out)
def sig_user_logged_out(sender, user, request, **kwargs):
	if not request.user.is_authenticated:
		return

	# TODO try this..
	new_item = User_Actions.objects.create(
		user_id = user, 
		user_ip = request.META['REMOTE_ADDR'],
		action = "logout",
	)

# Creating a new password reset link right after a password reset.
@receiver(post_save, sender=get_user_model())
def sig_user_password_reset(sender, **kwargs):
	user = kwargs.get('instance', None)
	if user:
		url = '/password-reset-confirm/'
		token = url + urlsafe_base64_encode(force_bytes(user.pk)) + '/' + default_token_generator.make_token(user) + '/'
		updated_item, new_item = Password_Reset_Links.objects.update_or_create(
			user_id = user, username = user.username, defaults={"reset_token": token}
		)
		# TODO: Move this to a decorator to get remote IP
		new_item = User_Actions.objects.create(
			user_id = user, 
			user_ip = '-',
			action = "password-change",
		)