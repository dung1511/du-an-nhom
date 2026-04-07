"""
Unit tests for rooms app models - SIMPLIFIED VERSION matching actual models.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from rooms.models import Room, RoomCategory, Coupon, Reservation, Service

from .factories import (
    RoomFactory,
    RoomCategoryFactory,
    CouponFactory,
    ReservationFactory,
    UserFactory,
    ServiceFactory,
)


@pytest.mark.django_db
def test_room_category_creation():
    """Test creating a room category."""
    category = RoomCategoryFactory(name="Suite")
    assert category.name == "Suite"
    assert str(category) == "Suite"


@pytest.mark.django_db
def test_room_creation():
    """Test creating a room."""
    room = RoomFactory(name="Ocean View", price=Decimal("250.00"))
    assert room.name == "Ocean View"
    assert room.price == Decimal("250.00")
    assert room.size == "D"
    assert str(room) == "Ocean View"


@pytest.mark.django_db
def test_room_capacity():
    """Test room capacity."""
    room = RoomFactory(capacity=6, capacity_adults=4, capacity_children=2)
    assert room.capacity == 6
    assert room.capacity_adults == 4
    assert room.capacity_children == 2


@pytest.mark.django_db
def test_room_size_choices():
    """Test room size options."""
    room_s = RoomFactory(size="S")
    room_d = RoomFactory(size="D")
    room_t = RoomFactory(size="T")
    
    assert room_s.size == "S"
    assert room_d.size == "D"
    assert room_t.size == "T"


@pytest.mark.django_db
def test_room_availability():
    """Test room availability check."""
    room = RoomFactory()
    check_in = date.today() + timedelta(days=5)
    check_out = date.today() + timedelta(days=7)
    
    # Room should be available
    assert room.is_available(check_in, check_out) == True


@pytest.mark.django_db
def test_coupon_creation():
    """Test creating a coupon."""
    coupon = CouponFactory(code="SAVE2024", discount_percentage=Decimal("15.00"))
    assert coupon.code == "SAVE2024"
    assert coupon.discount_percentage == Decimal("15.00")
    assert coupon.active == True
    assert str(coupon) == "SAVE2024"


@pytest.mark.django_db
def test_coupon_inactive():
    """Test inactive coupon."""
    coupon = CouponFactory(active=False)
    assert coupon.active == False


@pytest.mark.django_db
def test_coupon_validity_dates():
    """Test coupon validity dates."""
    from_date =date.today()
    to_date = date.today() + timedelta(days=30)
    coupon = CouponFactory(valid_from=from_date, valid_to=to_date)
    
    assert coupon.valid_from == from_date
    assert coupon.valid_to == to_date


@pytest.mark.django_db
def test_service_creation():
    """Test creating a service."""
    service = ServiceFactory(name="Airport Shuttle", price=Decimal("30.00"))
    assert service.name == "Airport Shuttle"
    assert service.price == Decimal("30.00")
    assert service.active == True
    assert str(service) == "Airport Shuttle"


@pytest.mark.django_db
def test_service_slug_auto_generation():
    """Test service slug auto-generation."""
    service = ServiceFactory(name="Spa Service")
    # Slug should be generated from name
    assert service.slug is not None


@pytest.mark.django_db
def test_reservation_creation():
    """Test creating a reservation."""
    user = UserFactory()
    room = RoomFactory()
    
    res = ReservationFactory(user=user, room=room)
    assert res.user == user
    assert res.room == room
    assert res.is_checked_out == False


@pytest.mark.django_db
def test_reservation_dates():
    """Test reservation dates."""
    check_in = date.today() + timedelta(days=5)
    check_out = date.today() + timedelta(days=7)
    
    res = ReservationFactory(check_in_date=check_in, check_out_date=check_out)
    assert res.check_in_date == check_in
    assert res.check_out_date == check_out


@pytest.mark.django_db
def test_reservation_guest_info():
    """Test reservation guest information."""
    res = ReservationFactory(
        first_name="Nguyễn",
        last_name="Văn A",
        email="test@example.com",
        phone="0123456789"
    )
    assert res.first_name == "Nguyễn"
    assert res.last_name == "Văn A"
    assert res.email == "test@example.com"
    assert res.phone == "0123456789"


@pytest.mark.django_db
def test_reservation_payment_info():
    """Test reservation payment information."""
    res = ReservationFactory(
        subtotal=Decimal("300.00"),
        gst=Decimal("54.00"),
        total=Decimal("354.00"),
        payment_method="cards"
    )
    assert res.subtotal == Decimal("300.00")
    assert res.gst == Decimal("54.00")
    assert res.total == Decimal("354.00")
    assert res.payment_method == "cards"
    assert res.payment_status == "pending"


@pytest.mark.django_db
def test_reservation_checkout():
    """Test reservation checkout status."""
    res = ReservationFactory(is_checked_out=False)
    assert res.is_checked_out == False
    
    # Simulate checkout
    res.is_checked_out = True
    assert res.is_checked_out == True


@pytest.mark.django_db
def test_room_queryset():
    """Test querying rooms."""
    RoomFactory.create_batch(5)
    rooms = Room.objects.all()
    assert rooms.count() >= 5


@pytest.mark.django_db
def test_reservation_queryset_by_user():
    """Test querying reservations by user."""
    user1 = UserFactory()
    user2 = UserFactory()
    
    ReservationFactory.create_batch(3, user=user1)
    ReservationFactory.create_batch(2, user=user2)
    
    user1_res = Reservation.objects.filter(user=user1)
    user2_res = Reservation.objects.filter(user=user2)
    
    assert user1_res.count() == 3
    assert user2_res.count() == 2


@pytest.mark.django_db
def test_active_coupons():
    """Test querying active coupons."""
    CouponFactory.create_batch(3, active=True)
    CouponFactory.create_batch(2, active=False)
    
    active = Coupon.objects.filter(active=True)
    assert active.count() >= 3


@pytest.mark.django_db
def test_room_search_suitable():
    """Test room search functionality."""
    check_in = date.today() + timedelta(days=1)
    check_out = date.today() + timedelta(days=3)
    
    room = RoomFactory(capacity=4, capacity_adults=2, capacity_children=2)
    
    # Search for suitable rooms
    suitable = Room.objects.search_suitable_rooms(check_in, check_out, adults=2, children=0)
    assert room in suitable


@pytest.mark.django_db
def test_reservation_string_repr():
    """Test reservation string representation."""
    room = RoomFactory(name="Suite 101")
    res = ReservationFactory(room=room)
    
    str_repr = str(res)
    assert "Suite 101" in str_repr
