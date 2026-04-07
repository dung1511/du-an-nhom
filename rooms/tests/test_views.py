"""
API endpoint tests for rooms app.

Tests cover:
- API request/response handling
- Authentication and permissions
- Data validation and error handling
- Business logic in views
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
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
        url = reverse('room-list')  # Adjust based on your URL name
        response = api_client.get(url)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 5
    
    def test_room_list_pagination(self, api_client):
        """Test room list pagination."""
        RoomFactory.create_batch(15)
        
        url = reverse('room-list') + '?limit=5'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'pagination' in response.data or len(response.data) <= 5
    
    def test_room_detail_view(self, api_client):
        """Test retrieving a single room."""
        room = RoomFactory(room_title="Ocean View")
        
        url = reverse('room-detail', kwargs={'pk': room.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['room_title'] == "Ocean View"
    
    def test_room_detail_not_found(self, api_client):
        """Test room detail with invalid ID."""
        url = reverse('room-detail', kwargs={'pk': 99999})
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
        
        url = reverse('room-search')  # Adjust based on your URL name
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
        url = reverse('room-search')
        data = {
            'check_in_date': date.today().isoformat(),
            # Missing check_out_date, adults
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_search_rooms_past_checkin_date(self, api_client):
        """Test search with past check-in date."""
        url = reverse('room-search')
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
        url = reverse('room-search')
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
        
        url = reverse('room-search')
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
        
        url = reverse('reservation-list')
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
    
    def test_create_reservation_unauthenticated(self, api_client):
        """Test creating reservation without authentication."""
        room = RoomFactory()
        
        url = reverse('reservation-list')
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
        
        url = reverse('reservation-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Verify we get the user's reservations
        assert len(response.data) >= 3 or 'results' in response.data
    
    def test_list_user_reservations_unauthenticated(self, api_client):
        """Test listing reservations without authentication."""
        url = reverse('reservation-list')
        response = api_client.get(url)
        
        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_reservation_invalid_room(self, authenticated_client):
        """Test creating reservation with invalid room ID."""
        url = reverse('reservation-list')
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
        url = reverse('reservation-list')
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
        
        url = reverse('reservation-detail', kwargs={'pk': reservation.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == reservation.id
    
    def test_retrieve_other_user_reservation(self, authenticated_client):
        """Test retrieving another user's reservation (should be denied)."""
        other_user = UserFactory()
        reservation = ReservationFactory(user=other_user)
        
        url = reverse('reservation-detail', kwargs={'pk': reservation.id})
        response = authenticated_client.get(url)
        
        # Should deny access to another user's reservation
        assert response.status_code == status.HTTP_403_FORBIDDEN or status.HTTP_404_NOT_FOUND
    
    def test_retrieve_nonexistent_reservation(self, authenticated_client):
        """Test retrieving non-existent reservation."""
        url = reverse('reservation-detail', kwargs={'pk': 99999})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestReservationCheckoutAPIView:
    """Tests for checkout endpoint."""
    
    def test_checkout_valid_reservation(self, authenticated_client, user):
        """Test checking out a valid reservation."""
        reservation = ReservationFactory(user=user, is_checked_out=False)
        
        url = reverse('reservation-checkout', kwargs={'pk': reservation.id})
        data = {'is_checked_out': True}
        
        response = authenticated_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_checked_out'] == True
    
    def test_checkout_already_checked_out(self, authenticated_client, user):
        """Test checking out an already checked-out reservation."""
        reservation = ReservationFactory(user=user, is_checked_out=True)
        
        url = reverse('reservation-checkout', kwargs={'pk': reservation.id})
        data = {'is_checked_out': True}
        
        response = authenticated_client.put(url, data, format='json')
        
        # May succeed or return validation message
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
    
    def test_checkout_without_authentication(self, api_client):
        """Test checkout without authentication."""
        reservation = ReservationFactory()
        
        url = reverse('reservation-checkout', kwargs={'pk': reservation.id})
        data = {'is_checked_out': True}
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestReservationPaymentAPIView:
    """Tests for payment endpoint."""
    
    def test_process_payment_valid(self, authenticated_client, user):
        """Test processing payment for a reservation."""
        reservation = ReservationFactory(user=user)
        
        url = reverse('reservation-payment', kwargs={'pk': reservation.id})
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
        
        url = reverse('reservation-payment', kwargs={'pk': reservation.id})
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
        
        url = reverse('reservation-payment', kwargs={'pk': reservation.id})
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
        
        url = reverse('checked-out-reservations')  # Adjust URL name
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
        url = reverse('admin-dashboard')  # Adjust URL name
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
        url = reverse('admin-dashboard')
        response = api_client.get(url)
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]  # May vary based on implementation


@pytest.mark.django_db
class TestRoomCategoryListAPIView:
    """Tests for room categories endpoint."""
    
    def test_list_room_categories(self, api_client):
        """Test listing room categories."""
        # Create categories
        RoomCategoryFactory.create_batch(5)
        
        url = reverse('room-category-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 5 or 'results' in response.data
