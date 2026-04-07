from django.db import models
from django.contrib.auth.models import User
import os
import uuid


def avatar_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"uploads/avatars/{uuid.uuid4().hex}{ext}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=10, blank=True, null=True)
    profile_picture = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"