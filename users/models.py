from django.db import models
from django.contrib.auth.models import User

class Password_Reset_Links(models.Model):
	user_id = models.OneToOneField(User, db_column='user_id', on_delete=models.PROTECT)
	username = models.CharField(max_length=250)
	reset_token = models.CharField(max_length=250)
	date_updated = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "user_credentials_reset_links"

class Treatments(models.Model):
	treatment = models.IntegerField(null=False, primary_key=True)
	reward_link = models.IntegerField(default=0)
	reward_monthly = models.IntegerField(default=0)
	
	class Meta:
		db_table = "treatments"

class User_Treatments(models.Model):
	user_id = models.OneToOneField(User, primary_key=True, db_column='user_id', on_delete=models.PROTECT)
	treatment = models.ForeignKey(Treatments, db_column='treatment', on_delete=models.PROTECT)
	
	class Meta:
		db_table = "user_treatments"