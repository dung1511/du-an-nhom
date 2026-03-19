from django.db import models
from django.contrib.auth.models import User

class RoomManager(models.Manager):
    def available_rooms(self, check_in, check_out, adults):
        reserved_rooms = Reservation.objects.filter(
            check_in_date__lt=check_out,
            check_out_date__gt=check_in
        ).values_list('room_id', flat=True)
        return self.filter(capacity__gte=adults).exclude(id__in=reserved_rooms)

# --- MODEL MỚI: TIỆN ÍCH DỊCH VỤ ---
class Service(models.Model):
    name = models.CharField(max_length=100)
    # Dùng để chứa class icon của FontAwesome (VD: fas fa-wifi)
    icon = models.CharField(max_length=50, help_text="Nhập class FontAwesome (vd: fas fa-wifi)")

    def __str__(self):
        return self.name

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
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='rooms/', blank=True, null=True)
    
    # --- THÊM LIÊN KẾT ĐẾN SERVICES ---
    services = models.ManyToManyField(Service, blank=True, related_name='rooms')
    
    objects = RoomManager()

    def __str__(self):
        return self.name
    
    def is_available(self, check_in, check_out):
        overlapping_reservations = Reservation.objects.filter(
            room=self,
            check_in_date__lt=check_out,
            check_out_date__gt=check_in
        ).exists()
        return not overlapping_reservations

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
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    adults = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.CharField(max_length=200 ,null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    postcode = models.CharField(max_length=20, null=True, blank=True)
    adhar_id = models.CharField(max_length=20, null=True, blank=True)
    note = models.TextField(blank=True) 
    
    payment_method = models.CharField(
        max_length=20,
        choices=[('pay_on_arrival', 'Pay on Arrival'), ('upi', 'UPI'), ('cards', 'Cards')],
        null=False,
        blank=False,
        default='pay_on_arrival',
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    gst = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Reservation for {self.room.name} from {self.check_in_date} to {self.check_out_date}"