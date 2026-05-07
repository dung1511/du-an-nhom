#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quanlykhachsannn.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import Profile

# Check current user status
user = User.objects.filter(username='kieu').first()
if user:
    print(f"User 'kieu' found:")
    print(f"  is_staff: {user.is_staff}")
    print(f"  is_superuser: {user.is_superuser}")
    print(f"  is_active: {user.is_active}")
    
    profile = Profile.objects.filter(user=user).first()
    if profile:
        print(f"  Profile.role: {profile.role}")
    else:
        print(f"  Profile: NOT FOUND")
    
    # Update to admin
    print("\nUpdating user to admin...")
    user.is_staff = True
    user.is_superuser = True
    user.save()
    
    # Create/Update profile
    if not profile:
        Profile.objects.create(user=user, role='admin')
        print("  Created Profile with role='admin'")
    else:
        profile.role = 'admin'
        profile.save()
        print("  Updated Profile with role='admin'")
    
    print("\n✓ User 'kieu' is now admin!")
    print("You can now login to /admin/ with username: kieu")
else:
    print("User 'kieu' NOT FOUND")
