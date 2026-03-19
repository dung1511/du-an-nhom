from django.db import models
from django.contrib.auth.models import User
from rooms.models import Room

class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # Optional for non-authenticated users
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True, null=True)  # For non-authenticated users
    email = models.EmailField(blank=True, null=True)  # For non-authenticated users
    country = models.CharField(max_length=100, blank=True, null=True)
    rating = models.PositiveIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"{self.user.username}'s Feedback for {self.room.name}"
        else:
            return f"Anonymous Feedback for {self.room.name}"