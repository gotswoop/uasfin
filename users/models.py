from django.db import models
from django.contrib.auth.models import User

class Password_Reset_Links(models.Model):
	user_id = models.OneToOneField(User, db_column='user_id', on_delete=models.CASCADE)
	username = models.CharField(max_length=100)
	reset_token = models.CharField(max_length=200)
	date_updated = models.DateTimeField(null=True, auto_now=True)

	class Meta:
		db_table = "user_password_reset_links"

class Actions(models.Model):
	user_id = models.ForeignKey(User, db_column='user_id', on_delete=models.CASCADE)
	user_ip = models.CharField(max_length=15)
	username = models.CharField(max_length=100)
	action = models.CharField(max_length=20)
	action_details = models.CharField(max_length=200, null=True)
	date_created = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "user_actions"