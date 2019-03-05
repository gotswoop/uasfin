from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

from users.models import Password_Reset_Links

class Command(BaseCommand):
    help = 'Set or update user\'s password reset token'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, help='The user_id for which you want to reset the password reset token')

    def handle(self, *args, **kwargs):
        user_id = kwargs['user_id']
        self.stdout.write("User_id: %s" % user_id)
        user = User.objects.get(id = user_id)
        self.stdout.write("Email: %s" % user.email)
        url = 'http://127.0.0.1:8000/password-reset-confirm/'
        token = url + urlsafe_base64_encode(force_bytes(user.pk)).decode() + '/' + default_token_generator.make_token(user) + '/'
        updated_item, new_item = Password_Reset_Links.objects.update_or_create(
            user_id = user, username = user.username, defaults={"reset_token": token}
        )
        self.stdout.write("Email: %s" % token)


'''
print(usr.email)
print(usr.username)
print(usr.pk)

from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
tk=default_token_generator
token = tk.make_token(usr)
print(token)
print(urlsafe_base64_encode(force_bytes(usr.pk)).decode(), token)

http://127.0.0.1:8000/password-reset-confirm/Nw/547-d1562c6b9000128a9bb0/

http://127.0.0.1:8000/password-reset-confirm/OAo/547-1736711240dd16d0d599/

https://uasfin.usc.edu/password-reset-confirm/MTE/548-4d297cdbae87b273181a/

https://cryptii.com/pipes/text-to-base64
'''