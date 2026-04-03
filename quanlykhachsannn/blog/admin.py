from django.contrib import admin
from .models import Blog, BlogCategory, Comment

admin.site.register(Blog)
admin.site.register(BlogCategory)
admin.site.register(Comment)