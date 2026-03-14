from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Profile
from .forms import ProfileForm  

# Signup view 
def sign_up(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, 'Passwords do not match', extra_tags='danger')
            return redirect('accounts:sign_up')

        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists', extra_tags='danger')
            return redirect('accounts:sign_up')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already in use', extra_tags='danger')
            return redirect('accounts:sign_up')

        # Create the user
        user = User.objects.create_user(first_name=first_name, username=username, email=email, password=password)
        user.save()

        messages.success(request, 'Account created successfully', extra_tags='success')
        return redirect('accounts:sign_up')  # Redirect to login after signup

    return render(request, 'accounts_templates/signup.html')

# Login view 
def login_page(request):
    if request.method == 'POST':
        username = request.POST.get('username') 
        password = request.POST.get('password')

        existing_user = authenticate(username=username, password=password)
        if existing_user is not None:
            login(request, existing_user)
            return redirect('home')  # Redirect to phomw page
        else:
            messages.error(request, 'Invalid Username or Password', extra_tags='danger')
            return redirect('accounts:login_page')
    
    return render(request, 'accounts_templates/login.html')

# Logout view
@login_required(login_url='accounts:login_page')
def logout_user(request):
    logout(request)
    return redirect('accounts:login_page')

# Profile view
@login_required(login_url='accounts:login_page')
def profile(request):
    # Get or create the user's profile
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    
    context = {
        'user': request.user,
        'profile': profile,
    }
    return render(request, 'accounts_templates/profile.html', context)

# Edit profile view
@login_required(login_url='accounts:login_page')
def edit_profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully', extra_tags='success')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=profile)

    context = {
        'form': form,
    }
    return render(request, 'accounts_templates/edit_profile.html', context)