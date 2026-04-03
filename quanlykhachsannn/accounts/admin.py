from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile

# Inline Profile editing in User admin
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False

# Customize User admin
class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]

# Unregister and re-register User with custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register Profile model separately (optional)
admin.site.register(Profile)