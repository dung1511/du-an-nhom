from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, time, timedelta as dt_timedelta
from django.conf import settings
from django.core.mail import mail_admins, send_mail

from rooms.models import Reservation


DEFAULT_CHECK_IN_TIME = getattr(settings, 'DEFAULT_CHECK_IN_TIME', '08:00')
DEFAULT_NO_SHOW_GRACE_HOURS = getattr(settings, 'NO_SHOW_GRACE_HOURS', 6)


class Command(BaseCommand):
    help = 'Auto-cancel & auto-checkout reservations where guest did not show up on check-in date after grace period. Updates room status automatically.'

    def handle(self, *args, **options):
        now = timezone.now()
        today = now.date()

        canceled = []
        checked_out = []

        for reservation in Reservation.objects.filter(
            check_in_date=today,
            is_checked_in=False,
            is_checked_out=False,
            is_canceled=False,
        ):
            # build threshold datetime: check_in_date + DEFAULT_CHECK_IN_TIME + grace hours
            try:
                h, m = map(int, DEFAULT_CHECK_IN_TIME.split(':'))
            except Exception:
                h, m = 8, 0

            check_in_dt = datetime.combine(reservation.check_in_date, time(hour=h, minute=m))
            # Ensure timezone-aware when comparing with timezone.now()
            if timezone.is_naive(check_in_dt):
                check_in_dt = timezone.make_aware(check_in_dt)

            threshold = check_in_dt + dt_timedelta(hours=int(DEFAULT_NO_SHOW_GRACE_HOURS))

            # Ensure both datetimes are comparable (both aware or both naive)
            if timezone.is_naive(now) and timezone.is_aware(threshold):
                now = timezone.make_aware(now)

            if now >= threshold:
                # Step 1: Auto-checkout (mark as checked out and free up the room)
                reservation.is_checked_out = True
                reservation.checkout_at = now
                reservation.actual_check_out_date = today
                reservation.save(update_fields=['is_checked_out', 'checkout_at', 'actual_check_out_date'])
                checked_out.append(reservation.booking_code)
                
                # Step 2: Cancel the reservation
                reason = 'no_show_auto_cancel'
                reservation.cancel_reservation(reason=reason)
                canceled.append(reservation.booking_code)

                # Step 3: Notify admins
                subject = f'Auto-cancelled booking {reservation.booking_code} (no-show)'
                body = (
                    f'Reservation {reservation.booking_code} (id={reservation.id}) was auto-checked-out and cancelled due to no-show on {reservation.check_in_date}.\n'
                    f'Guest: {reservation.first_name or ""} {reservation.last_name or ""} - {reservation.email or "(no email)"}\n'
                    f'Room: {reservation.room.name if reservation.room else "Unknown"}\n'
                    f'Room status has been updated to AVAILABLE.'
                )
                try:
                    mail_admins(subject, body, fail_silently=True)
                except Exception:
                    try:
                        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [a for _, a in getattr(settings, 'ADMINS', [])], fail_silently=True)
                    except Exception:
                        pass

                # Step 4: Notify guest if email exists
                if reservation.email:
                    try:
                        send_mail(
                            f'Booking {reservation.booking_code} đã bị hủy (không tới)',
                            f'Chào {reservation.first_name or "Khách"},\n\nĐặt phòng {reservation.booking_code} đã được tự động check-out và hủy vì không nhận phòng đúng ngày ({reservation.check_in_date}).\n\n'
                            f'Phòng: {reservation.room.name if reservation.room else "Unknown"}\n'
                            f'Trạng thái phòng đã được cập nhật thành CÓ SẴN.\n\n'
                            f'Nếu có thắc mắc, vui lòng liên hệ với chúng tôi.',
                            settings.DEFAULT_FROM_EMAIL,
                            [reservation.email],
                            fail_silently=True,
                        )
                    except Exception:
                        pass

        self.stdout.write(self.style.SUCCESS(
            f'Auto-cancel & auto-checkout completed.\n'
            f'  - {len(checked_out)} reservation(s) auto-checked-out\n'
            f'  - {len(canceled)} reservation(s) canceled\n'
            f'  - Room status(es) updated to AVAILABLE'
        ))