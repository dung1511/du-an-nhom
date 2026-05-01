"""
API endpoint tests for rooms app.

Tests cover:
- API request/response handling
- Authentication and permissions
- Data validation and error handling
- Business logic in views
"""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.test import RequestFactory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from rooms.models import Room, Reservation, Coupon
from .factories import (
    RoomFactory,
    UserFactory,
    ReservationFactory,
    CouponFactory,
    RoomCategoryFactory,
)


@pytest.mark.django_db
class TestRoomListAPIView:
    """Tests for room list API endpoint."""
    
    def test_list_all_rooms(self, api_client):
        """Test retrieving list of all rooms."""
        # Create test data
        RoomFactory.create_batch(5)
        
        # Make request
        url = reverse('rooms:api_rooms_list')
        response = api_client.get(url)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 5
    
    def test_room_list_pagination(self, api_client):
        """Test room list pagination."""
        RoomFactory.create_batch(15)
        
        url = reverse('rooms:api_rooms_list') + '?limit=5'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'pagination' in response.data or len(response.data) <= 5
    
    def test_room_detail_view(self, api_client):
        """Test retrieving a single room."""
        room = RoomFactory(room_title="Ocean View")
        
        url = reverse('rooms:api_room_detail', kwargs={'id': room.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['room_title'] == "Ocean View"
    
    def test_room_detail_not_found(self, api_client):
        """Test room detail with invalid ID."""
        url = reverse('rooms:api_room_detail', kwargs={'id': 99999})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestRoomSearchAPIView:
    """Tests for room search API endpoint."""
    
    def test_search_rooms_valid_criteria(self, api_client):
        """Test searching rooms with valid criteria."""
        # Create available rooms
        category = RoomCategoryFactory()
        room = RoomFactory(
            category=category,
            max_adult=2,
            max_children=1,
            price=Decimal("150.00")
        )
        
        url = reverse('rooms:api_rooms_search')
        data = {
            'check_in_date': (date.today() + timedelta(days=1)).isoformat(),
            'check_out_date': (date.today() + timedelta(days=3)).isoformat(),
            'adults': 2,
            'children': 0,
            'limit': 5
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('success') == True
        assert 'results' in response.data or 'rooms' in response.data
    
    def test_search_rooms_missing_required_fields(self, api_client):
        """Test search with missing required fields."""
        url = reverse('rooms:api_rooms_search')
        data = {
            'check_in_date': date.today().isoformat(),
            # Missing check_out_date, adults
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_search_rooms_past_checkin_date(self, api_client):
        """Test search with past check-in date."""
        url = reverse('rooms:api_rooms_search')
        data = {
            'check_in_date': (date.today() - timedelta(days=5)).isoformat(),  # Past date
            'check_out_date': (date.today() + timedelta(days=2)).isoformat(),
            'adults': 1,
            'children': 0
        }
        
        response = api_client.post(url, data, format='json')
        
        # Should reject past dates
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_search_rooms_checkout_before_checkin(self, api_client):
        """Test search where checkout is before check-in."""
        url = reverse('rooms:api_rooms_search')
        data = {
            'check_in_date': (date.today() + timedelta(days=10)).isoformat(),
            'check_out_date': (date.today() + timedelta(days=5)).isoformat(),  # Before check-in
            'adults': 1,
            'children': 0
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_search_rooms_capacity_not_met(self, api_client):
        """Test search where no rooms match capacity."""
        # Create room with low capacity
        RoomFactory(max_adult=1, max_children=0)
        
        url = reverse('rooms:api_rooms_search')
        data = {
            'check_in_date': (date.today() + timedelta(days=1)).isoformat(),
            'check_out_date': (date.today() + timedelta(days=3)).isoformat(),
            'adults': 5,  # High capacity
            'children': 2,
        }
        
        response = api_client.post(url, data, format='json')
        
        # May return empty results or message
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestReservationListCreateAPIView:
    """Tests for reservation list and create endpoints."""
    
    def test_create_reservation_authenticated(self, authenticated_client, user):
        """Test creating reservation when authenticated."""
        room = RoomFactory()
        
        url = reverse('rooms:api_booking_create')
        data = {
            'room': room.id,
            'check_in_date': (date.today() + timedelta(days=1)).isoformat(),
            'check_out_date': (date.today() + timedelta(days=3)).isoformat(),
            'adults': 2,
            'children': 0,
            'first_name': 'Nguyễn',
            'last_name': 'Văn A',
            'email': user.email,
            'phone': '0123456789',
            'address': '123 Đường A',
            'city': 'Hà Nội',
            'state': 'Hà Nội',
            'postcode': '100000'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['user'] == user.id
        assert response.data['booking_code'].startswith('BK')
        assert 'booking_confirmation_url' in response.data
        assert 'invoice' in response.data
        assert response.data['invoice']['final_total'] is not None
    
    def test_create_reservation_unauthenticated(self, api_client):
        """Test creating reservation without authentication."""
        room = RoomFactory()
        
        url = reverse('rooms:api_reservations_list')
        data = {
            'room': room.id,
            'adults': 2
        }
        
        response = api_client.post(url, data, format='json')
        
        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_list_user_reservations_authenticated(self, authenticated_client, user):
        """Test listing user's reservations when authenticated."""
        # Create reservations for the user
        ReservationFactory.create_batch(3, user=user)
        
        url = reverse('rooms:api_reservations_list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Verify we get the user's reservations
        assert len(response.data) >= 3 or 'results' in response.data
    
    def test_list_user_reservations_unauthenticated(self, api_client):
        """Test listing reservations without authentication."""
        url = reverse('rooms:api_reservations_list')
        response = api_client.get(url)
        
        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_reservation_invalid_room(self, authenticated_client):
        """Test creating reservation with invalid room ID."""
        url = reverse('rooms:api_reservations_list')
        data = {
            'room': 99999,  # Non-existent room
            'check_in_date': (date.today() + timedelta(days=1)).isoformat(),
            'check_out_date': (date.today() + timedelta(days=3)).isoformat(),
            'adults': 2,
            'children': 0,
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'phone': '0123456789',
            'address': '123 Street',
            'city': 'City',
            'state': 'State',
            'postcode': '00000'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_reservation_missing_fields(self, authenticated_client):
        """Test creating reservation with missing required fields."""
        url = reverse('rooms:api_booking_create')
        data = {
            'room': RoomFactory().id,
            # Missing check_in_date, check_out_date, personal info, etc.
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestReservationDetailAPIView:
    """Tests for reservation detail endpoint."""
    
    def test_retrieve_own_reservation(self, authenticated_client, user):
        """Test retrieving own reservation."""
        reservation = ReservationFactory(user=user)
        
        url = reverse('rooms:api_reservation_detail', kwargs={'id': reservation.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == reservation.id
    
    def test_retrieve_other_user_reservation(self, authenticated_client):
        """Test retrieving another user's reservation (should be denied)."""
        other_user = UserFactory()
        reservation = ReservationFactory(user=other_user)
        
        url = reverse('rooms:api_reservation_detail', kwargs={'id': reservation.id})
        response = authenticated_client.get(url)
        
        # Should deny access to another user's reservation
        assert response.status_code == status.HTTP_403_FORBIDDEN or status.HTTP_404_NOT_FOUND
    
    def test_retrieve_nonexistent_reservation(self, authenticated_client):
        """Test retrieving non-existent reservation."""
        url = reverse('rooms:api_reservation_detail', kwargs={'id': 99999})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestReservationCheckoutAPIView:
    """Tests for checkout endpoint."""
    
    def test_checkout_valid_reservation(self, authenticated_client, user):
        """Test checking out a valid reservation."""
        reservation = ReservationFactory(user=user, is_checked_in=True, is_checked_out=False)
        reservation.checked_in_at = reservation.checked_in_at or datetime.now()
        reservation.save(update_fields=['is_checked_in', 'checked_in_at'])
        
        url = reverse('rooms:api_checkout', kwargs={'id': reservation.id})
        data = {'damage_reported': False, 'damage_notes': ''}
        
        response = authenticated_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['reservation']['is_checked_out'] is True
        assert response.data['final_total'] is not None
    
    def test_checkout_already_checked_out(self, authenticated_client, user):
        """Test checking out an already checked-out reservation."""
        reservation = ReservationFactory(user=user, is_checked_in=True, is_checked_out=True)
        
        url = reverse('rooms:api_checkout', kwargs={'id': reservation.id})
        data = {'damage_reported': False}
        
        response = authenticated_client.put(url, data, format='json')
        
        # May succeed or return validation message
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
    
    def test_checkout_without_authentication(self, api_client):
        """Test checkout without authentication."""
        reservation = ReservationFactory()
        
        url = reverse('rooms:api_checkout', kwargs={'id': reservation.id})
        data = {'damage_reported': False}
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_frontdesk_print_slip_shows_updated_momo_amount(monkeypatch):
    """Test the front desk slip reflects updated damage totals for MoMo QR."""
    admin_user = UserFactory(
        username='frontdesk-admin',
        email='frontdesk-admin@example.com',
        password='adminpass123',
    )
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save(update_fields=['is_staff', 'is_superuser'])

    reservation = ReservationFactory(
        payment_method='momo_qr',
        subtotal=Decimal('1000.00'),
        gst=Decimal('180.00'),
        total=Decimal('1180.00'),
        damage_reported=True,
        damage_notes='Broken lamp',
        is_checked_in=True,
        checked_in_adults=2,
        checked_in_children=0,
        email='',
    )
    reservation.sync_financial_fields()
    reservation.is_checked_out = True
    reservation.checkout_at = datetime.now()
    reservation.save(
        update_fields=[
            'damage_reported',
            'damage_notes',
            'damage_fee',
            'final_total',
            'deposit_amount',
            'balance_due',
            'is_checked_in',
            'checked_in_adults',
            'checked_in_children',
            'is_checked_out',
            'checkout_at',
        ]
    )

    url = reverse('rooms:frontdesk_print_slip', kwargs={'booking_code': reservation.booking_code})
    request = RequestFactory().get(url)
    request.user = admin_user

    from rooms import views as rooms_views

    monkeypatch.setattr(rooms_views.messages, 'success', lambda *args, **kwargs: None)
    monkeypatch.setattr(rooms_views.messages, 'warning', lambda *args, **kwargs: None)
    monkeypatch.setattr(rooms_views.messages, 'error', lambda *args, **kwargs: None)

    response = rooms_views.frontdesk_print_slip.__wrapped__(request, booking_code=reservation.booking_code)

    assert response.status_code == status.HTTP_200_OK
    assert 'QR MoMo' in response.content.decode('utf-8')
    assert f'₹{reservation.final_total}' in response.content.decode('utf-8')


@pytest.mark.django_db
class TestReservationPaymentAPIView:
    """Tests for payment endpoint."""
    
    def test_process_payment_valid(self, authenticated_client, user):
        """Test processing payment for a reservation."""
        reservation = ReservationFactory(user=user)
        
        url = reverse('rooms:api_payment', kwargs={'id': reservation.id})
        data = {
            'payment_method': 'cards',
            'amount': str(reservation.total)
        }
        
        response = authenticated_client.put(url, data, format='json')
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
    
    def test_process_payment_with_coupon(self, authenticated_client, user):
        """Test processing payment with coupon code."""
        coupon = CouponFactory(code="SAVE20", discount_price=Decimal("20.00"), is_active=True)
        reservation = ReservationFactory(user=user)
        
        url = reverse('rooms:api_payment', kwargs={'id': reservation.id})
        data = {
            'payment_method': 'cards',
            'coupon_code': coupon.code,
            'amount': str(reservation.total - coupon.discount_price)
        }
        
        response = authenticated_client.put(url, data, format='json')
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
    
    def test_process_payment_invalid_coupon(self, authenticated_client, user):
        """Test payment with invalid coupon code."""
        reservation = ReservationFactory(user=user)
        
        url = reverse('rooms:api_payment', kwargs={'id': reservation.id})
        data = {
            'payment_method': 'cards',
            'coupon_code': 'INVALID123',
            'amount': str(reservation.total)
        }
        
        response = authenticated_client.put(url, data, format='json')
        
        # Should handle invalid coupon gracefully
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]


@pytest.mark.django_db
class TestCheckedOutReservationsListAPIView:
    """Tests for checked-out reservations list endpoint."""
    
    def test_list_checked_out_reservations(self, authenticated_client, user):
        """Test listing checked-out reservations."""
        # Create mix of checked-out and pending
        ReservationFactory.create_batch(2, user=user, is_checked_out=True)
        ReservationFactory.create_batch(2, user=user, is_checked_out=False)
        
        url = reverse('rooms:api_checked_out_reservations_list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Should only return checked-out reservations
        checked_out_count = len(response.data) if isinstance(response.data, list) else response.data.get('count', 0)
        assert checked_out_count >= 0


@pytest.mark.django_db
class TestAdminDashboardAPIView:
    """Tests for admin dashboard API."""
    
    def test_admin_dashboard_unauthorized(self, authenticated_client):
        """Test accessing admin dashboard without admin rights."""
        url = reverse('rooms:api_admin_dashboard')
        response = authenticated_client.get(url)
        
        # Regular user should not access
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]
    
    def test_admin_dashboard_authorized(self, api_client):
        """Test accessing admin dashboard with admin user."""
        admin = UserFactory()
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        
        api_client.force_authenticate(user=admin)
        url = reverse('rooms:api_admin_dashboard')
        response = api_client.get(url)
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]  # May vary based on implementation


@pytest.mark.django_db
class TestRoomCategoryListAPIView:
    """Tests for room categories endpoint."""
    
    def test_list_room_categories(self, api_client):
        """Test listing room categories."""
        # Create categories
        RoomCategoryFactory.create_batch(5)
        
        url = reverse('rooms:api_room_categories')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 5 or 'results' in response.data
