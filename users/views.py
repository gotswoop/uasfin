from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm
from django.shortcuts import redirect
from fin.models import Items, Item_accounts, Item_account_transactions

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
    try:
        user_institutions = Items.objects.filter(user_id = request.user).order_by('p_item_name')
    except Items.DoesNotExist:
        user_institutions = None
        
    context = {
	    'title': "Profile",
        'accounts': user_institutions,
    }
    
    return render(request, 'users/profile.html', context)

def passwordReset(request):
    return render(request, 'users/passwd_reset.html')