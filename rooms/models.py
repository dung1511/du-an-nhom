from django.db import models
from django.contrib.auth.models import User
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal
import os
import uuid
from itertools import combinations


# Hàm tạo đường dẫn upload ảnh bìa phòng
def room_cover_upload_path(instance, filename):

    # Lấy phần mở rộng của file
    # Ví dụ:
    # image.png -> .png
    ext = os.path.splitext(filename)[1].lower() or ".jpg"

    # Trả về đường dẫn lưu file
    # uuid.uuid4().hex giúp tạo tên file ngẫu nhiên tránh trùng
    return f"uploads/rooms/{uuid.uuid4().hex}{ext}"



# Hàm tạo đường dẫn upload ảnh gallery phòng
def room_gallery_upload_path(instance, filename):
    # Lấy đuôi file
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    # Trả về đường dẫn upload
    return f"uploads/room-gallery/{uuid.uuid4().hex}{ext}"
# Hàm tạo đường dẫn upload ảnh dịch vụ
def service_image_upload_path(instance, filename):
    # Lấy phần mở rộng file
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    # Trả về đường dẫn lưu ảnh dịch vụ
    return f"uploads/services/{uuid.uuid4().hex}{ext}"



# Tạo custom manager cho model Room
class RoomManager(models.Manager):
    # Hàm tìm phòng còn trống
    def available_rooms(self, check_in, check_out, adults):
        """
        Tìm phòng còn trống và đủ sức chứa
        """
        # Tìm các phòng đã được đặt
        reserved_rooms = Reservation.objects.filter(
            # Ngày check-in booking cũ nhỏ hơn ngày checkout mới
            check_in_date__lt=check_out,
            # Ngày checkout booking cũ lớn hơn ngày checkin mới
            check_out_date__gt=check_in,
            # Chưa checkout
            is_checked_out=False,
        ).values_list('room_id', flat=True)
        # Trả về các phòng:
        # - đủ sức chứa
        # - không nằm trong danh sách đã đặt
        return self.filter(
            capacity__gte=adults
        ).exclude(
            id__in=reserved_rooms
        )
    # Hàm tìm phòng phù hợp
    def search_suitable_rooms(
        self,
        check_in,
        check_out,
        adults,
        children=0,
        limit=None
    ):
        """
        Tìm phòng phù hợp cho nhóm khách
        adults + children
        """
        # Import F và Q để query nâng cao
        from django.db.models import F, Q
        # Tổng số khách
        total_guests = adults + children
        # ===== TÌM PHÒNG ĐÃ ĐƯỢC ĐẶT =====
        reserved_rooms = Reservation.objects.filter(
            # Điều kiện trùng ngày
            check_in_date__lt=check_out,
            check_out_date__gt=check_in,
            # Chưa checkout
            is_checked_out=False
        ).values_list('room_id', flat=True)
        # ===== TÌM PHÒNG PHÙ HỢP =====
        suitable_rooms = self.filter(
            # Tổng sức chứa >= tổng khách
            total_capacity__gte=total_guests,
            # Sức chứa người lớn đủ
            capacity_adults__gte=adults,
            # Sức chứa trẻ em đủ
            capacity_children__gte=children
        ).exclude(
            # Loại bỏ phòng đã được đặt
            id__in=reserved_rooms
        )
        # ===== SẮP XẾP =====
        # Ưu tiên:
        # 1. Phòng vừa đủ sức chứa
        # 2. Giá rẻ hơn
        suitable_rooms = suitable_rooms.order_by(
            'total_capacity',
            'price'
        )
        # Nếu có giới hạn số lượng phòng
        if limit:
            # Chỉ lấy số lượng cần thiết
            suitable_rooms = suitable_rooms[:limit]
        # Trả kết quả
        return suitable_rooms
    # Hàm đề xuất tổ hợp nhiều phòng
    def recommend_room_combinations(
        self,
        check_in,
        check_out,
        adults,
        children=0,
        max_rooms=2,
        limit=3
    ):
        """
        Đề xuất tổ hợp phòng cho nhóm khách đông
        """
        # Tổng khách
        total_guests = adults + children
        # ===== LẤY DANH SÁCH PHÒNG TRỐNG =====
        available_rooms = list(
            self.filter(
                total_capacity__gte=1,
            )
            .exclude(
                # Loại phòng đã đặt
                id__in=Reservation.objects.filter(
                    check_in_date__lt=check_out,
                    check_out_date__gt=check_in,
                    is_checked_out=False,
                ).values_list('room_id', flat=True)
            )
            # Sắp xếp theo sức chứa và giá
            .order_by(
                'total_capacity',
                'price'
            )
        )
        # Nếu ít hơn 2 phòng hoặc không có khách
        if len(available_rooms) < 2 or total_guests <= 0:

            # Trả về danh sách rỗng
            return []
        # Danh sách chứa kết quả tổ hợp
        scored_combinations = []
        # Số lượng phòng tối đa
        max_group_size = 2 if max_rooms is None else max(2, max_rooms)
        # ===== DUYỆT TỪNG TỔ HỢP =====
        for group_size in range(2, max_group_size + 1):
            # combinations tạo tổ hợp phòng
            for room_group in combinations(
                available_rooms,
                group_size
            ):
                # Tổng sức chứa
                total_capacity = sum(
                    room.total_capacity or room.capacity
                    for room in room_group
                )
                # Nếu không đủ chứa khách
                if total_capacity < total_guests:
                    continue
                # Tổng giá phòng
                total_price = sum(
                    room.price
                    for room in room_group
                )
                # Điểm đánh giá tổ hợp
                score = (

                    # Ít phòng hơn ưu tiên hơn
                    len(room_group),

                    # Phòng vừa đủ ưu tiên hơn
                    total_capacity - total_guests,

                    # Giá rẻ ưu tiên hơn
                    total_price,
                )
                # Thêm vào danh sách
                scored_combinations.append(
                    (
                        score,
                        room_group,
                        total_capacity,
                        total_price
                    )
                )
        # ===== SẮP XẾP TỔ HỢP =====
        scored_combinations.sort(
            key=lambda item: item[0]
        )
        # Danh sách kết quả cuối
        results = []
        # Tránh trùng tổ hợp
        seen_sets = set()
        # ===== LẤY KẾT QUẢ =====
        for _, room_group, total_capacity, total_price in scored_combinations:
            # Lấy ID các phòng
            room_ids = tuple(
                sorted(room.id for room in room_group)
            )
            # Nếu đã tồn tại thì bỏ qua
            if room_ids in seen_sets:
                continue
            # Đánh dấu đã dùng
            seen_sets.add(room_ids)
            # Thêm vào kết quả
            results.append(
                {

                    # Danh sách phòng
                    'rooms': room_group,

                    # Tổng sức chứa
                    'total_capacity': total_capacity,

                    # Tổng giá
                    'total_price': total_price,
                }
            )
            # Nếu đủ số lượng limit
            if len(results) >= limit:
                break
        # Trả về kết quả
        return results


# ===== MODEL DANH MỤC PHÒNG =====
class RoomCategory(models.Model):

    # Tạo field tên danh mục phòng
    # max_length=50 -> tối đa 50 ký tự
    # unique=True -> tên không được trùng
    name = models.CharField(
        max_length=50,
        unique=True
    )

    # Hàm hiển thị object dưới dạng chuỗi
    def __str__(self):

        # Trả về tên danh mục
        return self.name



# ===== MODEL PHÒNG =====
class Room(models.Model):

    # Các lựa chọn loại phòng
    SIZE_CHOICES = (

        # Phòng đơn
        ('S', 'Single Bedroom'),

        # Phòng đôi
        ('D', 'Double Bedroom'),

        # Phòng ba
        ('T', 'Triple Bedroom'),
    )


    # ===== THÔNG TIN PHÒNG =====

    # Tên phòng
    name = models.CharField(max_length=100)


    # Liên kết với bảng RoomCategory
    # on_delete=models.SET_NULL
    # -> nếu xóa category thì category = NULL
    category = models.ForeignKey(
        RoomCategory,
        on_delete=models.SET_NULL,
        null=True
    )


    # Sức chứa cơ bản
    capacity = models.PositiveIntegerField()


    # Kích thước phòng
    # choices=SIZE_CHOICES
    # -> chỉ cho phép chọn S, D, T
    size = models.CharField(
        max_length=1,
        choices=SIZE_CHOICES
    )


    # ===== SỨC CHỨA =====

    # Sức chứa người lớn
    capacity_adults = models.PositiveIntegerField(default=2)

    # Sức chứa trẻ em
    capacity_children = models.PositiveIntegerField(default=2)

    # Tổng sức chứa
    total_capacity = models.PositiveIntegerField(default=4)


    # ===== THÔNG TIN KHÁC =====

    # Mô tả phòng
    description = models.TextField()

    # Giá phòng
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Ảnh đại diện phòng
    image = models.ImageField(

        # Đường dẫn upload ảnh
        upload_to=room_cover_upload_path,

        # Không bắt buộc
        blank=True,

        # Cho phép null database
        null=True
    )


    # Gắn custom manager
    objects = RoomManager()



    # ===== HÀM KHỞI TẠO =====
    def __init__(self, *args, **kwargs):

        # Nếu truyền room_title nhưng không có name
        if 'room_title' in kwargs and 'name' not in kwargs:

            # Đổi room_title thành name
            kwargs['name'] = kwargs.pop('room_title')


        # Nếu truyền max_adult
        if 'max_adult' in kwargs and 'capacity_adults' not in kwargs:

            # Gán vào capacity_adults
            kwargs['capacity_adults'] = kwargs.pop('max_adult')


        # Nếu truyền max_children
        if 'max_children' in kwargs and 'capacity_children' not in kwargs:

            # Gán vào capacity_children
            kwargs['capacity_children'] = kwargs.pop('max_children')


        # Gọi constructor của class cha
        super().__init__(*args, **kwargs)



    # ===== HIỂN THỊ OBJECT =====
    def __str__(self):

        # Trả về tên phòng
        return self.name



    # ===== PROPERTY room_title =====
    @property
    def room_title(self):

        # Trả về name
        return self.name


    @room_title.setter
    def room_title(self, value):

        # Gán name
        self.name = value



    # ===== PROPERTY max_adult =====
    @property
    def max_adult(self):

        # Trả về capacity_adults
        return self.capacity_adults


    @max_adult.setter
    def max_adult(self, value):

        # Gán giá trị
        self.capacity_adults = value



    # ===== PROPERTY max_children =====
    @property
    def max_children(self):

        # Trả về sức chứa trẻ em
        return self.capacity_children


    @max_children.setter
    def max_children(self, value):

        # Gán giá trị
        self.capacity_children = value



    # ===== KIỂM TRA SỨC CHỨA =====
    def can_accommodate(self, adults, children=0):

        """
        Kiểm tra phòng có đủ sức chứa hay không
        """

        # Nếu adults None -> 0
        adults = adults or 0

        # Nếu children None -> 0
        children = children or 0


        # Tổng số khách
        total_guests = adults + children


        # ===== TÍNH TỔNG SỨC CHỨA =====
        total_capacity = (

            # Ưu tiên total_capacity
            self.total_capacity

            # Nếu không có -> capacity
            or self.capacity

            # Nếu không có nữa -> cộng adults + children
            or (
                self.capacity_adults +
                self.capacity_children
            )
        )


        # ===== SỨC CHỨA NGƯỜI LỚN =====
        adults_capacity = (

            self.capacity_adults
            or self.capacity
            or total_capacity
        )


        # ===== SỨC CHỨA TRẺ EM =====
        children_capacity = (

            self.capacity_children
            if self.capacity_children is not None
            else total_capacity
        )


        # ===== KIỂM TRA ĐIỀU KIỆN =====
        return (

            # Phải có ít nhất 1 người lớn
            adults >= 1

            # Trẻ em không âm
            and children >= 0

            # Tổng khách không vượt quá tổng sức chứa
            and total_guests <= total_capacity

            # Người lớn không vượt quá giới hạn
            and adults <= adults_capacity

            # Trẻ em không vượt quá giới hạn
            and children <= children_capacity
        )



    # ===== TRẠNG THÁI PHÒNG =====
    def availability_status(self):

        # Lấy ngày hiện tại
        today = date.today()

        # Ngày mai
        tomorrow = today + timedelta(days=1)


        # Nếu phòng trống
        if self.is_available(today, tomorrow):

            return 'Phòng trống'

        # Nếu đã đặt
        return 'Đã đặt'



    # ===== SAVE =====
    def save(self, *args, **kwargs):

        # Tự động tính tổng sức chứa
        self.total_capacity = (

            self.capacity_adults +
            self.capacity_children
        )

        # Lưu dữ liệu
        super().save(*args, **kwargs)



    # ===== KIỂM TRA PHÒNG TRỐNG =====
    def is_available(self, check_in=None, check_out=None):

        """
        Kiểm tra phòng có trống hay không
        """

        # Nếu không truyền check_in
        if check_in is None:

            # Dùng ngày hiện tại
            check_in = date.today()


        # Nếu không truyền check_out
        if check_out is None:

            # Mặc định ngày mai
            check_out = check_in + timedelta(days=1)


        # Import Reservation tránh lỗi vòng lặp
        from .models import Reservation


        # Tìm booking bị trùng lịch
        overlapping = Reservation.objects.filter(

            # Phòng hiện tại
            room=self,

            # Chưa checkout
            is_checked_out=False,

            # Điều kiện trùng ngày
            check_in_date__lt=check_out,
            check_out_date__gt=check_in
        )


        # Nếu không tồn tại booking
        # -> phòng trống
        return not overlapping.exists()



    # ===== PROPERTY TRẠNG THÁI =====
    @property
    def availability_status(self):

        try:

            # Nếu phòng trống
            if self.is_available():

                return "Phòng trống"

            # Nếu đã đặt
            return "Đã đặt"

        except Exception as e:

            # In lỗi
            print(f"Lỗi kiểm tra trạng thái: {e}")

            return "Đang kiểm tra"



# ===== MODEL ẢNH PHÒNG =====
class RoomImage(models.Model):

    # Liên kết với Room
    room = models.ForeignKey(

        Room,

        # room.images.all()
        related_name='images',

        # Xóa phòng -> xóa ảnh
        on_delete=models.CASCADE
    )

    # Ảnh phòng
    image = models.ImageField(
        upload_to=room_gallery_upload_path
    )


    # Hiển thị object
    def __str__(self):

        return f"Image for {self.room.name}"



# ===== MODEL MÃ GIẢM GIÁ =====
class Coupon(models.Model):

    # Mã giảm giá
    code = models.CharField(
        max_length=50,
        unique=True
    )

    # % giảm giá
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    # Trạng thái hoạt động
    active = models.BooleanField(default=True)

    # Ngày bắt đầu
    valid_from = models.DateField()

    # Ngày kết thúc
    valid_to = models.DateField()



    # ===== CONSTRUCTOR =====
    def __init__(self, *args, **kwargs):

        # Nếu có discount_price
        if 'discount_price' in kwargs and 'discount_percentage' not in kwargs:

            # Mapping sang discount_percentage
            kwargs['discount_percentage'] = kwargs.pop(
                'discount_price'
            )


        # Nếu có is_active
        if 'is_active' in kwargs and 'active' not in kwargs:

            # Mapping sang active
            kwargs['active'] = kwargs.pop(
                'is_active'
            )

        # Gọi constructor cha
        super().__init__(*args, **kwargs)



    # ===== HIỂN THỊ OBJECT =====
    def __str__(self):

        # Trả về mã coupon
        return self.code



    # ===== PROPERTY discount_price =====
    @property
    def discount_price(self):

        # Trả về discount_percentage
        return self.discount_percentage


    @discount_price.setter
    def discount_price(self, value):

        # Gán giá trị
        self.discount_percentage = value



    # ===== PROPERTY is_active =====
    @property
    def is_active(self):

        # Trả về active
        return self.active


    @is_active.setter
    def is_active(self, value):

        # Gán active
        self.active = value

# ===== MODEL DỊCH VỤ =====
class Service(models.Model):

    # Tên dịch vụ
    # unique=True -> tên không được trùng
    name = models.CharField(
        max_length=120,
        unique=True
    )

    # Slug dùng cho URL thân thiện
    # Ví dụ:
    # "Spa VIP" -> "spa-vip"
    slug = models.SlugField(
        max_length=140,
        unique=True
    )

    # Mô tả dịch vụ
    # blank=True -> cho phép để trống form
    description = models.TextField(blank=True)

    # Giá dịch vụ
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    # Ảnh dịch vụ upload từ máy
    image = models.ImageField(

        # Thư mục upload
        upload_to=service_image_upload_path,

        # Không bắt buộc
        blank=True,

        # Cho phép NULL
        null=True
    )

    # URL ảnh online
    image_url = models.CharField(
        max_length=255,
        blank=True
    )

    # Trạng thái hoạt động
    active = models.BooleanField(default=True)

    # Thứ tự hiển thị
    order = models.PositiveIntegerField(default=0)


    # ===== SAVE =====
    def save(self, *args, **kwargs):

        # Nếu chưa có slug
        if not self.slug:

            # Tự tạo slug từ tên
            self.slug = slugify(self.name)

        # Lưu dữ liệu
        super().save(*args, **kwargs)


    # ===== HIỂN THỊ OBJECT =====
    def __str__(self):

        # Trả về tên dịch vụ
        return self.name




# ===== MODEL ĐẶT PHÒNG =====
class Reservation(models.Model):


    # ===== TRẠNG THÁI THANH TOÁN =====
    PAYMENT_STATUS_CHOICES = (

        # Chưa thanh toán
        ('pending', 'Pending'),

        # Đã thanh toán
        ('paid', 'Paid'),

        # Thanh toán thất bại
        ('failed', 'Failed'),

        # Đã hoàn tiền
        ('refunded', 'Refunded'),
    )


    # ===== PHƯƠNG THỨC THANH TOÁN =====
    PAYMENT_METHOD_CHOICES = (

        # Tiền mặt
        ('cash', 'Tiền mặt'),

        # QR MoMo
        ('momo_qr', 'Chuyển khoản MoMo'),

        # Quẹt thẻ
        ('cards', 'Quẹt thẻ'),
    )


    # ===== HẰNG SỐ =====

    # % tiền cọc mặc định
    DEFAULT_DEPOSIT_PERCENTAGE = Decimal('30.00')

    # % phí bồi thường
    DAMAGE_FEE_PERCENTAGE = Decimal('10.00')



    # ===== THÔNG TIN PHÒNG =====

    # Liên kết với Room
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE
    )

    # Ngày check-in
    check_in_date = models.DateField(
        null=True,
        blank=True
    )

    # Ngày check-out
    check_out_date = models.DateField(
        null=True,
        blank=True
    )

    # Số người lớn
    adults = models.PositiveIntegerField(default=1)

    # Số trẻ em
    children = models.PositiveIntegerField(default=0)

    # Thời gian tạo booking
    created_at = models.DateTimeField(auto_now_add=True)

    # Mã booking duy nhất
    booking_code = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    # Người dùng đặt phòng
    user = models.ForeignKey(

        User,

        # Nếu xóa user -> user = NULL
        on_delete=models.SET_NULL,

        null=True,
        blank=True
    )



    # ===== THÔNG TIN KHÁCH HÀNG =====

    first_name = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    last_name = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    email = models.EmailField(
        null=True,
        blank=True
    )

    phone = models.CharField(
        max_length=15,
        null=True,
        blank=True
    )

    address = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    city = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    state = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    postcode = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    adhar_id = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    # Ghi chú khách hàng
    note = models.TextField(blank=True)



    # ===== CHECK-IN / CHECK-OUT =====

    # Đã check-in chưa
    is_checked_in = models.BooleanField(default=False)

    # Thời gian check-in
    checked_in_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Người lớn thực tế check-in
    checked_in_adults = models.PositiveIntegerField(default=0)

    # Trẻ em thực tế check-in
    checked_in_children = models.PositiveIntegerField(default=0)

    # Đã check-out chưa
    is_checked_out = models.BooleanField(default=False)



    # ===== THANH TOÁN =====

    # Phương thức thanh toán
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash',
    )

    # Trạng thái thanh toán
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
    )



    # ===== GIÁ TIỀN =====

    # Tổng tiền trước thuế
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    # Thuế GST
    gst = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    # Tổng tiền
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )



    # ===== TIỀN CỌC =====

    # % cọc
    deposit_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('30.00')
    )

    # Tiền cọc
    deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Tiền còn lại
    balance_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )



    # ===== COUPON =====

    # Mã giảm giá
    coupon = models.ForeignKey(

        Coupon,

        on_delete=models.SET_NULL,

        null=True,
        blank=True
    )

    # Số tiền giảm
    discount_applied = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )



    # ===== DỊCH VỤ =====

    # Tổng tiền dịch vụ
    service_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    # Dịch vụ khách chọn
    selected_services = models.ManyToManyField(

        Service,

        blank=True,

        related_name='reservations'
    )



    # ===== PHÍ HƯ HỎNG =====

    # Có hư hỏng không
    damage_reported = models.BooleanField(default=False)

    # Ghi chú hư hỏng
    damage_notes = models.TextField(blank=True)

    # Phí bồi thường
    damage_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )



    # ===== TỔNG CUỐI =====

    final_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )



    # ===== THỜI GIAN =====

    # Thời gian checkout
    checkout_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Thời gian gửi hóa đơn
    invoice_notified_at = models.DateTimeField(
        null=True,
        blank=True
    )



    # ===== HỦY BOOKING =====

    # Đã hủy chưa
    is_canceled = models.BooleanField(default=False)

    # Thời gian hủy
    canceled_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Lý do hủy
    canceled_reason = models.CharField(
        max_length=255,
        blank=True
    )



    # ===== CHECK-IN SỚM =====

    # Ngày check-in thực tế
    actual_check_in_date = models.DateField(
        null=True,
        blank=True
    )

    # Số ngày check-in sớm
    early_checkin_days = models.PositiveIntegerField(default=0)

    # Phí check-in sớm
    early_checkin_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )



    # ===== CHECK-OUT SỚM =====

    # Ngày checkout thực tế
    actual_check_out_date = models.DateField(
        null=True,
        blank=True
    )

    # Số ngày checkout sớm
    early_checkout_days = models.PositiveIntegerField(default=0)

    # Tiền hoàn checkout sớm
    early_checkout_refund = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )



    # ===== THANH TOÁN HYBRID =====

    # Tiền cọc qua QR
    deposit_paid_via_qr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Tiền còn lại trả khi check-in
    balance_paid_at_checkin = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )



    # ===== BIÊN LAI =====

    # Ảnh biên lai
    deposit_receipt = models.ImageField(
        upload_to='uploads/deposit_receipts/',
        null=True,
        blank=True
    )

    # Thời gian upload
    deposit_receipt_uploaded_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Đã xác nhận chưa
    deposit_confirmed = models.BooleanField(default=False)

    # Thời gian xác nhận
    deposit_confirmed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Người xác nhận
    deposit_confirmed_by = models.ForeignKey(

        User,

        null=True,
        blank=True,

        on_delete=models.SET_NULL,

        related_name='confirmed_deposits'
    )

    def calculate_early_checkin_fee(self):
        """Tính phí check-in sớm"""
        if not self.early_checkin_days or self.early_checkin_days <= 0:
            return Decimal('0.00')
        
        daily_rate = self.room.price
        early_fee = (daily_rate * Decimal('0.50')) * Decimal(self.early_checkin_days)
        return early_fee

    def sync_financial_fields(self):
        """Đồng bộ các trường tài chính"""
        self.early_checkin_fee = self.calculate_early_checkin_fee()
        self.final_total = self.total + self.damage_fee + self.early_checkin_fee

    def save(self, *args, **kwargs):
        """Tạo booking code tự động nếu chưa có"""
        if not self.booking_code:
            self.booking_code = str(uuid.uuid4())[:12].upper()
        super().save(*args, **kwargs)

    def can_check_in(self):
        """Kiểm tra xem booking có thể check-in được không"""
        # Kiểm tra booking đã check-in chưa
        if self.is_checked_in:
            return False, "Booking này đã check-in rồi"
        
        # Kiểm tra ngày check-in
        today = timezone.now().date()
        if self.check_in_date > today:
            return False, f"Check-in sớm, vui lòng quay lại vào {self.check_in_date}"
        
        # Kiểm tra status
        if self.status not in ['confirmed', 'deposits_confirmed']:
            return False, "Booking chưa được xác nhận"
        
        return True, "Có thể check-in"

    def can_check_out(self):
        """Kiểm tra xem booking có thể checkout được không"""
        # Phải check-in rồi mới checkout
        if not self.is_checked_in:
            return False, "Chưa check-in, không thể checkout"
        
        # Không được checkout trước ngày
        today = timezone.now().date()
        if today < self.check_out_date:
            return False, f"Chưa tới ngày checkout, checkout vào {self.check_out_date}"
        
        return True, "Có thể checkout"

    def calculate_final_total(self):
        """Tính tổng tiền cuối cùng"""
        total = self.total
        
        # Thêm phí damage nếu có
        if self.damage_fee:
            total += self.damage_fee
        
        # Thêm phí early check-in nếu có
        if self.early_checkin_fee:
            total += self.early_checkin_fee
        
        # Trừ coupon discount nếu có
        if self.coupon_discount:
            total -= self.coupon_discount
        
        return total

    def get_number_of_nights(self):
        """Lấy số đêm ở lại"""
        if self.check_in_date and self.check_out_date:
            nights = (self.check_out_date - self.check_in_date).days
            return max(nights, 1)  # Tối thiểu 1 đêm
        return 0

    def calculate_refund_amount(self):
        """Tính số tiền hoàn lại"""
        if self.status == 'cancelled':
            # Hoàn lại 80% tiền deposit nếu hủy trước ngày check-in 2 tuần
            if self.check_in_date:
                days_until_checkin = (self.check_in_date - timezone.now().date()).days
                if days_until_checkin >= 14:
                    return self.deposit_paid * Decimal('0.80')
                elif days_until_checkin >= 7:
                    return self.deposit_paid * Decimal('0.50')
        return Decimal('0.00')

    def get_booking_code_display(self):
        """Lấy booking code định dạng hiển thị"""
        if self.booking_code:
            # Format: XXXX-XXXX-XXXX
            code = str(self.booking_code).upper()
            return f"{code[:4]}-{code[4:8]}-{code[8:]}"
        return "N/A"

    def is_payment_pending(self):
        """Kiểm tra xem booking có đang chờ thanh toán không"""
        return self.status == 'pending' and not self.is_paid

    def is_cancelled(self):
        """Kiểm tra xem booking đã hủy chưa"""
        return self.status == 'cancelled'

    def is_completed(self):
        """Kiểm tra xem booking đã hoàn thành chưa"""
        return self.status == 'checked_out' and self.is_checked_in

    def validate_booking_dates(self):
        """Validate ngày check-in và check-out"""
        errors = {}
        
        if self.check_in_date >= self.check_out_date:
            errors['check_out_date'] = 'Ngày checkout phải sau ngày check-in'
        
        today = timezone.now().date()
        if self.check_in_date < today:
            errors['check_in_date'] = 'Ngày check-in không được trong quá khứ'
        
        return errors

    def room_is_available_during_stay(self):
        """Kiểm tra phòng có trống suốt thời gian ở lại không"""
        if not self.room:
            return False
        
        # Kiểm tra xem có booking khác xung đột không
        conflicting = Reservation.objects.filter(
            room=self.room,
            status__in=['confirmed', 'checked_in'],
            check_in_date__lt=self.check_out_date,
            check_out_date__gt=self.check_in_date
        ).exclude(id=self.id)
        
        return not conflicting.exists()