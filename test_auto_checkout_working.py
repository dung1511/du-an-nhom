#!/usr/bin/env python
"""
Script to test the auto-checkout feature by creating a test reservation
and then running the auto-cancel command.

Usage:
    python test_auto_checkout_working.py
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
    print("AUTO-CHECKOUT FEATURE - WORKING TEST")
    print("="*70)
    
    now = timezone.now()
    today = now.date()
    
    DEFAULT_CHECK_IN_TIME = getattr(settings, 'DEFAULT_CHECK_IN_TIME', '08:00')
    NO_SHOW_GRACE_HOURS = getattr(settings, 'NO_SHOW_GRACE_HOURS', 6)
    
    print(f"\n📋 Configuration:")
    print(f"   Current Time:         {now}")
    print(f"   Current Date:         {today}")
    print(f"   Check-in Time:        {DEFAULT_CHECK_IN_TIME}")
    print(f"   Grace Period:         {NO_SHOW_GRACE_HOURS} hours")
    print(f"   Timezone Aware:       {timezone.is_aware(now)}")
    
    # Calculate threshold (same logic as in the command)
    try:
        h, m = map(int, DEFAULT_CHECK_IN_TIME.split(':'))
    except Exception:
        h, m = 8, 0
    
    check_in_dt = datetime.combine(today, time(hour=h, minute=m))
    if timezone.is_naive(check_in_dt):
        check_in_dt = timezone.make_aware(check_in_dt)
    
    # Make sure now is in the same timezone state as check_in_dt
    if timezone.is_naive(check_in_dt) and timezone.is_aware(now):
        now = timezone.make_naive(now) 
    elif timezone.is_aware(check_in_dt) and timezone.is_naive(now):
        now = timezone.make_aware(now)
    
    threshold = check_in_dt + timedelta(hours=int(NO_SHOW_GRACE_HOURS))
    
    print(f"\n⏰ Auto-Cancel Calculation:")
    print(f"   Check-in DateTime:    {check_in_dt}")
    print(f"   Auto-cancel at:       {threshold}")
    print(f"   Current >= Threshold: {now >= threshold}")
    
    if now < threshold:
        remaining = threshold - now
        mins = int(remaining.total_seconds() / 60)
        print(f"\n⏳ Grace period active: ~{mins} minutes remaining")
    else:
        print(f"\n✅ Ready for auto-checkout!")
    
    # Create test room
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
    
    # Create test reservation
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
    print(f"📌 Test Reservation: {reservation.booking_code}")
    print(f"{'='*70}")
    print(f"   Room:         {room.name}")
    print(f"   Check-in:     {today}")
    print(f"   Check-out:    {tomorrow}")
    print(f"   Status Before:")
    print(f"      - Checked-in:  {reservation.is_checked_in}")
    print(f"      - Checked-out: {reservation.is_checked_out}")
    print(f"      - Canceled:    {reservation.is_canceled}")
    
    # Run the auto-cancel command
    print(f"\n▶️  Running: python manage.py auto_cancel_no_shows")
    print("-" * 70)
    out = StringIO()
    call_command('auto_cancel_no_shows', stdout=out)
    output = out.getvalue()
    print(output)
    print("-" * 70)
    
    # Check result
    reservation.refresh_from_db()
    print(f"\n   Status After:")
    print(f"      - Checked-out: {reservation.is_checked_out}")
    print(f"      - Canceled:    {reservation.is_canceled}")
    if reservation.is_checked_out:
        print(f"      - Checkout At: {reservation.checkout_at}")
    if reservation.is_canceled:
        print(f"      - Canceled At: {reservation.canceled_at}")
        print(f"      - Reason:     {reservation.canceled_reason}")
    
    print(f"\n{'='*70}")
    
    # Summary
    if reservation.is_checked_out and reservation.is_canceled:
        print("✅ SUCCESS! Auto-checkout & auto-cancel worked correctly!")
        print(f"   Room {room.name} is now available for rebooking")
    elif now < threshold:
        print("⓵ Grace period is still active")
        print(f"   Auto-checkout will trigger at: {threshold}")
        print(f"   Create a reservation with check_in_date in the past to test")
    else:
        print("⚠️  Reservation wasn't processed. Check the database.")
        print(f"   Verify: check_in_date={today}, not checked-in, not canceled")
    
    print(f"{'='*70}\n")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
