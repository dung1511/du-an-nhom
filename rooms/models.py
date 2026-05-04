from django.db import models
from django.contrib.auth.models import User
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from django.utils.text import slugify
from decimal import Decimal
import os
import uuid
from itertools import combinations


def room_cover_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"uploads/rooms/{uuid.uuid4().hex}{ext}"


def room_gallery_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"uploads/room-gallery/{uuid.uuid4().hex}{ext}"


def service_image_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"uploads/services/{uuid.uuid4().hex}{ext}"

class RoomManager(models.Manager):
    def available_rooms(self, check_in, check_out, adults):
        """Tìm phòng trống và đủ sức chứa"""
        reserved_rooms = Reservation.objects.filter(
            check_in_date__lt=check_out,
            check_out_date__gt=check_in,
            is_checked_out=False,
        ).values_list('room_id', flat=True)

        return self.filter(capacity__gte=adults).exclude(id__in=reserved_rooms)

    def search_suitable_rooms(self, check_in, check_out, adults, children=0, limit=None):
        """
        Tìm phòng phù hợp cho nhóm khách (adults + children).
        Sắp xếp theo độ phù hợp: phòng nhỏ nhất vừa đủ chứa khách.
        
        Args:
            check_in: Ngày nhận phòng
            check_out: Ngày trả phòng
            adults: Số người lớn
            children: Số trẻ em (default 0)
            limit: Số lượng phòng đề xuất (default None = tất cả)
        
        Returns:
            QuerySet các phòng phù hợp, sắp xếp theo độ phù hợp
        """
        from django.db.models import F, Q
        
        total_guests = adults + children
        
        # Tìm phòng trống
        reserved_rooms = Reservation.objects.filter(
            check_in_date__lt=check_out,
            check_out_date__gt=check_in,
            is_checked_out=False
        ).values_list('room_id', flat=True)
        
        # Tìm phòng có đủ capacity
        suitable_rooms = self.filter(
            total_capacity__gte=total_guests,  # Tổng sức chứa >= tổng khách
            capacity_adults__gte=adults,  # Sức chứa người lớn >= số người lớn
            capacity_children__gte=children  # Sức chứa trẻ em >= số trẻ em
        ).exclude(id__in=reserved_rooms)
        
        # Sắp xếp theo độ phù hợp: total_capacity nhỏ nhất (phòng tối nhất vừa đủ)
        # sau đó sắp xếp theo giá (rẻ nhất đầu)
        suitable_rooms = suitable_rooms.order_by('total_capacity', 'price')
        
        if limit:
            suitable_rooms = suitable_rooms[:limit]
        
        return suitable_rooms

    def recommend_room_combinations(self, check_in, check_out, adults, children=0, max_rooms=2, limit=3):
        """Đề xuất tổ hợp phòng phù hợp cho nhóm khách."""
        total_guests = adults + children
        available_rooms = list(
            self.filter(
                total_capacity__gte=1,
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

        if len(available_rooms) < 2 or total_guests <= 0:
            return []

        scored_combinations = []
        max_group_size = 2 if max_rooms is None else max(2, max_rooms)

        for group_size in range(2, max_group_size + 1):
            for room_group in combinations(available_rooms, group_size):
                total_capacity = sum(room.total_capacity or room.capacity for room in room_group)
                if total_capacity < total_guests:
                    continue

                total_price = sum(room.price for room in room_group)
                score = (
                    len(room_group),
                    total_capacity - total_guests,
                    total_price,
                )
                scored_combinations.append((score, room_group, total_capacity, total_price))

        scored_combinations.sort(key=lambda item: item[0])

        results = []
        seen_sets = set()
        for _, room_group, total_capacity, total_price in scored_combinations:
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
            if len(results) >= limit:
                break

        return results


class RoomCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Room(models.Model):
    SIZE_CHOICES = (
        ('S', 'Single Bedroom'),
        ('D', 'Double Bedroom'),
        ('T', 'Triple Bedroom'),
    )
    
    name = models.CharField(max_length=100)
    category = models.ForeignKey(RoomCategory, on_delete=models.SET_NULL, null=True)
    capacity = models.PositiveIntegerField()
    size = models.CharField(max_length=1, choices=SIZE_CHOICES)
    # Thêm default=2 hoặc default=4 vào các trường mới
    capacity_adults = models.PositiveIntegerField(default=2)
    capacity_children = models.PositiveIntegerField(default=2)
    total_capacity = models.PositiveIntegerField(default=4) # Thêm default ở đây
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to=room_cover_upload_path, blank=True, null=True)

    objects = RoomManager()

    def __str__(self):
        return self.name

    def can_accommodate(self, adults, children=0):
        """Return True when the room can host the given adults/children split."""
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
        today = date.today()
        tomorrow = today + timedelta(days=1)
        return 'Phòng trống' if self.is_available(today, tomorrow) else 'Đã đặt'
    
    def save(self, *args, **kwargs):
        self.total_capacity = self.capacity_adults + self.capacity_children
        super().save(*args, **kwargs)

    def is_available(self, check_in=None, check_out=None):
        """Kiểm tra phòng trống"""
        if check_in is None:
            check_in = date.today()
        if check_out is None:
            check_out = check_in + timedelta(days=1)

        # Import Reservation ở đây để tránh lỗi vòng lặp
        from .models import Reservation 
        
        overlapping = Reservation.objects.filter(
            room=self,
            is_checked_out=False,
            check_in_date__lt=check_out,
            check_out_date__gt=check_in
        )
        return not overlapping.exists()

    # 2. SAU ĐÓ MỚI GỌI TRONG PROPERTY NÀY
    @property
    def availability_status(self):
        try:
            # Gọi hàm đã định nghĩa ở trên
            if self.is_available():
                return "Phòng trống"
            return "Đã đặt"
        except Exception as e:
            print(f"Lỗi kiểm tra trạng thái: {e}")
            return "Đang kiểm tra"

class RoomImage(models.Model):
    room = models.ForeignKey(Room, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to=room_gallery_upload_path)

    def __str__(self):
        return f"Image for {self.room.name}"


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    active = models.BooleanField(default=True)
    valid_from = models.DateField()
    valid_to = models.DateField()

    def __str__(self):
        return self.code


class Service(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    image = models.ImageField(upload_to=service_image_upload_path, blank=True, null=True)
    image_url = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Reservation(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('pay_on_arrival', 'Cash on Arrival'),
        ('cash', 'Cash'),
        ('momo_qr', 'MoMo QR'),
        ('upi', 'UPI'),
        ('cards', 'Cards'),
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
        default='pay_on_arrival',
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
    )

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

    def sync_financial_fields(self):
        self.deposit_amount = self.calculate_deposit_amount()
        self.balance_due = self.calculate_balance_due()
        self.damage_fee = self.calculate_damage_fee() if self.damage_reported else Decimal('0.00')
        self.final_total = self.total + self.damage_fee

    @property
    def booking_code(self):
        if not self.pk:
            return ''
        return f"BK{self.pk:06d}"

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
    
    