from django.contrib import admin
from .models import Room, RoomCategory, RoomImage, Reservation, Coupon, Service

# Quản lý ảnh phòng dạng Inline (hiển thị ngay trong trang chỉnh sửa Room)
class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1
    fields = ('image',)

# 1. Quản lý Tiện ích (MỚI)
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)

# 2. Quản lý Phòng (Cập nhật filter và Inline)
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'capacity', 'size', 'price')
    list_filter = ('category', 'size', 'services') # Thêm lọc theo tiện ích
    search_fields = ('name', 'description')
    inlines = [RoomImageInline] # Giúp bạn thêm nhiều ảnh ngay tại trang sửa phòng
    # Hiển thị chọn Service dạng ngang cho dễ nhìn (tùy chọn)
    filter_horizontal = ('services',) 

@admin.register(RoomCategory)
class RoomCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(RoomImage)
class RoomImageAdmin(admin.ModelAdmin):
    list_display = ('room', 'image')
    list_filter = ('room',)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'check_in_date', 'check_out_date', 'adults', 'total', 'payment_method', 'created_at')
    list_filter = ('room', 'check_in_date', 'check_out_date', 'payment_method')
    search_fields = ('first_name', 'last_name', 'email', 'room__name')
    date_hierarchy = 'created_at'

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'active', 'valid_from', 'valid_to')
    list_filter = ('active', 'valid_from', 'valid_to')
    search_fields = ('code',)