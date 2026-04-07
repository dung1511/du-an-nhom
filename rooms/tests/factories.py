"""
Factory classes for generating test data.

Factories provide a convenient way to create test objects with sensible defaults.
They're preferable to fixtures for complex objects and can be customized per test.

Example:
    room = RoomFactory(name="Suite", price=200.00)
    user = UserFactory(username="testuser")
"""
import factory
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from rooms.models import Room, RoomCategory, Coupon, Reservation, Service


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating test User objects."""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = "Test"
    last_name = "User"
    
    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Set the password after user creation."""
        if extracted:
            obj.set_password(extracted)
        else:
            obj.set_password("testpass123")
        if create:
            obj.save()


class RoomCategoryFactory(factory.django.DjangoModelFactory):
    """Factory for creating test RoomCategory objects."""
    
    class Meta:
        model = RoomCategory
    
    name = factory.Sequence(lambda n: f"Category {n}")


class RoomFactory(factory.django.DjangoModelFactory):
    """Factory for creating test Room objects."""
    
    class Meta:
        model = Room
    
    name = factory.Sequence(lambda n: f"Room {n}")
    category = factory.SubFactory(RoomCategoryFactory)
    description = "Beautiful test room"
    price = Decimal("150.00")
    capacity = 4
    capacity_adults = 2
    capacity_children = 2
    total_capacity = 4
    size = "D"


class CouponFactory(factory.django.DjangoModelFactory):
    """Factory for creating test Coupon objects."""
    
    class Meta:
        model = Coupon
    
    code = factory.Sequence(lambda n: f"COUPON{n:03d}")
    discount_percentage = Decimal("15.00")
    active = True
    valid_from = factory.LazyFunction(date.today)
    valid_to = factory.LazyFunction(lambda: date.today() + timedelta(days=365))


class ServiceFactory(factory.django.DjangoModelFactory):
    """Factory for creating test Service objects."""
    
    class Meta:
        model = Service
    
    name = factory.Sequence(lambda n: f"Service {n}")
    slug = factory.Sequence(lambda n: f"service-{n}")
    description = "Test service"
    price = Decimal("50.00")
    image_url = "https://example.com/service.jpg"
    active = True
    order = 0


class ReservationFactory(factory.django.DjangoModelFactory):
    """Factory for creating test Reservation objects."""
    
    class Meta:
        model = Reservation
    
    user = factory.SubFactory(UserFactory)
    room = factory.SubFactory(RoomFactory)
    
    # Dates: check-in tomorrow, check-out in 3 days
    check_in_date = factory.LazyFunction(lambda: date.today() + timedelta(days=1))
    check_out_date = factory.LazyFunction(lambda: date.today() + timedelta(days=3))
    
    adults = 2
    children = 0
    
    # Guest information
    first_name = "Nguyễn"
    last_name = "Văn A"
    email = "nguyenvana@example.com"
    phone = "0123456789"
    address = "123 Đường A"
    city = "Hà Nội"
    state = "Hà Nội"
    postcode = "100000"
    
    # Payment information
    subtotal = Decimal("300.00")
    gst = Decimal("54.00")
    discount_applied = Decimal("0.00")
    total = Decimal("354.00")
    
    payment_method = "cards"
    payment_status = "pending"
    is_checked_out = False
    service_total = Decimal("0.00")
