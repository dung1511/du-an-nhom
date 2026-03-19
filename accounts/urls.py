from django.urls import path
from . import views

app_name = 'accounts'  # Namespace for URL names

urlpatterns = [
    path('signup/', views.sign_up, name='sign_up'),
    path('login/', views.login_page, name='login_page'),
    path('logout/', views.logout_user, name='logout_user'),
    path('profile/', views.profile, name='profile'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
]   