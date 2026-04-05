from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

app_name = 'accounts'  # Namespace for URL names

urlpatterns = [
    path('signup/', views.sign_up, name='sign_up'),
    path('login/', views.login_page, name='login_page'),
    path('logout/', views.logout_user, name='logout_user'),
    path('profile/', views.profile, name='profile'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),

    
   # Hệ thống API (JWT)
    path('api/register/', views.RegisterView.as_view(), name='auth_register'),
    path('api/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/profile/', views.ProfileAPIView.as_view(), name='api_profile'),
    path('api/change-password/', views.ChangePasswordAPIView.as_view(), name='api_change_password'),
    path('api/logout/', views.LogoutAPIView.as_view(), name='api_logout'),
    path('api/admin/users/', views.AdminUserListAPIView.as_view(), name='api_admin_users'),
]   