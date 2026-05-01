from .models import Profile


def user_role(request):
    """Context processor để cung cấp thông tin role user cho templates"""
    user_role_type = None
    
    if request.user.is_authenticated:
        if request.user.is_superuser:
            user_role_type = 'admin'
        else:
            try:
                profile = request.user.profile
                if profile.role == Profile.ROLE_RECEPTIONIST:
                    user_role_type = 'receptionist'
                else:
                    user_role_type = 'customer'
            except Profile.DoesNotExist:
                user_role_type = 'customer'
    else:
        user_role_type = 'guest'
    
    return {
        'user_role_type': user_role_type,
    }
