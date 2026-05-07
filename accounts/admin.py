from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile

# Inline Profile editing in User admin
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fields = ('role', 'phone_number', 'profile_picture')

# Customize User admin
class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ('username', 'email', 'get_role', 'is_staff', 'is_superuser', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__role')

    def get_role(self, obj):
        profile = getattr(obj, 'profile', None)
        if not profile:
            return 'customer'
        return profile.get_role_display()

    get_role.short_description = 'Vai trò'

# Unregister and re-register User with custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register Profile model separately (optional)
admin.site.register(Profile)