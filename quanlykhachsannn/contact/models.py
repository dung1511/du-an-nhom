from django.db import models
from django.contrib.auth.models import User

class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # Optional for authenticated users
    name = models.CharField(max_length=100, blank=True, null=True)  # For anonymous users
    email = models.EmailField(blank=True, null=True)  # For anonymous users
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"Contact from {self.user.username}"
        return f"Contact from {self.name or 'Anonymous'}"