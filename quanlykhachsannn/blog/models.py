from django.db import models
from django.contrib.auth.models import User

class BlogCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Blog(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    country = models.CharField(max_length=100)
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True)
    image1 = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    image2 = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Comment(models.Model):
    blog = models.ForeignKey(Blog, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100, blank=True)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.user:
            return f"Comment by {self.user.username}"
        else:
            return f"Comment by {self.name}"