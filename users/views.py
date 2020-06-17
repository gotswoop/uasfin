from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings

from django.shortcuts import redirect
from fin.models import Fin_Items
from django.http import HttpResponse

from users.forms import UserRegisterForm
from fin.functions import fetch_treatment, error_handler

def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, format('Your account has been created! You are now able to log in'))
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def profile(request):
    
	internal_staff = False
	if request.user.groups.filter(name__in=['cesr_team','cfsi_team']).exists():
		internal_staff = True

	try:
		user_institutions = Fin_Items.objects.filter(user_id = request.user).order_by('p_item_name')
	except Fin_Items.DoesNotExist:
		user_institutions = None

	treatment = fetch_treatment(request.user.id)
	if not treatment:
		return HttpResponse(status=500)

	context = {
		'title': "Profile",
		'internal_staff': internal_staff,
		'treatment': treatment,
		'accounts': user_institutions,
		'plaid_env': settings.PLAID_ENV,
	}
    
	return render(request, 'users/profile.html', context)

def passwordReset(request):
    if request.user.is_authenticated:
        return redirect('home')

    return render(request, 'users/passwd_reset.html')

def ping(request):
	ip = get_client_ip(request)
	return HttpResponse('<html>OK<br/>' + ip + '</html>')

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
