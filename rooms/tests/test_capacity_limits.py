import pytest
from datetime import date, timedelta

from rooms.serializers import ReservationCreateSerializer
from .factories import RoomFactory


@pytest.mark.django_db
def test_room_can_accommodate_respects_all_capacity_dimensions():
    room = RoomFactory(capacity=10, capacity_adults=2, capacity_children=1, total_capacity=3)

    assert room.can_accommodate(adults=2, children=1)
    assert not room.can_accommodate(adults=3, children=0)
    assert not room.can_accommodate(adults=2, children=2)
    assert not room.can_accommodate(adults=1, children=3)


@pytest.mark.django_db
def test_reservation_create_serializer_rejects_guest_count_over_room_limit():
    room = RoomFactory(capacity=10, capacity_adults=2, capacity_children=1, total_capacity=3)
    payload = {
        "room_id": room.id,
        "check_in_date": date.today() + timedelta(days=1),
        "check_out_date": date.today() + timedelta(days=2),
        "adults": 3,
        "children": 0,
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "phone": "0123456789",
        "address": "123 Test Street",
        "city": "Ha Noi",
    }

    serializer = ReservationCreateSerializer(data=payload)

    assert not serializer.is_valid()
    error_text = str(serializer.errors)
    assert "chi cho toi da" in error_text
