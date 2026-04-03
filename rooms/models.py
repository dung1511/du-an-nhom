from django.db import models
from django.contrib.auth.models import User
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from datetime import date, timedelta

class RoomManager(models.Manager):
    def available_rooms(self, check_in, check_out, adults):
        reserved_rooms = Reservation.objects.filter(
            check_in_date__lt=check_out,
            check_out_date__gt=check_in
        ).values_list('room_id', flat=True)

        return self.filter(capacity__gte=adults).exclude(id__in=reserved_rooms)


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
    image = models.ImageField(upload_to='rooms/', blank=True, null=True)

    objects = RoomManager()

    def __str__(self):
        return self.name

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
    image = models.ImageField(upload_to='room_images/')

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


class Reservation(models.Model):
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
    is_checked_out = models.BooleanField(default=False) # Thêm trường này
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('pay_on_arrival', 'Pay on Arrival'),
            ('upi', 'UPI'),
            ('cards', 'Cards')
        ],
        default='pay_on_arrival',
    )

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    gst = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def clean(self):
        if self.check_in_date and self.check_out_date:
            if self.check_out_date <= self.check_in_date:
                raise ValidationError("Check-out date must be after check-in date.")

    def __str__(self):
        return f"Reservation for {self.room.name} from {self.check_in_date} to {self.check_out_date}"
    
    