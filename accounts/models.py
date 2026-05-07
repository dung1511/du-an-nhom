from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import os
import uuid


def avatar_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"uploads/avatars/{uuid.uuid4().hex}{ext}"

class Profile(models.Model):
    ROLE_CUSTOMER = 'customer'
    ROLE_RECEPTIONIST = 'receptionist'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_CUSTOMER, 'Khách hàng'),
        (ROLE_RECEPTIONIST, 'Lễ tân'),
        (ROLE_ADMIN, 'Quản trị viên'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    phone_number = models.CharField(max_length=10, blank=True, null=True)
    profile_picture = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.role == self.ROLE_ADMIN:
            self.user.is_staff = True
            self.user.is_superuser = True
        elif self.role == self.ROLE_RECEPTIONIST:
            self.user.is_staff = True
            self.user.is_superuser = False
        else:
            self.user.is_staff = False
            self.user.is_superuser = False

        self.user.save(update_fields=['is_staff', 'is_superuser'])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username}'s profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance, defaults={'role': Profile.ROLE_CUSTOMER})