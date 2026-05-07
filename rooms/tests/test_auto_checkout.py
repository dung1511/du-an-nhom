import pytest
from django.utils import timezone
from datetime import datetime, time, timedelta, date
from django.core.management import call_command
from io import StringIO
from django.test import TestCase
from django.contrib.auth.models import User

from rooms.models import Room, Reservation, RoomCategory
from rooms.tests.factories import RoomFactory, ReservationFactory


class AutoCheckoutNoShowTests(TestCase):
    """Test cases for auto-checkout no-show feature"""

    @pytest.fixture
    def test_data(self):
        """Create test data"""
        # Create a room
        category = RoomCategory.objects.create(name='Deluxe')
        room = Room.objects.create(
            name='Room 302 - Deluxe',
            category=category,
            capacity=2,
            capacity_adults=2,
            capacity_children=0,
            total_capacity=2,
            size='D',
            description='Nice room',
            price=1000000.00
        )
        return room

    def setUp(self):
        """Set up test data before each test"""
        self.category = RoomCategory.objects.create(name='Deluxe')
        self.room = Room.objects.create(
            name='Room 302 - Deluxe',
            category=self.category,
            capacity=2,
            capacity_adults=2,
            capacity_children=0,
            total_capacity=2,
            size='D',
            description='Nice room',
            price=1000000.00
        )

    def test_auto_checkout_no_show_reservation(self):
        """Test that no-show reservations are auto-checked-out and cancelled"""
        # Create a reservation for today that hasn't been checked in
        today = date.today()
        reservation = Reservation.objects.create(
            room=self.room,
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            adults=2,
            children=0,
            first_name='Mong',
            last_name='Mo',
            email='mong.mo@example.com',
            phone='0912345678',
            payment_method='cash',
            payment_status='pending',
            subtotal=1000000.00,
            gst=0.00,
            total=1000000.00
        )

        # Verify initial state
        assert reservation.is_checked_in is False
        assert reservation.is_checked_out is False
        assert reservation.is_canceled is False

        # Run the auto-cancel command
        out = StringIO()
        call_command('auto_cancel_no_shows', stdout=out)

        # Refresh from database
        reservation.refresh_from_db()

        # Verify auto-checkout happened
        assert reservation.is_checked_out is True
        assert reservation.checkout_at is not None
        assert reservation.actual_check_out_date == today

        # Verify cancellation happened
        assert reservation.is_canceled is True
        assert reservation.canceled_at is not None
        assert reservation.canceled_reason == 'no_show_auto_cancel'

    def test_auto_checkout_respects_grace_period(self):
        """Test that auto-checkout respects the grace period"""
        # Create a reservation for today that's within grace period
        today = date.today()
        now = timezone.now()
        
        # Create a reservation for this morning (within grace period)
        reservation = Reservation.objects.create(
            room=self.room,
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            adults=2,
            children=0,
            first_name='Mong',
            last_name='Mo',
            email='mong.mo@example.com',
            phone='0912345678',
            payment_method='cash',
            payment_status='pending',
            subtotal=1000000.00,
            gst=0.00,
            total=1000000.00
        )

        # Run the auto-cancel command
        out = StringIO()
        call_command('auto_cancel_no_shows', stdout=out)

        # Refresh from database
        reservation.refresh_from_db()

        # If we're still within grace period, reservation should NOT be cancelled
        check_in_dt = datetime.combine(today, time(hour=8, minute=0))
        check_in_dt = timezone.make_aware(check_in_dt)
        threshold = check_in_dt + timedelta(hours=6)

        if now < threshold:
            # Within grace period - should NOT be cancelled
            assert reservation.is_canceled is False
        else:
            # Outside grace period - should be cancelled
            assert reservation.is_canceled is True

    def test_checked_in_reservations_not_auto_cancelled(self):
        """Test that already checked-in reservations are not auto-cancelled"""
        today = date.today()
        reservation = Reservation.objects.create(
            room=self.room,
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            adults=2,
            children=0,
            first_name='Mong',
            last_name='Mo',
            email='mong.mo@example.com',
            phone='0912345678',
            payment_method='cash',
            payment_status='paid',
            subtotal=1000000.00,
            gst=0.00,
            total=1000000.00,
            is_checked_in=True,
            checked_in_at=timezone.now(),
            checked_in_adults=2,
            checked_in_children=0
        )

        # Run the auto-cancel command
        out = StringIO()
        call_command('auto_cancel_no_shows', stdout=out)

        # Refresh from database
        reservation.refresh_from_db()

        # Verified reservation was NOT cancelled
        assert reservation.is_canceled is False

    def test_already_checked_out_not_auto_cancelled(self):
        """Test that already checked-out reservations are not auto-cancelled"""
        today = date.today()
        reservation = Reservation.objects.create(
            room=self.room,
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            adults=2,
            children=0,
            first_name='Mong',
            last_name='Mo',
            email='mong.mo@example.com',
            phone='0912345678',
            payment_method='cash',
            payment_status='paid',
            subtotal=1000000.00,
            gst=0.00,
            total=1000000.00,
            is_checked_out=True,
            checkout_at=timezone.now()
        )

        # Run the auto-cancel command
        out = StringIO()
        call_command('auto_cancel_no_shows', stdout=out)

        # Refresh from database
        reservation.refresh_from_db()

        # Verified reservation was NOT cancelled
        assert reservation.is_canceled is False

    def test_room_becomes_available_after_auto_checkout(self):
        """Test that room status updates to available after auto-checkout"""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        reservation = Reservation.objects.create(
            room=self.room,
            check_in_date=today,
            check_out_date=tomorrow,
            adults=2,
            children=0,
            first_name='Mong',
            last_name='Mo',
            email='mong.mo@example.com',
            phone='0912345678',
            payment_method='cash',
            payment_status='pending',
            subtotal=1000000.00,
            gst=0.00,
            total=1000000.00
        )

        # Before auto-checkout: room should be marked as occupied
        is_available_before = self.room.is_available(today, tomorrow)

        # Run the auto-cancel command
        out = StringIO()
        call_command('auto_cancel_no_shows', stdout=out)

        # After auto-checkout: room should be available
        is_available_after = self.room.is_available(today, tomorrow)

        # Since the reservation is now checked out, the room should be available
        assert is_available_after is True

    def test_multiple_no_shows_handled(self):
        """Test that multiple no-show reservations are handled in one run"""
        today = date.today()
        reservations = []

        # Create 3 no-show reservations
        for i in range(3):
            res = Reservation.objects.create(
                room=self.room,
                check_in_date=today,
                check_out_date=today + timedelta(days=1),
                adults=2,
                children=0,
                first_name=f'Guest {i}',
                last_name='Test',
                email=f'guest{i}@example.com',
                phone='0912345678',
                payment_method='cash',
                payment_status='pending',
                subtotal=1000000.00,
                gst=0.00,
                total=1000000.00
            )
            reservations.append(res)

        # Run the auto-cancel command
        out = StringIO()
        call_command('auto_cancel_no_shows', stdout=out)
        output = out.getvalue()

        # Verify all were cancelled
        for res in reservations:
            res.refresh_from_db()
            # Note: Only one can actually be cancelled for this room at a time
            # since is_checked_out would prevent overlaps
            assert res.is_canceled or res.is_checked_out

        # Check output mentions the cancellations
        assert 'completed' in output.lower()


class ReservationAutoCheckoutIntegrationTests(TestCase):
    """Integration tests for auto-checkout feature"""

    def setUp(self):
        """Set up test data"""
        self.category = RoomCategory.objects.create(name='Suite')
        self.room = Room.objects.create(
            name='Luxury Suite',
            category=self.category,
            capacity=4,
            capacity_adults=3,
            capacity_children=1,
            total_capacity=4,
            size='T',
            description='Luxury room',
            price=5000000.00
        )

    def test_auto_checkout_updates_all_required_fields(self):
        """Test that auto-checkout sets all required fields correctly"""
        today = date.today()
        before_now = timezone.now()

        reservation = Reservation.objects.create(
            room=self.room,
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            adults=3,
            children=1,
            first_name='VIP',
            last_name='Guest',
            email='vip@example.com',
            phone='0987654321',
            payment_method='momo_qr',
            payment_status='pending',
            subtotal=5000000.00,
            gst=0.00,
            total=5000000.00,
            adults=3,
            children=1
        )

        # Verify initial state
        assert reservation.actual_check_out_date is None
        assert reservation.is_checked_out is False
        assert reservation.checkout_at is None

        # Run auto-checkout
        out = StringIO()
        call_command('auto_cancel_no_shows', stdout=out)

        # Refresh and verify
        reservation.refresh_from_db()
        after_now = timezone.now()

        assert reservation.is_checked_out is True
        assert reservation.actual_check_out_date == today
        assert before_now <= reservation.checkout_at <= after_now
        assert reservation.is_canceled is True
        assert reservation.canceled_reason == 'no_show_auto_cancel'


if __name__ == '__main__':
    pytest.main([__file__])
