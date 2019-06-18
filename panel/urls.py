from django.urls import path
from django.conf import settings
from . import views

urlpatterns = [
    path('', views.panel_home, name='panel_home'),
    path('admin/', views.panel_admin, name='panel_admin'),
    path('download/', views.panel_download, name='panel_download'),
]
