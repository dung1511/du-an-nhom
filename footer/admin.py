from django.contrib import admin
from .models import FooterText

@admin.register(FooterText)
class FooterTextAdmin(admin.ModelAdmin):
    list_display = ('text', 'is_editable')
    list_filter = ('is_editable',)
    search_fields = ('text',)

    def has_change_permission(self, request, obj=None):
        # Only superusers can edit
        if not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete
        if not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)