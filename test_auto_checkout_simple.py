#!/usr/bin/env python
"""
Script to test the auto-checkout feature by creating a test reservation
and then running the auto-cancel command.

Usage:
    python test_auto_checkout_simple.py
"""

import os
import sys
import django
from datetime import date, timedelta, datetime, time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quanlykhachsannn.settings')
django.setup()

from django.core.management import call_command
from django.utils import timezone
from django.conf import settings
from io import StringIO
from rooms.models import Room, Reservation, RoomCategory


def main():
    """Main test function"""
    print("\n" + "="*70)
    print("AUTO-CHECKOUT FEATURE - SIMPLE TEST")
    print("="*70)
    
    now = timezone.now()
    today = now.date()
    
    DEFAULT_CHECK_IN_TIME = getattr(settings, 'DEFAULT_CHECK_IN_TIME', '08:00')
    NO_SHOW_GRACE_HOURS = getattr(settings, 'NO_SHOW_GRACE_HOURS', 6)
    
    print(f"\nCurrent Time:          {now}")
    print(f"Current Date:          {today}")
    print(f"Check-in Time:         {DEFAULT_CHECK_IN_TIME}")
    print(f"Grace Period:          {NO_SHOW_GRACE_HOURS} hours")
    
    # Calculate threshold
    try:
        h, m = map(int, DEFAULT_CHECK_IN_TIME.split(':'))
    except Exception:
        h, m = 8, 0
    
    check_in_dt = datetime.combine(today, time(hour=h, minute=m))
    if timezone.is_naive(check_in_dt):
        check_in_dt = timezone.make_aware(check_in_dt)
    
    threshold = check_in_dt + timedelta(hours=int(NO_SHOW_GRACE_HOURS))
    
    print(f"\nAuto-cancel Threshold: {threshold}")
    print(f"Current time >= Threshold: {now >= threshold}")
    
    if now < threshold:
        mins_remaining = int((threshold - now).total_seconds() / 60)
        print(f"⚠️  Auto-checkout will trigger in ~{mins_remaining} minutes")
        print(f"\n✅ Grace period is working correctly!")
        print(f"   Reservations created now will be auto-cancelled at {threshold}")
    else:
        print(f"✅ Ready for auto-checkout!")
        print(f"   Any no-show reservations created now will be processed.")
    
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
    tomorrow = today + timedelta(days=1)
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
    
    print(f"\n{'='*70}")
    print(f"Test Reservation Created: {reservation.booking_code}")
    print(f"{'='*70}")
    print(f"Room:        {room.name}")
    print(f"Check-in:    {today}")
    print(f"Check-out:   {tomorrow}")
    print(f"Initial Status:")
    print(f"  - is_checked_in:  {reservation.is_checked_in}")
    print(f"  - is_checked_out: {reservation.is_checked_out}")
    print(f"  - is_canceled:    {reservation.is_canceled}")
    
    # Run the command
    print(f"\nRunning: python manage.py auto_cancel_no_shows")
    out = StringIO()
    call_command('auto_cancel_no_shows', stdout=out)
    print(out.getvalue())
    
    # Check result
    reservation.refresh_from_db()
    print(f"\nAfter Command:")
    print(f"  - is_checked_out: {reservation.is_checked_out}")
    print(f"  - is_canceled:    {reservation.is_canceled}")
    print(f"  - checkout_at:    {reservation.checkout_at}")
    print(f"  - canceled_at:    {reservation.canceled_at}")
    
    if reservation.is_checked_out and reservation.is_canceled:
        print(f"\n✅ SUCCESS! Auto-checkout & auto-cancel worked!")
    elif now < threshold:
        print(f"\n⓵ Note: Grace period is still active.")
        print(f"   Auto-checkout will trigger at {threshold}")
    else:
        print(f"\n⚠️  Auto-checkout didn't trigger. Check logs for details.")
    
    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
