from django.contrib import admin
from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'room', 'rating', 'country','created_at')
    search_fields = ('name', 'email', 'room__name')
    list_filter = ('rating', 'created_at')
    ordering = ('-created_at',)