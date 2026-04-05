from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Profile
from .forms import ProfileForm  
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from django.db.models import Count, Sum, Q
from .serializers import RegisterSerializer, ProfileSerializer, ChangePasswordSerializer, AdminUserSerializer

# views.py
def sign_up(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        username = request.POST.get('username').strip()
        email = request.POST.get('email').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Kiểm tra mật khẩu khớp
        if password != confirm_password:
            messages.error(request, 'Passwords do not match', extra_tags='danger')
            return redirect('accounts:sign_up')

        # Kiểm tra trùng Username (Để tránh lỗi IntegrityError bạn gặp lúc nãy)
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists', extra_tags='danger')
            return redirect('accounts:sign_up')

        # Tạo user
        user = User.objects.create_user(first_name=first_name, username=username, email=email, password=password)
        user.save()

        # Thông báo thành công
        messages.success(request, 'Account created successfully! Please login.', extra_tags='success')
        
        # ĐIỀU HƯỚNG SANG LOGIN
        return redirect('accounts:login_page')

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

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Đăng ký thành công!",
                "user": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_profile(self, user):
        profile, _ = Profile.objects.get_or_create(user=user)
        return profile

    def get(self, request):
        profile = self.get_profile(request.user)
        return Response(ProfileSerializer(profile).data)

    def put(self, request):
        return self._update(request)

    def patch(self, request):
        return self._update(request)

    def _update(self, request):
        profile = self.get_profile(request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Cập nhật hồ sơ thành công.',
            'profile': ProfileSerializer(profile).data,
        })


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'error': 'Mật khẩu hiện tại không đúng.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        update_session_auth_hash(request, user)
        return Response({'message': 'Đổi mật khẩu thành công.'}, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'message': 'Đăng xuất thành công.'}, status=status.HTTP_200_OK)


class AdminUserListAPIView(generics.ListAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return User.objects.select_related('profile').order_by('-date_joined')