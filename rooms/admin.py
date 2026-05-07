from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Room, RoomCategory, RoomImage, Reservation, Coupon, Service


class ReadOnlyForStaffAdminMixin:
    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def has_add_permission(self, request):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)

class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1
    fields = ('image',)

@admin.register(Room)
class RoomAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'category', 'capacity', 'size', 'price')
    list_filter = ('category', 'name')

@admin.register(RoomCategory)
class RoomCategoryAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):
    list_display = ('name',)

@admin.register(RoomImage)
class RoomImageAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):
    list_display = ('room', 'image')
    list_filter = ('room',)

# admin.py
@admin.register(Reservation)
class ReservationAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):
    # Thêm 'is_checked_out' vào list_display để Admin thấy ngay trạng thái
    list_display = ('user', 'room', 'check_in_date', 'check_out_date', 'is_checked_out', 'total', 'deposit_status_label', 'created_at', 'checkout_at')
    
    # Thêm bộ lọc bên phải để Admin lọc nhanh những ai đã trả phòng hoặc chưa
    list_filter = ('is_checked_out', 'room', 'check_in_date', 'payment_method', 'checkout_at')
    
    search_fields = ('first_name', 'last_name', 'email', 'room__name')
    date_hierarchy = 'created_at'
<<<<<<< HEAD
    actions = ['confirm_deposit_action']
=======
    # Add action to confirm uploaded deposit receipts and to mark QR-paid deposits
    actions = ['confirm_deposit_action', 'mark_qr_deposits_action']
>>>>>>> b311d48 (update feature admin room)
    readonly_fields = ('deposit_receipt_preview', 'deposit_status_label', 'deposit_receipt_uploaded_at', 'deposit_confirmed', 'deposit_confirmed_at', 'deposit_confirmed_by', 'created_at', 'checkout_at')
    fields = (
        'user', 'room', 'check_in_date', 'check_out_date', 'first_name', 'last_name', 'email', 'phone',
        'total', 'deposit_amount', 'deposit_paid_via_qr', 'deposit_status_label', 'deposit_receipt_preview', 'deposit_receipt', 'deposit_receipt_uploaded_at',
        'deposit_confirmed', 'deposit_confirmed_at', 'deposit_confirmed_by', 'is_checked_in', 'is_checked_out', 'created_at', 'checkout_at'
    )

    def deposit_status_label(self, obj):
<<<<<<< HEAD
        if obj and obj.deposit_confirmed:
=======
        # Consider deposit confirmed if admin explicitly confirmed it or a QR payment amount was recorded
        if obj and (getattr(obj, 'deposit_confirmed', False) or getattr(obj, 'deposit_paid_via_qr', 0)):
>>>>>>> b311d48 (update feature admin room)
            return 'Đã chuyển cọc'
        if obj and obj.deposit_receipt:
            return 'Đang chờ duyệt'
        return 'Chưa chuyển cọc'

    deposit_status_label.short_description = 'Trạng thái cọc'

    def deposit_receipt_preview(self, obj):
        if obj and obj.deposit_receipt:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-width:120px;max-height:120px;object-fit:cover;"/></a>', obj.deposit_receipt.url, obj.deposit_receipt.url)
        return 'No receipt'

    deposit_receipt_preview.short_description = 'Deposit receipt'

    def confirm_deposit_action(self, request, queryset):
        updated = 0
        for reservation in queryset:
            if reservation.deposit_receipt and not reservation.deposit_confirmed:
                reservation.deposit_confirmed = True
                reservation.deposit_confirmed_at = timezone.now()
                reservation.deposit_confirmed_by = request.user
                reservation.deposit_paid_via_qr = reservation.deposit_amount or reservation.deposit_paid_via_qr
                reservation.payment_status = 'paid'
                reservation.save(update_fields=['deposit_confirmed', 'deposit_confirmed_at', 'deposit_confirmed_by', 'deposit_paid_via_qr', 'payment_status'])
                updated += 1
        self.message_user(request, f"Đã xác nhận biên lai cho {updated} booking(s).")

    confirm_deposit_action.short_description = 'Confirm selected deposit receipts'
<<<<<<< HEAD
=======

    def mark_qr_deposits_action(self, request, queryset):
        updated = 0
        for reservation in queryset:
            try:
                if (getattr(reservation, 'deposit_paid_via_qr', 0) and not reservation.deposit_confirmed) and reservation.deposit_paid_via_qr > 0:
                    reservation.deposit_confirmed = True
                    reservation.deposit_confirmed_at = timezone.now()
                    reservation.save(update_fields=['deposit_confirmed', 'deposit_confirmed_at'])
                    updated += 1
            except Exception:
                continue
        self.message_user(request, f"Đã đánh dấu {updated} booking(s) có QR payment là đã chuyển cọc.")

    mark_qr_deposits_action.short_description = 'Mark selected QR-paid reservations as deposit-confirmed'
>>>>>>> b311d48 (update feature admin room)

@admin.register(Coupon)
class CouponAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'active', 'valid_from', 'valid_to')
    list_filter = ('active', 'valid_from', 'valid_to')
    search_fields = ('code',)


@admin.register(Service)
class ServiceAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):
    list_display = ('image_preview', 'name', 'price', 'active', 'order')
    list_filter = ('active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('image_preview',)
    fields = ('image_preview', 'image', 'image_url', 'name', 'slug', 'description', 'price', 'active', 'order')

    def image_preview(self, obj):
        image_url = None
        if obj and obj.image:
            image_url = obj.image.url
        elif obj and obj.image_url:
            image_url = obj.image_url

        if image_url:
            return format_html(
                '<img src="{}" style="width:56px;height:56px;object-fit:cover;border-radius:14px;border:1px solid #dbe4ef;box-shadow:0 8px 18px rgba(19,32,51,.08);" />',
                image_url,
            )
        return 'No image'

    image_preview.short_description = 'Preview'