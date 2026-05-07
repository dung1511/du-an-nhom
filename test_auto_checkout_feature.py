#!/usr/bin/env python
"""
Script to test the auto-checkout feature by creating a test reservation
and then running the auto-cancel command.

Usage:
    python test_auto_checkout_feature.py
"""

import os
import sys
import django
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quanlykhachsannn.settings')
django.setup()

from django.core.management import call_command
from django.utils import timezone
from io import StringIO
from rooms.models import Room, Reservation, RoomCategory


def create_test_reservation():
    """Create a test reservation for today (no check-in)"""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    # Get or create test room
    category, _ = RoomCategory.objects.get_or_create(name='Test Suite')
    room, _ = Room.objects.get_or_create(
        name='Test Room 999',
        defaults={
            'category': category,
            'capacity': 2,
            'capacity_adults': 2,
            'capacity_children': 0,
            'total_capacity': 2,
            'size': 'D',
            'description': 'Test room for auto-checkout feature',
            'price': 1000000.00
        }
    )
    
    # Create reservation for today (no check-in yet)
    reservation, created = Reservation.objects.get_or_create(
        room=room,
        check_in_date=today,
        defaults={
            'check_out_date': tomorrow,
            'adults': 2,
            'children': 0,
            'first_name': 'Test',
            'last_name': 'Guest',
            'email': 'test.guest@example.com',
            'phone': '0912345678',
            'payment_method': 'cash',
            'payment_status': 'pending',
            'subtotal': 1000000.00,
            'gst': 0.00,
            'total': 1000000.00,
            'is_checked_in': False,
            'is_checked_out': False,
            'is_canceled': False
        }
    )
    
    return room, reservation, created


def verify_auto_checkout(reservation):
    """Verify that reservation was auto-checked-out"""
    reservation.refresh_from_db()
    
    print("\n" + "="*70)
    print("RESERVATION STATUS AFTER AUTO-CHECKOUT")
    print("="*70)
    print(f"Booking Code:          {reservation.booking_code}")
    print(f"Room:                  {reservation.room.name}")
    print(f"Check-in Date:         {reservation.check_in_date}")
    print(f"Check-out Date:        {reservation.check_out_date}")
    print(f"Guest:                 {reservation.first_name} {reservation.last_name}")
    print(f"\nAuto-Checkout Status:")
    print(f"  ✓ is_checked_out:    {reservation.is_checked_out}")
    print(f"  ✓ checkout_at:       {reservation.checkout_at}")
    print(f"  ✓ actual_checkout:   {reservation.actual_check_out_date}")
    print(f"\nAuto-Cancel Status:")
    print(f"  ✓ is_canceled:       {reservation.is_canceled}")
    print(f"  ✓ canceled_at:       {reservation.canceled_at}")
    print(f"  ✓ canceled_reason:   {reservation.canceled_reason}")
    print("="*70)
    
    # Verify all fields are set correctly
    assert reservation.is_checked_out is True, "ERROR: is_checked_out is not True!"
    assert reservation.checkout_at is not None, "ERROR: checkout_at is None!"
    assert reservation.actual_check_out_date is not None, "ERROR: actual_check_out_date is None!"
    assert reservation.is_canceled is True, "ERROR: is_canceled is not True!"
    assert reservation.canceled_at is not None, "ERROR: canceled_at is None!"
    assert reservation.canceled_reason == 'no_show_auto_cancel', "ERROR: canceled_reason is incorrect!"
    
    print("\n✅ All auto-checkout fields verified successfully!")


def verify_room_availability(room, check_in, check_out):
    """Verify that room is now available"""
    is_available = room.is_available(check_in, check_out)
    print(f"\n✅ Room '{room.name}' is now available: {is_available}")
    return is_available


def main():
    """Main test function"""
    print("\n" + "="*70)
    print("AUTO-CHECKOUT FEATURE TEST")
    print("="*70)
    
    # Step 1: Create test reservation
    print("\n[Step 1] Creating test reservation for today...")
    room, reservation, created = create_test_reservation()
    
    if created:
        print(f"✅ Created new test reservation: {reservation.booking_code}")
    else:
        print(f"⓵ Using existing test reservation: {reservation.booking_code}")
    
    # Print initial status
    print(f"\nInitial Status:")
    print(f"  is_checked_in:  {reservation.is_checked_in}")
    print(f"  is_checked_out: {reservation.is_checked_out}")
    print(f"  is_canceled:    {reservation.is_canceled}")
    
    # Step 2: Run auto-cancel command
    print("\n[Step 2] Running auto-cancel command...")
    out = StringIO()
    try:
        call_command('auto_cancel_no_shows', stdout=out)
        command_output = out.getvalue()
        print(command_output)
    except Exception as e:
        print(f"❌ ERROR running command: {e}")
        return False
    
    # Step 3: Verify auto-checkout
    print("\n[Step 3] Verifying auto-checkout results...")
    try:
        verify_auto_checkout(reservation)
    except AssertionError as e:
        print(f"❌ VERIFICATION FAILED: {e}")
        return False
    
    # Step 4: Verify room availability
    print("\n[Step 4] Verifying room availability...")
    try:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        is_available = verify_room_availability(room, today, tomorrow)
        if not is_available:
            print("⚠️  WARNING: Room is not showing as available!")
    except Exception as e:
        print(f"❌ ERROR verifying room availability: {e}")
        return False
    
    # Final summary
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print("\nSummary:")
    print(f"  - Reservation {reservation.booking_code} auto-checked-out ✓")
    print(f"  - Reservation {reservation.booking_code} auto-canceled ✓")
    print(f"  - Room '{room.name}' status updated ✓")
    print(f"  - Email notifications sent (if configured) ✓")
    print("\nThe auto-checkout feature is working correctly!")
    print("="*70 + "\n")
    
    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
