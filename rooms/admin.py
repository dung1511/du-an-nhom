# Import thư viện admin của Django để tùy chỉnh trang quản trị
from django.contrib import admin

# Import format_html để hiển thị HTML an toàn trong Django Admin
from django.utils.html import format_html

# Import timezone để lấy thời gian hiện tại theo múi giờ Django
from django.utils import timezone

# Import các model từ file models.py
from .models import Room, RoomCategory, RoomImage, Reservation, Coupon, Service


# Tạo class mixin để phân quyền cho staff và superuser
class ReadOnlyForStaffAdminMixin:

    # Cho phép xem dữ liệu nếu đã đăng nhập và là staff hoặc superuser
    def has_view_permission(self, request, obj=None):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_staff or request.user.is_superuser)
        )

    # Cho phép truy cập module admin nếu có quyền xem
    def has_module_permission(self, request):
        return self.has_view_permission(request)

    # Chỉ superuser mới được thêm dữ liệu
    def has_add_permission(self, request):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser
        )

    # Chỉ superuser mới được sửa dữ liệu
    def has_change_permission(self, request, obj=None):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser
        )

    # Chỉ superuser mới được xóa dữ liệu
    def has_delete_permission(self, request, obj=None):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser
        )


# Tạo inline để thêm nhiều ảnh phòng ngay trong Room Admin
class RoomImageInline(admin.TabularInline):

    # Model liên kết
    model = RoomImage

    # Hiển thị thêm 1 dòng trống để nhập ảnh mới
    extra = 1

    # Chỉ hiển thị field image
    fields = ('image',)


# Đăng ký model Room vào Django Admin
@admin.register(Room)

# Tạo class quản lý Room
class RoomAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):

    # Các cột hiển thị trong danh sách phòng
    list_display = ('name', 'category', 'capacity', 'size', 'price')

    # Bộ lọc bên phải admin
    list_filter = ('category', 'name')


# Đăng ký model RoomCategory
@admin.register(Room)

# Tạo class quản lý Room
class RoomAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):

    # Các cột hiển thị trong danh sách phòng
    list_display = ('name', 'category', 'capacity', 'size', 'price')

    # Bộ lọc bên phải admin
    list_filter = ('category', 'name')


# Đăng ký model RoomCategory
@admin.register(RoomCategory)

# Class quản lý danh mục phòng
class RoomCategoryAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):

    # Hiển thị tên danh mục
    list_display = ('name',)


# Đăng ký model RoomImage
@admin.register(RoomImage)

# Class quản lý ảnh phòng
class RoomImageAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):

    # Hiển thị phòng và ảnh
    list_display = ('room', 'image')

    # Bộ lọc theo phòng
    list_filter = ('room',)


# Đăng ký model Reservation
@admin.register(Reservation)

# Class quản lý đặt phòng
class ReservationAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):

    # Các cột hiển thị trong danh sách booking
    list_display = (
        'user',
        'room',
        'check_in_date',
        'check_out_date',
        'is_checked_out',
        'total',
        'deposit_status_label',
        'created_at',
        'checkout_at'
    )

    # Bộ lọc bên phải admin
    list_filter = (
        'is_checked_out',
        'room',
        'check_in_date',
        'payment_method',
        'checkout_at'
    )

    # Cho phép tìm kiếm
    search_fields = (
        'first_name',
        'last_name',
        'email',
        'room__name'
    )

    # Hiển thị theo ngày tạo
    date_hierarchy = 'created_at'

    # Action tùy chỉnh
    actions = ['confirm_deposit_action']

    # Các field chỉ đọc
    readonly_fields = (
        'deposit_receipt_preview',
        'deposit_status_label',
        'deposit_receipt_uploaded_at',
        'deposit_confirmed',
        'deposit_confirmed_at',
        'deposit_confirmed_by',
        'created_at',
        'checkout_at'
    )

    # Sắp xếp các field trong form admin
    fields = (
        'user',
        'room',
        'check_in_date',
        'check_out_date',
        'first_name',
        'last_name',
        'email',
        'phone',
        'total',
        'deposit_amount',
        'deposit_paid_via_qr',
        'deposit_status_label',
        'deposit_receipt_preview',
        'deposit_receipt',
        'deposit_receipt_uploaded_at',
        'deposit_confirmed',
        'deposit_confirmed_at',
        'deposit_confirmed_by',
        'is_checked_in',
        'is_checked_out',
        'created_at',
        'checkout_at'
    )

    # Hàm hiển thị trạng thái cọc
    def deposit_status_label(self, obj):

        # Nếu đã xác nhận cọc
        if obj and obj.deposit_confirmed:
            return 'Đã chuyển cọc'

        # Nếu có upload biên lai nhưng chưa duyệt
        if obj and obj.deposit_receipt:
            return 'Đang chờ duyệt'

        # Nếu chưa upload biên lai
        return 'Chưa chuyển cọc'

    # Đổi tên cột hiển thị
    deposit_status_label.short_description = 'Trạng thái cọc'

    # Hàm hiển thị ảnh biên lai
    def deposit_receipt_preview(self, obj):

        # Nếu có biên lai
        if obj and obj.deposit_receipt:

            # Hiển thị ảnh dạng HTML
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" '
                'style="max-width:120px;max-height:120px;object-fit:cover;"/>'
                '</a>',
                obj.deposit_receipt.url,
                obj.deposit_receipt.url
            )

        # Nếu không có biên lai
        return 'No receipt'

    # Đổi tên cột
    deposit_receipt_preview.short_description = 'Deposit receipt'

    # Action xác nhận chuyển khoản cọc
    def confirm_deposit_action(self, request, queryset):

        # Biến đếm số booking được cập nhật
        updated = 0

        # Duyệt từng booking được chọn
        for reservation in queryset:

            # Nếu đã xác nhận thì bỏ qua
            if reservation.deposit_confirmed:
                continue

            # Đánh dấu đã xác nhận cọc
            reservation.deposit_confirmed = True

            # Lưu thời gian xác nhận
            reservation.deposit_confirmed_at = timezone.now()

            # Lưu admin xác nhận
            reservation.deposit_confirmed_by = request.user

            # Cập nhật số tiền đã cọc
            reservation.deposit_paid_via_qr = (
                reservation.deposit_amount or
                reservation.deposit_paid_via_qr
            )

            # Đổi trạng thái thanh toán thành paid
            reservation.payment_status = 'paid'

            # Lưu dữ liệu
            reservation.save(
                update_fields=[
                    'deposit_confirmed',
                    'deposit_confirmed_at',
                    'deposit_confirmed_by',
                    'deposit_paid_via_qr',
                    'payment_status'
                ]
            )

            # Tăng biến đếm
            updated += 1

        # Hiển thị thông báo
        self.message_user(
            request,
            f"Đã xác nhận biên lai cho {updated} booking(s)."
        )

    # Tên action hiển thị trong admin
    confirm_deposit_action.short_description = (
        'Confirm selected deposit receipts'
    )


# Đăng ký model Coupon
@admin.register(Coupon)

# Class quản lý mã giảm giá
class CouponAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):

    # Các cột hiển thị
    list_display = (
        'code',
        'discount_percentage',
        'active',
        'valid_from',
        'valid_to'
    )

    # Bộ lọc
    list_filter = (
        'active',
        'valid_from',
        'valid_to'
    )

    # Tìm kiếm theo code
    search_fields = ('code',)


# Đăng ký model Service
@admin.register(Service)

# Class quản lý dịch vụ
class ServiceAdmin(ReadOnlyForStaffAdminMixin, admin.ModelAdmin):

    # Các cột hiển thị
    list_display = (
        'image_preview',
        'name',
        'price',
        'active',
        'order'
    )

    # Bộ lọc
    list_filter = ('active',)

    # Tìm kiếm
    search_fields = ('name', 'description')

    # Tự tạo slug từ name
    prepopulated_fields = {'slug': ('name',)}

    # Field chỉ đọc
    readonly_fields = ('image_preview',)

    # Sắp xếp field trong form
    fields = (
        'image_preview',
        'image',
        'image_url',
        'name',
        'slug',
        'description',
        'price',
        'active',
        'order'
    )

    # Hàm hiển thị preview ảnh
    def image_preview(self, obj):

        # Biến lưu url ảnh
        image_url = None

        # Nếu có upload ảnh
        if obj and obj.image:
            image_url = obj.image.url

        # Nếu không có upload nhưng có link ảnh
        elif obj and obj.image_url:
            image_url = obj.image_url

        # Nếu tồn tại ảnh
        if image_url:

            # Hiển thị HTML ảnh
            return format_html(
                '<img src="{}" '
                'style="width:56px;height:56px;'
                'object-fit:cover;'
                'border-radius:14px;'
                'border:1px solid #dbe4ef;'
                'box-shadow:0 8px 18px rgba(19,32,51,.08);" />',
                image_url,
            )

        # Nếu không có ảnh
        return 'No image'

    # Đổi tên cột preview
    image_preview.short_description = 'Preview'