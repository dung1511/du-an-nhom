"""
Pytest configuration and fixtures for rooms app tests.
"""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from .factories import UserFactory, RoomFactory, ReservationFactory


@pytest.fixture
def api_client():
    """
    Fixture to provide an API client for making requests.
    
    Usage:
        def test_api(api_client):
            response = api_client.get('/rooms/api/rooms/')
    """
    return APIClient()


@pytest.fixture
def user(db):
    """
    Fixture to create a test user in the database.
    
    Usage:
        def test_user(user):
            assert user.username == 'testuser'
    """
    return UserFactory(
        username='testuser',
        email='testuser@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """
    Fixture to provide an API client with authentication.
    
    Usage:
        def test_authenticated_api(authenticated_client):
            response = authenticated_client.get('/rooms/api/reservations/')
    """
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_user(db):
    """
    Fixture to create a superuser admin for testing admin endpoints.
    
    Usage:
        def test_admin_api(authenticated_client, admin_user):
            client = APIClient()
            client.force_authenticate(user=admin_user)
            response = client.get('/rooms/api/admin/dashboard/')
    """
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def room_data():
    """
    Fixture to provide room factory.
    
    Usage:
        def test_room(room_data):
            room = room_data(room_title="Luxury Suite")
            assert room.room_title == "Luxury Suite"
    """
    return RoomFactory


@pytest.fixture
def reservation_data():
    """
    Fixture to provide reservation factory.
    
    Usage:
        def test_reservation(reservation_data, user):
            res = reservation_data(user=user)
            assert res.user == user
    """
    return ReservationFactory
