from django.contrib import admin
from django.utils.html import format_html
from .models import Room, RoomCategory, RoomImage, Reservation, Coupon, Service

class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1
    fields = ('image',)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'capacity', 'size', 'price')
    list_filter = ('category', 'name')

@admin.register(RoomCategory)
class RoomCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(RoomImage)
class RoomImageAdmin(admin.ModelAdmin):
    list_display = ('room', 'image')
    list_filter = ('room',)

# admin.py
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    # Thêm 'is_checked_out' vào list_display để Admin thấy ngay trạng thái
    list_display = ('user', 'room', 'check_in_date', 'check_out_date', 'is_checked_out', 'total', 'created_at')
    
    # Thêm bộ lọc bên phải để Admin lọc nhanh những ai đã trả phòng hoặc chưa
    list_filter = ('is_checked_out', 'room', 'check_in_date', 'payment_method')
    
    search_fields = ('first_name', 'last_name', 'email', 'room__name')
    date_hierarchy = 'created_at'

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'active', 'valid_from', 'valid_to')
    list_filter = ('active', 'valid_from', 'valid_to')
    search_fields = ('code',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
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