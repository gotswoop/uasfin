from django.db import models
from django.contrib.auth.models import User

class Password_Reset_Links(models.Model):
	user_id = models.OneToOneField(User, db_column='user_id', on_delete=models.PROTECT)
	username = models.CharField(max_length=250)
	reset_token = models.CharField(max_length=250)
	date_updated = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "user_credentials_reset_links"