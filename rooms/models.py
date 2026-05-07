<<<<<<< HEAD
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
=======
# ============================================================================
# IMPORTS - Thư viện và module cần thiết cho ứng dụng quản lý khách sạn
# ============================================================================
from django.db import models  # ORM của Django để định nghĩa model dữ liệu
from django.contrib.auth.models import User  # Model User mặc định của Django
from datetime import date, timedelta  # Làm việc với ngày tháng
from django.core.exceptions import ValidationError  # Xử lý lỗi validation
from django.utils import timezone  # Lấy thời gian hiện tại
from django.utils.text import slugify  # Chuyển chuỗi thành URL-friendly slug
from decimal import Decimal  # Dùng cho tính toán tiền tệ chính xác
import os  # Làm việc với đường dẫn file
import uuid  # Tạo ID duy nhất cho file uploads
from itertools import combinations  # Tạo tổ hợp phòng
>>>>>>> b311d48 (update feature admin room)

# ============================================================================
# HÀM HELPER - Tạo đường dẫn upload file duy nhất bằng UUID
# ============================================================================

def room_cover_upload_path(instance, filename):
    """
    Tạo đường dẫn lưu trữ ảnh bìa phòng.
    Cách làm: uploads/rooms/{uuid_ngẫu_nhiên}.{extension}
    Lợi ích: Tránh xung đột tên file khi nhiều người upload cùng lúc
    """
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"uploads/rooms/{uuid.uuid4().hex}{ext}"


def room_gallery_upload_path(instance, filename):
    """
    Tạo đường dẫn lưu trữ ảnh trong bộ sưu tập phòng.
    Cách làm: uploads/room-gallery/{uuid_ngẫu_nhiên}.{extension}
    """
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"uploads/room-gallery/{uuid.uuid4().hex}{ext}"


def service_image_upload_path(instance, filename):
    """
    Tạo đường dẫn lưu trữ ảnh dịch vụ.
    Cách làm: uploads/services/{uuid_ngẫu_nhiên}.{extension}
    """
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"uploads/services/{uuid.uuid4().hex}{ext}"


# ============================================================================
# ROOM MANAGER - Xử lý logic tìm kiếm và đề xuất phòng
# ============================================================================

class RoomManager(models.Manager):
    """
    Manager tùy chỉnh cho model Room.
    Cung cấp các phương thức để tìm phòng trống, tìm phòng phù hợp, 
    và đề xuất tổ hợp phòng cho nhóm khách.
    """
    
    def available_rooms(self, check_in, check_out, adults):
        """
        Tìm các phòng trống trong khoảng thời gian và đủ sức chứa.
        
        Các bước:
        1. Tìm các phòng đã được đặt chồng lấp thời gian check_in/check_out
        2. Loại trừ những phòng đó khỏi danh sách
        3. Lọc các phòng còn lại có sức chứa >= số người lớn
        
        Return: QuerySet các phòng trống
        """
        reserved_rooms = Reservation.objects.filter(
            check_in_date__lt=check_out,  # Đặt phòng bắt đầu trước check_out của chúng ta
            check_out_date__gt=check_in,  # Đặt phòng kết thúc sau check_in của chúng ta
            is_checked_out=False,  # Chỉ xem xét đặt phòng chưa hoàn thành
        ).values_list('room_id', flat=True)  # Lấy danh sách ID phòng

        return self.filter(capacity__gte=adults).exclude(id__in=reserved_rooms)

    def search_suitable_rooms(self, check_in, check_out, adults, children=0, limit=None):
        """
        Tìm phòng phù hợp cho nhóm khách (người lớn + trẻ em).
        Sắp xếp theo độ phù hợp: chọn phòng nhỏ nhất vừa đủ chứa khách (tối ưu chi phí).
        
        Tham số:
        - check_in: Ngày nhận phòng
        - check_out: Ngày trả phòng
        - adults: Số người lớn
        - children: Số trẻ em (mặc định 0)
        - limit: Số lượng phòng đề xuất (mặc định = tất cả)
        
        Quá trình:
        1. Tính tổng số khách = người lớn + trẻ em
        2. Tìm phòng đã đặt (để loại bỏ)
        3. Lọc phòng có đủ sức chứa (tổng, người lớn, trẻ em)
        4. Sắp xếp theo sức chứa tổng (nhỏ nhất trước), rồi giá
        5. Giới hạn số lượng nếu có
        
        Return: QuerySet các phòng phù hợp
        """
        from django.db.models import F, Q
        
        total_guests = adults + children  # Tổng số khách
        
        # Tìm phòng trống
        reserved_rooms = Reservation.objects.filter(
            check_in_date__lt=check_out,
            check_out_date__gt=check_in,
            is_checked_out=False
        ).values_list('room_id', flat=True)
        
        # Tìm phòng có đủ capacity theo tất cả các tiêu chí
        suitable_rooms = self.filter(
            total_capacity__gte=total_guests,  # Tổng sức chứa >= tổng khách
            capacity_adults__gte=adults,  # Sức chứa người lớn >= số người lớn
            capacity_children__gte=children  # Sức chứa trẻ em >= số trẻ em
        ).exclude(id__in=reserved_rooms)
        
        # Sắp xếp: phòng nhỏ nhất vừa đủ (tối ưu), rồi theo giá (rẻ nhất)
        suitable_rooms = suitable_rooms.order_by('total_capacity', 'price')
        
        # Giới hạn số lượng nếu có
        if limit:
            suitable_rooms = suitable_rooms[:limit]
        
        return suitable_rooms

    def recommend_room_combinations(self, check_in, check_out, adults, children=0, max_rooms=2, limit=3):
        """
        Đề xuất tổ hợp nhiều phòng phù hợp cho nhóm khách (khi không có phòng đơn đủ).
        
        Ví dụ: Khách 6 người, không có phòng 6 người → đề xuất 2-3 phòng nhỏ hơn
        
        Tham số:
        - max_rooms: Tối đa bao nhiêu phòng trong một tổ hợp (thường 2)
        - limit: Số lượng tổ hợp đề xuất (thường 3 tổ hợp tốt nhất)
        
        Quá trình:
        1. Lấy danh sách tất cả phòng trống
        2. Tạo tổ hợp từ 2 đến max_rooms phòng
        3. Đánh điểm mỗi tổ hợp (dựa trên số phòng, sức chứa dư, tổng giá)
        4. Sắp xếp theo điểm (tốt nhất trước)
        5. Trả về top N tổ hợp
        
        Return: Danh sách các tổ hợp phòng được đề xuất
        """
        total_guests = adults + children
        # Lấy danh sách phòng trống, sắp xếp theo sức chứa, rồi giá
        available_rooms = list(
            self.filter(
                total_capacity__gte=1,  # Phòng có sức chứa >= 1 người
            )
            .exclude(
                id__in=Reservation.objects.filter(
                    check_in_date__lt=check_out,
                    check_out_date__gt=check_in,
                    is_checked_out=False,
                ).values_list('room_id', flat=True)
            )
            .order_by('total_capacity', 'price')
        )

        # Không có đủ phòng để tạo tổ hợp, hoặc khách < 1 người → trả về rỗng
        if len(available_rooms) < 2 or total_guests <= 0:
            return []

        scored_combinations = []
        max_group_size = 2 if max_rooms is None else max(2, max_rooms)

        # Tạo tất cả tổ hợp từ 2 đến max_group_size phòng
        for group_size in range(2, max_group_size + 1):
            for room_group in combinations(available_rooms, group_size):
                # Tính tổng sức chứa của tổ hợp
                total_capacity = sum(room.total_capacity or room.capacity for room in room_group)
                # Bỏ qua nếu không đủ chứa
                if total_capacity < total_guests:
                    continue

                # Tính tổng giá
                total_price = sum(room.price for room in room_group)
                # Điểm số: (số phòng, sức chứa dư, tổng giá)
                # Sắp xếp ưu tiên: ít phòng nhất, dư ít nhất, giá thấp nhất
                score = (
                    len(room_group),  # Ưu tiên tổ hợp ít phòng
                    total_capacity - total_guests,  # Ưu tiên sức chứa vừa đủ
                    total_price,  # Ưu tiên giá thấp
                )
                scored_combinations.append((score, room_group, total_capacity, total_price))

        # Sắp xếp theo điểm (từ tốt nhất)
        scored_combinations.sort(key=lambda item: item[0])

        results = []
        seen_sets = set()
        # Lấy top N tổ hợp tốt nhất
        for _, room_group, total_capacity, total_price in scored_combinations:
            # Tránh trùng lặp tổ hợp (dùng set các ID phòng)
            room_ids = tuple(sorted(room.id for room in room_group))
            if room_ids in seen_sets:
                continue
            seen_sets.add(room_ids)
            results.append(
                {
                    'rooms': room_group,
                    'total_capacity': total_capacity,
                    'total_price': total_price,
                }
            )
            # Dừng khi có đủ N tổ hợp
            if len(results) >= limit:
                break

        return results


# ============================================================================
# ROOM CATEGORY MODEL - Phân loại phòng (Deluxe, Standard, Suite, v.v.)
# ============================================================================

class RoomCategory(models.Model):
    """
    Lưu các loại phòng khác nhau trong khách sạn.
    Ví dụ: Deluxe, Standard, Suite, Presidential
    """
    name = models.CharField(max_length=50, unique=True)  # Tên loại phòng (không trùng)

    def __str__(self):
        return self.name


# ============================================================================
# ROOM MODEL - Thông tin chi tiết từng phòng
# ============================================================================

class Room(models.Model):
    """
    Model đại diện cho một phòng trong khách sạn.
    Lưu: tên, loại, sức chứa, kích cỡ, mô tả, giá, ảnh
    
    Sức chứa được chia thành 3 loại:
    - capacity_adults: Chỗ cho người lớn
    - capacity_children: Chỗ cho trẻ em
    - total_capacity: Tổng chỗ (tự động = adults + children)
    """
    
    SIZE_CHOICES = (
        ('S', 'Single Bedroom'),      # Phòng 1 giường
        ('D', 'Double Bedroom'),      # Phòng 2 giường
        ('T', 'Triple Bedroom'),      # Phòng 3+ giường
    )
    
    name = models.CharField(max_length=100)                      # Tên phòng (VD: "Room 101")
    category = models.ForeignKey(RoomCategory, on_delete=models.SET_NULL, null=True)  # Loại phòng
    capacity = models.PositiveIntegerField()                     # Sức chứa cơ bản
    size = models.CharField(max_length=1, choices=SIZE_CHOICES)  # Kích cỡ phòng
    capacity_adults = models.PositiveIntegerField(default=2)     # Số chỗ cho người lớn
    capacity_children = models.PositiveIntegerField(default=2)   # Số chỗ cho trẻ em
    total_capacity = models.PositiveIntegerField(default=4)      # Tổng sức chứa (tự động tính)
    description = models.TextField()                             # Mô tả phòng chi tiết
    price = models.DecimalField(max_digits=10, decimal_places=2) # Giá/đêm
    image = models.ImageField(upload_to=room_cover_upload_path, blank=True, null=True)  # Ảnh bìa

    objects = RoomManager()  # Sử dụng RoomManager tùy chỉnh

    def __str__(self):
        return self.name

    def can_accommodate(self, adults, children=0):
<<<<<<< HEAD
        """Return True when the room can host the given adults/children split."""
=======
        """
        Kiểm tra phòng này có thể chứa được nhóm khách không.
        
        Kiểm tra 3 điều kiện:
        1. Tổng sức chứa >= tổng khách (adults + children)
        2. Chỗ người lớn >= số người lớn
        3. Chỗ trẻ em >= số trẻ em
        
        Return: True nếu đủ, False nếu không
        """
>>>>>>> b311d48 (update feature admin room)
        adults = adults or 0
        children = children or 0
        total_guests = adults + children

        total_capacity = self.total_capacity or self.capacity or (self.capacity_adults + self.capacity_children)
        adults_capacity = self.capacity_adults or self.capacity or total_capacity
        children_capacity = self.capacity_children if self.capacity_children is not None else total_capacity

        return (
            adults >= 1
            and children >= 0
            and total_guests <= total_capacity
            and adults <= adults_capacity
            and children <= children_capacity
        )

    def availability_status(self):
        """Kiểm tra trạng thái phòng: 'Phòng trống' hoặc 'Đã đặt'"""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        return 'Phòng trống' if self.is_available(today, tomorrow) else 'Đã đặt'
    
    def save(self, *args, **kwargs):
        """Tự động tính tổng sức chứa khi lưu"""
        self.total_capacity = self.capacity_adults + self.capacity_children
        super().save(*args, **kwargs)

    def is_available(self, check_in=None, check_out=None):
        """
        Kiểm tra phòng có trống trong khoảng thời gian không.
        
        Nếu không truyền ngày → kiểm tra ngày hôm nay
        """
        if check_in is None:
            check_in = date.today()
        if check_out is None:
            check_out = check_in + timedelta(days=1)

        overlapping = Reservation.objects.filter(
            room=self,
            is_checked_out=False,
            check_in_date__lt=check_out,      # Đặt phòng bắt đầu trước ngày check_out của chúng ta
            check_out_date__gt=check_in       # Đặt phòng kết thúc sau ngày check_in của chúng ta
        )
        return not overlapping.exists()  # Trả về True nếu không có đặt phòng nào chồng lấp

    @property
    def availability_status(self):
        """
        Property để lấy trạng thái phòng (dùng @property để gọi như attribute).
        Ví dụ: room.availability_status (thay vì room.availability_status())
        """
        try:
            if self.is_available():
                return "Phòng trống"
            return "Đã đặt"
        except Exception as e:
            print(f"Lỗi kiểm tra trạng thái: {e}")
            return "Đang kiểm tra"


# ============================================================================
# ROOM IMAGE MODEL - Ảnh bộ sưu tập cho từng phòng
# ============================================================================

class RoomImage(models.Model):
    """
    Lưu các ảnh bổ sung cho phòng (gallery).
    Mỗi phòng có thể có nhiều ảnh.
    """
    room = models.ForeignKey(Room, related_name='images', on_delete=models.CASCADE)  # Liên kết tới phòng
    image = models.ImageField(upload_to=room_gallery_upload_path)                    # Ảnh

    def __str__(self):
        return f"Image for {self.room.name}"


# ============================================================================
# COUPON MODEL - Mã giảm giá
# ============================================================================

class Coupon(models.Model):
    """
    Lưu các mã giảm giá khách sạn.
    Ví dụ: SAVE20 (giảm 20%), SUMMER10 (giảm 10%), v.v.
    """
    code = models.CharField(max_length=50, unique=True)                 # Mã coupon (VD: "SAVE20")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)  # Phần trăm giảm
    active = models.BooleanField(default=True)                          # Coupon có hoạt động không
    valid_from = models.DateField()                                     # Ngày bắt đầu hiệu lực
    valid_to = models.DateField()                                       # Ngày kết thúc hiệu lực

    def __str__(self):
        return self.code


# ============================================================================
# SERVICE MODEL - Dịch vụ bổ sung (ăn sáng, giặt ủi, v.v.)
# ============================================================================

class Service(models.Model):
    """
    Lưu các dịch vụ bổ sung khách sạn mà khách có thể thêm.
    Ví dụ: Ăn sáng, Giặt ủi, Đưa đón sân bay, v.v.
    """
    name = models.CharField(max_length=120, unique=True)                # Tên dịch vụ
    slug = models.SlugField(max_length=140, unique=True)                # URL-friendly slug
    description = models.TextField(blank=True)                          # Mô tả chi tiết
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Giá dịch vụ
    image = models.ImageField(upload_to=service_image_upload_path, blank=True, null=True)  # Ảnh dịch vụ
    image_url = models.CharField(max_length=255, blank=True)            # URL ảnh ngoài (nếu có)
    active = models.BooleanField(default=True)                          # Dịch vụ có hoạt động không
    order = models.PositiveIntegerField(default=0)                      # Thứ tự hiển thị

    def save(self, *args, **kwargs):
        """Tự động tạo slug từ tên nếu chưa có"""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name



# ============================================================================
# RESERVATION MODEL - Đơn đặt phòng (Model lớn nhất - quản lý toàn bộ booking)
# ============================================================================

class Reservation(models.Model):
    """
    Model đại diện cho một đơn đặt phòng hoàn chỉnh.
    
    Chức năng chính:
    1. Lưu thông tin khách hàng (tên, email, điện thoại, địa chỉ)
    2. Lưu thông tin phòng và ngày check-in/check-out
    3. Quản lý thanh toán (cọc 30% trước, số dư 70% tại check-in)
    4. Quản lý dịch vụ bổ sung (ăn sáng, giặt ủi, v.v.)
    5. Quản lý phí phát sinh (phí check-in sớm, phí thiệt hại, hoàn tiền check-out sớm)
    6. Quản lý check-in/check-out và lưu tối hạn
    
    Quy trình thanh toán:
    - Khách đặt phòng → Thanh toán cọc 30% → Nhận mã booking
    - Cọc qua QR → Upload biên lai → Admin xác nhận
    - Tại check-in → Thanh toán số dư 70% + phí phát sinh (nếu có)
    - Tại check-out → Kiểm tra thiệt hại → Lập hóa đơn cuối cùng
    """
    
    # ========== HẰNG SỐ ĐỊNH NGHĨA ==========
    
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Chưa thanh toán'),           # Chưa thanh toán gì
        ('paid', 'Đã thanh toán'),                # Đã thanh toán đủ
        ('failed', 'Thanh toán thất bại'),        # QR thanh toán lỗi
        ('refunded', 'Đã hoàn tiền'),             # Hủy booking → hoàn tiền
    )

    PAYMENT_METHOD_CHOICES = (
<<<<<<< HEAD
        ('cash', 'Tiền mặt'),
        ('momo_qr', 'Chuyển khoản MoMo'),
        ('cards', 'Quẹt thẻ'),
    )

    DEFAULT_DEPOSIT_PERCENTAGE = Decimal('30.00')
    DAMAGE_FEE_PERCENTAGE = Decimal('10.00')

    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    check_in_date = models.DateField(null=True, blank=True)
    check_out_date = models.DateField(null=True, blank=True)
    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    postcode = models.CharField(max_length=20, null=True, blank=True)
    adhar_id = models.CharField(max_length=20, null=True, blank=True)
    note = models.TextField(blank=True)
    is_checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_adults = models.PositiveIntegerField(default=0)
    checked_in_children = models.PositiveIntegerField(default=0)
    is_checked_out = models.BooleanField(default=False) # Thêm trường này
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash',
=======
        ('cash', 'Tiền mặt'),                     # Thanh toán tại chỗ
        ('momo_qr', 'Chuyển khoản MoMo'),         # QR code MoMo
        ('cards', 'Quẹt thẻ'),                    # Thẻ tín dụng/ghi nợ
    )

    DEFAULT_DEPOSIT_PERCENTAGE = Decimal('30.00')  # Cọc 30% giá phòng
    DAMAGE_FEE_PERCENTAGE = Decimal('10.00')       # Phí thiệt hại = 10% giá phòng
    
    # ========== THÔNG TIN PHÒNG & NGÀY THÁNG ==========
    
    room = models.ForeignKey(Room, on_delete=models.CASCADE)          # Phòng được đặt
    check_in_date = models.DateField(null=True, blank=True)          # Ngày nhận phòng (dự kiến)
    check_out_date = models.DateField(null=True, blank=True)         # Ngày trả phòng (dự kiến)
    adults = models.PositiveIntegerField(default=1)                  # Số người lớn đặt trước
    children = models.PositiveIntegerField(default=0)                # Số trẻ em đặt trước
    created_at = models.DateTimeField(auto_now_add=True)             # Thời gian tạo booking
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # User nếu khách có đăng nhập
    
    # ========== THÔNG TIN KHÁCH HÀNG ==========
    
    first_name = models.CharField(max_length=100, null=True, blank=True)     # Tên
    last_name = models.CharField(max_length=100, null=True, blank=True)      # Họ
    email = models.EmailField(null=True, blank=True)                         # Email (gửi invoice & xác nhận)
    phone = models.CharField(max_length=15, null=True, blank=True)           # Điện thoại liên hệ
    address = models.CharField(max_length=200, null=True, blank=True)        # Địa chỉ
    city = models.CharField(max_length=100, null=True, blank=True)           # Thành phố
    state = models.CharField(max_length=100, null=True, blank=True)          # Tỉnh/Bang
    postcode = models.CharField(max_length=20, null=True, blank=True)        # Mã bưu điện
    adhar_id = models.CharField(max_length=20, null=True, blank=True)        # ID quốc gia (CMND/CCCD)
    note = models.TextField(blank=True)                                      # Ghi chú đặc biệt của khách
    
    # ========== THÔNG TIN CHECK-IN / CHECK-OUT ==========
    
    is_checked_in = models.BooleanField(default=False)                       # Khách đã check-in chưa?
    checked_in_at = models.DateTimeField(null=True, blank=True)              # Thời gian check-in thực tế
    checked_in_adults = models.PositiveIntegerField(default=0)               # Số người lớn check-in thực tế
    checked_in_children = models.PositiveIntegerField(default=0)             # Số trẻ em check-in thực tế
    is_checked_out = models.BooleanField(default=False)                      # Khách đã check-out chưa?
    
    # ========== THÔNG TIN THANH TOÁN ==========
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash',                           # Mặc định: thanh toán tiền mặt
>>>>>>> b311d48 (update feature admin room)
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',                        # Mặc định: chưa thanh toán
    )

<<<<<<< HEAD
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    gst = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    deposit_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('30.00'))
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    service_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selected_services = models.ManyToManyField(Service, blank=True, related_name='reservations')
    damage_reported = models.BooleanField(default=False)
    damage_notes = models.TextField(blank=True)
    damage_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    final_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    checkout_at = models.DateTimeField(null=True, blank=True)
    invoice_notified_at = models.DateTimeField(null=True, blank=True)
    # Early check-in fields
    actual_check_in_date = models.DateField(null=True, blank=True)  # Ngày check-in thực tế nếu sớm hơn
    early_checkin_days = models.PositiveIntegerField(default=0)  # Số ngày check-in sớm
    early_checkin_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Phí check-in sớm
    # Early check-out fields
    actual_check_out_date = models.DateField(null=True, blank=True)  # Ngày check-out thực tế nếu sớm hơn
    early_checkout_days = models.PositiveIntegerField(default=0)  # Số ngày check-out sớm
    early_checkout_refund = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Hoàn tiền checkout sớm
    # Hybrid payment
    deposit_paid_via_qr = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Số tiền deposit thanh toán qua QR
    balance_paid_at_checkin = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Số tiền còn lại thanh toán tại check-in
    # Biên lai chuyển khoản do khách upload (QR -> upload biên lai)
    deposit_receipt = models.ImageField(upload_to='uploads/deposit_receipts/', null=True, blank=True)
    deposit_receipt_uploaded_at = models.DateTimeField(null=True, blank=True)
    deposit_confirmed = models.BooleanField(default=False)
    deposit_confirmed_at = models.DateTimeField(null=True, blank=True)
    deposit_confirmed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='confirmed_deposits')
=======
    # Tính tiền
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)          # Tổng giá phòng (chưa gồm dịch vụ)
    gst = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)               # Thuế VAT (nếu có)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)             # Tổng (subtotal + gst + service + mã giảm)
    deposit_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('30.00'))  # % cọc (thường 30%)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))      # Số tiền cọc cần thanh toán
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))        # Số tiền còn lại (tại check-in)
    
    # Mã giảm giá
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)   # Mã coupon được áp dụng
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Số tiền giảm
    
    # Dịch vụ
    service_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)     # Tổng giá dịch vụ
    selected_services = models.ManyToManyField(Service, blank=True, related_name='reservations')  # Danh sách dịch vụ chọn
    
    # Phí phát sinh
    damage_reported = models.BooleanField(default=False)                                    # Có báo cáo thiệt hại không?
    damage_notes = models.TextField(blank=True)                                             # Ghi chú chi tiết thiệt hại
    damage_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Phí thiệt hại (nếu có)
    
    # Tổng cuối cùng & thời gian
    final_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Tổng tiền phải thanh toán (sau tất cả phí/hoàn tiền)
    checkout_at = models.DateTimeField(null=True, blank=True)                               # Thời gian checkout
    invoice_notified_at = models.DateTimeField(null=True, blank=True)                       # Thời gian gửi hóa đơn cho khách
    
    # ========== THÔNG TIN CHECK-IN SỚM & CHECK-OUT SỚM ==========
    
    actual_check_in_date = models.DateField(null=True, blank=True)                          # Ngày check-in thực tế (nếu check-in sớm)
    early_checkin_days = models.PositiveIntegerField(default=0)                             # Số ngày check-in sớm
    early_checkin_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Phí check-in sớm (50% giá phòng/ngày)
    
    actual_check_out_date = models.DateField(null=True, blank=True)                         # Ngày check-out thực tế (nếu check-out sớm)
    early_checkout_days = models.PositiveIntegerField(default=0)                            # Số ngày check-out sớm
    early_checkout_refund = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Hoàn tiền check-out sớm (50% giá phòng/ngày)
    
    # ========== THÔNG TIN THANH TOÁN HYBRID (QR + Tiền mặt) ==========
    
    deposit_paid_via_qr = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))   # Số tiền cọc thanh toán qua QR
    balance_paid_at_checkin = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # Số tiền trả tại check-in
    
    # ========== THÔNG TIN BIÊN LAI & XÁC NHẬN CỌC ==========
    
    deposit_receipt = models.ImageField(upload_to='uploads/deposit_receipts/', null=True, blank=True)  # Biên lai chuyển khoản (ảnh upload)
    deposit_receipt_uploaded_at = models.DateTimeField(null=True, blank=True)               # Thời gian khách upload biên lai
    deposit_confirmed = models.BooleanField(default=False)                                  # Admin đã xác nhận cọc chưa? (KEY FIELD!)
    deposit_confirmed_at = models.DateTimeField(null=True, blank=True)                      # Thời gian admin xác nhận
    deposit_confirmed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='confirmed_deposits')  # Admin xác nhận
>>>>>>> b311d48 (update feature admin room)
    def clean(self):
        if self.check_in_date and self.check_out_date:
            if self.check_out_date <= self.check_in_date:
                raise ValidationError("Check-out date must be after check-in date.")

        adults = self.adults or 0
        children = self.children or 0
        if self.room_id and not self.room.can_accommodate(adults=adults, children=children):
            raise ValidationError("Số lượng khách vượt quá sức chứa của phòng.")

    def __str__(self):
        return f"Reservation for {self.room.name} from {self.check_in_date} to {self.check_out_date}"

    def calculate_deposit_amount(self):
        return (self.total * self.deposit_percentage) / Decimal('100')

    def calculate_balance_due(self):
        return self.total - self.calculate_deposit_amount()

    def calculate_damage_fee(self):
        return (self.total * self.DAMAGE_FEE_PERCENTAGE) / Decimal('100')

    def calculate_early_checkin_fee(self):
        """Tính phí check-in sớm: 50% giá phòng cho mỗi ngày"""
        if not self.actual_check_in_date or not self.check_in_date or self.actual_check_in_date >= self.check_in_date:
            return Decimal('0.00')
        
        days_early = (self.check_in_date - self.actual_check_in_date).days
        if days_early <= 0:
            return Decimal('0.00')
        
        # Tính phí: 50% giá phòng cho mỗi ngày check-in sớm
        daily_rate = self.room.price if self.room else Decimal('0.00')
        early_fee = (daily_rate * Decimal('0.50')) * Decimal(days_early)
        return early_fee

    def calculate_early_checkout_refund(self):
        """Tính tiền hoàn lại nếu check-out sớm: 50% giá phòng cho mỗi ngày"""
        if not self.actual_check_out_date or not self.check_out_date or self.actual_check_out_date >= self.check_out_date:
            return Decimal('0.00')
        
        days_early = (self.check_out_date - self.actual_check_out_date).days
        if days_early <= 0:
            return Decimal('0.00')
        
        # Hoàn lại: 50% giá phòng cho mỗi ngày check-out sớm
        daily_rate = self.room.price if self.room else Decimal('0.00')
        refund = (daily_rate * Decimal('0.50')) * Decimal(days_early)
        return refund

    def sync_financial_fields(self):
        self.deposit_amount = self.calculate_deposit_amount()
        self.balance_due = self.calculate_balance_due()
        self.damage_fee = self.calculate_damage_fee() if self.damage_reported else Decimal('0.00')
        self.early_checkin_fee = self.calculate_early_checkin_fee()
        self.early_checkout_refund = self.calculate_early_checkout_refund()
        self.final_total = self.total + self.damage_fee + self.early_checkin_fee - self.early_checkout_refund

    @property
    def booking_code(self):
        if not self.pk:
            return ''
        return f"BK{self.pk:06d}"

    @property
    def can_cancel_online(self):
        if self.is_checked_in or self.is_checked_out:
            return False

        if not self.check_in_date:
            return True

        return timezone.now().date() <= self.check_in_date

    @classmethod
    def get_reservation_id_from_booking_code(cls, booking_code):
        if not booking_code:
            raise ValueError('Mã booking không hợp lệ.')

        normalized = booking_code.strip().upper()
        if normalized.startswith('#'):
            normalized = normalized[1:]
        if normalized.startswith('BK'):
            normalized = normalized[2:]

        if not normalized.isdigit():
            raise ValueError('Mã booking không hợp lệ.')

        return int(normalized)
    
    