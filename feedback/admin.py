from django.contrib import admin
from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'room', 'booking_code', 'rating', 'country', 'created_at')
    search_fields = ('name', 'email', 'room__name', 'reservation__id')
    list_filter = ('rating', 'created_at', 'room')
    readonly_fields = ('created_at', 'booking_code')
    ordering = ('-created_at',)
    
    def booking_code(self, obj):
        if obj.reservation:
            return obj.reservation.booking_code
        return '-'
    booking_code.short_description = 'Booking Code'
