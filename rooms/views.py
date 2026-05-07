import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import quote_plus

from blog.models import Blog
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Avg, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from feedback.forms import FeedbackForm
from feedback.models import Feedback
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import BookingForm
from .models import Coupon, Reservation, Room, RoomCategory, RoomImage, Service
from .permissions import IsStaffOrAdmin
from .serializers import (
    ReservationCheckInSerializer,
    ReservationCheckoutSerializer,
    ReservationCreateSerializer,
    ReservationDetailSerializer,
    ReservationPaymentSerializer,
    ReturnedReservationSerializer,
    ServiceSerializer,
    RoomCategorySerializer,
    RoomSearchSerializer,
    RoomSerializer,
)
from .serializers import UploadDepositReceiptSerializer
from django.core.mail import mail_admins, send_mail
from django.conf import settings
from .upload_security import build_safe_filename, validate_image_file


logger = logging.getLogger(__name__)

DEFAULT_CHECK_IN_TIME = '08:00'
DEFAULT_CHECK_OUT_TIME = '12:00'


def _has_admin_booking_access(user):
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def _reservation_queryset_for_user(user):
    queryset = Reservation.objects.select_related('room', 'user', 'coupon')
    if _has_admin_booking_access(user):
        return queryset.order_by('-created_at')
    return queryset.filter(user=user).order_by('-created_at')


def _get_reservation_by_booking_code(booking_code):
    reservation_id = Reservation.get_reservation_id_from_booking_code(booking_code)
    return get_object_or_404(
        Reservation.objects.select_related('room', 'user', 'coupon').prefetch_related('selected_services'),
        id=reservation_id,
    )


def _normalize_payment_method(value):
    normalized = (value or '').strip().lower()
    if normalized in {'pay_on_arrival', 'cash'}:
        return 'cash'
    if normalized in {'momo', 'momo_qr', 'momo-qr'}:
        return 'momo_qr'
    if normalized == 'cards':
        return 'cards'
    return 'cash'


def _build_momo_qr_url(reservation):
    account_name = 'PHAM MONG KIEU'
    account_number = '1031249010'
    bank_short_name = 'VCB'

    amount = reservation.deposit_amount or reservation.final_total or Decimal('0.00')
    amount_value = str(amount.quantize(Decimal('1')))

    note_parts = [reservation.booking_code]
    if reservation.first_name or reservation.last_name:
        note_parts.append(' '.join(part for part in [reservation.first_name, reservation.last_name] if part).strip())
    transfer_note = ' - '.join(part for part in note_parts if part)

    return (
        'https://img.vietqr.io/image/'
        f'{bank_short_name}-{account_number}-compact2.png'
        f'?amount={quote_plus(amount_value)}'
        f'&addInfo={quote_plus(transfer_note)}'
        f'&accountName={quote_plus(account_name)}'
    )


def _build_reservation_invoice_context(reservation):
    num_nights = (reservation.check_out_date - reservation.check_in_date).days
    if num_nights <= 0:
        num_nights = 1

    vietnamese_weekdays = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

    def format_vietnamese_date(value):
        if not value:
            return ''
        return f"{vietnamese_weekdays[value.weekday()]}, {value.day} tháng {value.month} {value.year}"

    def format_datetime(value):
        if not value:
            return 'Chưa có'
        return value.strftime('%d/%m/%Y %H:%M')

    check_in_time = format_datetime(reservation.checked_in_at) if reservation.checked_in_at else 'Chưa check-in'
    check_out_time = format_datetime(reservation.checkout_at) if reservation.checkout_at else 'Chưa check-out'
    has_damage = bool(reservation.damage_reported or reservation.damage_fee)
    check_in_default_slot = f"{format_vietnamese_date(reservation.check_in_date)} - {DEFAULT_CHECK_IN_TIME}"
    check_out_default_slot = f"{format_vietnamese_date(reservation.check_out_date)} - {DEFAULT_CHECK_OUT_TIME}"
    payment_method = _normalize_payment_method(reservation.payment_method)
    momo_qr_url = _build_momo_qr_url(reservation)

    return {
        'reservation': reservation,
        'booking_code': reservation.booking_code,
        'num_nights': num_nights,
        'deposit_amount': reservation.deposit_amount,
        'balance_due': reservation.balance_due,
        'damage_fee': reservation.damage_fee,
        'final_total': reservation.final_total,
        'damage_reported': reservation.damage_reported,
        'damage_notes': reservation.damage_notes,
        'check_in_display': format_vietnamese_date(reservation.check_in_date),
        'check_out_display': format_vietnamese_date(reservation.check_out_date),
        'check_in_time': check_in_time,
        'check_out_time': check_out_time,
        'default_check_in_time': DEFAULT_CHECK_IN_TIME,
        'default_check_out_time': DEFAULT_CHECK_OUT_TIME,
        'check_in_default_slot': check_in_default_slot,
        'check_out_default_slot': check_out_default_slot,
        'has_damage': has_damage,
        'actual_guest_count': (reservation.checked_in_adults or 0) + (reservation.checked_in_children or 0),
        'payment_method': payment_method,
        'momo_qr_url': momo_qr_url,
        'bank_name': 'Vietcombank',
        'bank_account_name': 'PHAM MONG KIEU',
        'bank_account_number': '1031249010',
    }


def _build_reservation_invoice_payload(reservation):
    guest_name = ' '.join(part for part in [reservation.first_name, reservation.last_name] if part).strip()
    if not guest_name:
        guest_name = 'Khach hang'

    return {
        'booking_code': reservation.booking_code,
        'booking_confirmation_url': reverse('rooms:booking_confirmation', kwargs={'reservation_id': reservation.id}),
        'invoice': {
            'booking_code': reservation.booking_code,
            'guest_name': guest_name,
            'room_name': reservation.room.name,
            'check_in_date': reservation.check_in_date.isoformat() if reservation.check_in_date else None,
            'check_out_date': reservation.check_out_date.isoformat() if reservation.check_out_date else None,
            'num_nights': max(1, (reservation.check_out_date - reservation.check_in_date).days),
            'subtotal': str(reservation.subtotal),
            'gst': str(reservation.gst),
            'discount_applied': str(reservation.discount_applied),
            'service_total': str(reservation.service_total),
            'deposit_amount': str(reservation.deposit_amount),
            'balance_due': str(reservation.balance_due),
            'damage_fee': str(reservation.damage_fee),
            'final_total': str(reservation.final_total),
            'payment_status': reservation.payment_status,
        },
    }


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    page_query_param = 'page'
    max_page_size = 100

    def get_paginated_response(self, data):
        total_pages = self.page.paginator.num_pages
        return Response(
            {
                'results': data,
                'pagination': {
                    'page': self.page.number,
                    'limit': self.get_page_size(self.request),
                    'total_items': self.page.paginator.count,
                    'total_pages': total_pages,
                    'has_next': self.page.has_next(),
                    'has_previous': self.page.has_previous(),
                },
            }
        )


class ReservationListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ReservationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        reservation = serializer.save()
        transaction.on_commit(lambda reservation=reservation: _send_booking_confirmation_email(reservation, reason='created'))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        reservation = serializer.instance
        headers = self.get_success_headers(serializer.data)
        response_data = dict(serializer.data)
        response_data['user'] = reservation.user_id
        response_data.update(_build_reservation_invoice_payload(reservation))

        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)


class ReservationCheckoutAPIView(generics.UpdateAPIView):
    serializer_class = ReservationCheckoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return Reservation.objects.all() if _has_admin_booking_access(self.request.user) else Reservation.objects.filter(user=self.request.user)

    def get_object(self):
        reservation = super().get_object()
        if not (_has_admin_booking_access(self.request.user) or reservation.user_id == self.request.user.id):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied('Không có quyền truy cập đặt phòng này.')
        return reservation

    def update(self, request, *args, **kwargs):
        reservation = self.get_object()

        if reservation.is_checked_out:
            return Response({'error': 'Phòng này đã được trả rồi.'}, status=status.HTTP_400_BAD_REQUEST)

        if not reservation.is_checked_in:
            return Response({'error': 'Booking chưa check-in, không thể check-out.'}, status=status.HTTP_400_BAD_REQUEST)

        is_early_checkout = date.today() < reservation.check_out_date

        serializer = self.get_serializer(reservation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        message = f'Trả phòng {reservation.room.name} thành công!'
        if is_early_checkout:
            message += ' Đây là trả phòng sớm trước ngày dự kiến, hệ thống giữ nguyên tổng hóa đơn theo booking.'

        return Response(
            {
                'success': True,
                'message': message,
                'reservation': serializer.data,
                'final_total': str(reservation.final_total),
                'is_early_checkout': is_early_checkout,
            },
            status=status.HTTP_200_OK,
        )


class ReservationCheckInAPIView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def post(self, request):
        serializer = ReservationCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reservation = serializer.validated_data['reservation']
        checked_in_adults = serializer.validated_data['checked_in_adults']
        checked_in_children = serializer.validated_data.get('checked_in_children', 0)
        actual_check_in_date = serializer.validated_data.get('actual_check_in_date')

        # Tính số ngày check-in sớm
        early_days = 0
        if actual_check_in_date and actual_check_in_date < reservation.check_in_date:
            early_days = (reservation.check_in_date - actual_check_in_date).days

        # Nếu khách thanh toán chuyển khoản (momo_qr) nhưng admin chưa xác nhận, chặn check-in
        if reservation.payment_method == 'momo_qr' and not reservation.deposit_confirmed:
            return Response({'error': 'Chưa có xác nhận chuyển khoản từ admin, không thể check-in.'}, status=status.HTTP_400_BAD_REQUEST)

        reservation.is_checked_in = True
        reservation.checked_in_at = datetime.now()
        reservation.checked_in_adults = checked_in_adults
        reservation.checked_in_children = checked_in_children
        # Đánh dấu trạng thái thanh toán là 'paid' chỉ khi cần thiết (sau khi đã qua kiểm tra xác nhận deposit)
        reservation.payment_status = 'paid'
        reservation.actual_check_in_date = actual_check_in_date
        reservation.early_checkin_days = early_days
        
        # Tính phí check-in sớm
        reservation.sync_financial_fields()
        
        reservation.save(
            update_fields=[
                'is_checked_in',
                'checked_in_at',
                'checked_in_adults',
                'checked_in_children',
                'payment_status',
                'actual_check_in_date',
                'early_checkin_days',
                'early_checkin_fee',
                'final_total',
                'deposit_amount',
                'balance_due',
            ]
        )

        message = f'Check-in thành công cho booking {reservation.booking_code}.'
        if early_days > 0:
            message += f' Check-in sớm {early_days} ngày. Phí check-in sớm: {reservation.early_checkin_fee} VND.'

        return Response(
            {
                'success': True,
                'message': message,
                'booking_code': reservation.booking_code,
                'guest_name': f'{reservation.first_name or ""} {reservation.last_name or ""}'.strip(),
                'room': reservation.room.name,
                'checked_in_guests': checked_in_adults + checked_in_children,
                'early_checkin_days': early_days,
                'early_checkin_fee': str(reservation.early_checkin_fee),
                'amount_due_collected': str(reservation.balance_due),
                'final_total': str(reservation.final_total),
                'payment_status': reservation.payment_status,
            },
            status=status.HTTP_200_OK,
        )


class UploadDepositReceiptAPIView(APIView):
    """Khách upload ảnh biên lai deposit (QR -> mở form upload)."""
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = []  # allow anonymous via QR link

    def post(self, request, id):
        reservation = get_object_or_404(Reservation, id=id)
        booking_code = (request.data.get('booking_code') or request.query_params.get('booking_code') or '').strip()
        if not booking_code or booking_code.upper() != reservation.booking_code:
            return Response({'detail': 'Mã booking không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UploadDepositReceiptSerializer(reservation, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        reservation.deposit_receipt_uploaded_at = timezone.now()
        reservation.save(update_fields=['deposit_receipt', 'deposit_receipt_uploaded_at'])

        # Send notification to admins
        subject = f'New deposit receipt uploaded for {reservation.booking_code}'
        body = (
            f'A deposit receipt has been uploaded for booking {reservation.booking_code} (id={reservation.id}).\n'
            f'Guest: {reservation.first_name or ""} {reservation.last_name or ""}\n'
            f'Email: {reservation.email or "(no email)"}\n'
            f'Please review in admin: {request.build_absolute_uri(reverse("admin:rooms_reservation_change", args=[reservation.id]))}'
        )
        try:
            # Prefer mail_admins (uses ADMINS setting); fallback to DEFAULT_FROM_EMAIL -> ADMINS
            mail_admins(subject, body, fail_silently=True)
        except Exception:
            try:
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [a for _, a in getattr(settings, 'ADMINS', [])], fail_silently=True)
            except Exception:
                logger.exception('Failed to send admin notification for deposit upload')

        return Response({'success': True, 'message': 'Biên lai đã được tải lên. Vui lòng chờ xác nhận từ admin.'})


def upload_deposit_page(request, reservation_id):
    """Web page where guest can upload deposit receipt (access via QR)."""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if request.method == 'POST':
        form_file = request.FILES.get('deposit_receipt')
        booking_code = (request.POST.get('booking_code') or '').strip()
        if not booking_code or booking_code.upper() != reservation.booking_code:
            messages.error(request, 'Mã booking không hợp lệ.')
            return redirect(request.path)

        if not form_file:
            messages.error(request, 'Vui lòng chọn ảnh biên lai để tải lên.')
            return redirect(request.path)

        # Save file
        reservation.deposit_receipt = form_file
        reservation.deposit_receipt_uploaded_at = timezone.now()
        reservation.save(update_fields=['deposit_receipt', 'deposit_receipt_uploaded_at'])

        # Notify admins
        subject = f'New deposit receipt uploaded for {reservation.booking_code}'
        body = (
            f'A deposit receipt has been uploaded for booking {reservation.booking_code} (id={reservation.id}).\n'
            f'Guest: {reservation.first_name or ""} {reservation.last_name or ""}\n'
            f'Email: {reservation.email or "(no email)"}\n'
            f'Please review in admin: {request.build_absolute_uri(reverse("admin:rooms_reservation_change", args=[reservation.id]))}'
        )
        try:
            mail_admins(subject, body, fail_silently=True)
        except Exception:
            logger.exception('Failed to send admin notification for deposit upload (web)')

        messages.success(request, 'Biên lai đã được tải lên. Vui lòng chờ xác nhận từ admin.')
        return redirect('rooms:booking_confirmation', reservation_id=reservation.id)

    # Build QR link to this page
    upload_url = request.build_absolute_uri(reverse('rooms:upload_deposit_page', args=[reservation.id]))
    qr_image_url = f'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={quote_plus(upload_url)}'
    context = {'reservation': reservation, 'upload_url': upload_url, 'qr_image_url': qr_image_url}
    return render(request, 'rooms/upload_deposit.html', context)


class AdminConfirmDepositAPIView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def post(self, request, id):
        reservation = get_object_or_404(Reservation, id=id)
        if not reservation.deposit_receipt:
            return Response({'detail': 'Không có biên lai để xác nhận.'}, status=status.HTTP_400_BAD_REQUEST)

        # Mark confirmed
        reservation.deposit_confirmed = True
        reservation.deposit_confirmed_at = timezone.now()
        reservation.deposit_confirmed_by = request.user
        reservation.deposit_paid_via_qr = reservation.deposit_amount or reservation.deposit_paid_via_qr
        reservation.payment_status = 'paid'
        reservation.save(update_fields=['deposit_confirmed', 'deposit_confirmed_at', 'deposit_confirmed_by', 'deposit_paid_via_qr', 'payment_status'])

        return Response({'success': True, 'message': 'Đã xác nhận biên lai và cập nhật trạng thái thanh toán.'})


@login_required
@ensure_csrf_cookie
def frontdesk_dashboard(request):
    if not _has_admin_booking_access(request.user):
        messages.error(request, 'Bạn không có quyền truy cập màn hình lễ tân.')
        return redirect('home')

    reservation = None
    booking_code = (request.POST.get('booking_code') or request.GET.get('booking_code') or '').strip()
    action = (request.POST.get('action') or '').strip().lower()
    checked_in_result = None
    checkout_result = None

    room_query = (request.GET.get('room_query') or '').strip()
    service_query = (request.GET.get('service_query') or '').strip()
    availability_error = None

    raw_check_in = (request.GET.get('available_check_in') or '').strip()
    raw_check_out = (request.GET.get('available_check_out') or '').strip()
    raw_adults = (request.GET.get('available_adults') or '').strip()

    available_check_in = date.today()
    available_check_out = date.today() + timedelta(days=1)
    available_adults = 1

    if raw_check_in:
        try:
            available_check_in = datetime.strptime(raw_check_in, '%Y-%m-%d').date()
        except ValueError:
            availability_error = 'Ngày check-in tra cứu không hợp lệ, đã dùng ngày hôm nay.'

    if raw_check_out:
        try:
            available_check_out = datetime.strptime(raw_check_out, '%Y-%m-%d').date()
        except ValueError:
            availability_error = 'Ngày check-out tra cứu không hợp lệ, đã dùng ngày mặc định.'

    if available_check_out <= available_check_in:
        available_check_out = available_check_in + timedelta(days=1)
        availability_error = 'Ngày check-out phải sau check-in, hệ thống đã tự điều chỉnh +1 ngày.'

    if raw_adults:
        try:
            available_adults = max(1, int(raw_adults))
        except ValueError:
            available_adults = 1
            availability_error = 'Số khách tra cứu không hợp lệ, hệ thống đã đặt về 1.'

    available_rooms = Room.objects.available_rooms(available_check_in, available_check_out, available_adults).select_related('category').order_by('price')
    if room_query:
        available_rooms = available_rooms.filter(Q(name__icontains=room_query) | Q(category__name__icontains=room_query))

    services = Service.objects.filter(active=True).order_by('order', 'name')
    if service_query:
        services = services.filter(Q(name__icontains=service_query) | Q(description__icontains=service_query))

    if request.method == 'POST' and booking_code:
        try:
            reservation = _get_reservation_by_booking_code(booking_code)
        except Exception:
            reservation = None
            messages.error(request, 'Không tìm thấy booking tương ứng.')
        else:
            if action == 'checkin':
                try:
                    actual_check_in_str = (request.POST.get('actual_check_in_date') or '').strip()
                    checkin_payload = {
                        'booking_code': booking_code,
                        'checked_in_adults': int(request.POST.get('checked_in_adults', 1)),
                        'checked_in_children': int(request.POST.get('checked_in_children', 0)),
                    }
                    if actual_check_in_str:
                        checkin_payload['actual_check_in_date'] = actual_check_in_str
                except (TypeError, ValueError):
                    messages.error(request, 'Số lượng khách check-in không hợp lệ.')
                else:
                    serializer = ReservationCheckInSerializer(data=checkin_payload)
                    try:
                        serializer.is_valid(raise_exception=True)
                    except DRFValidationError as exc:
                        detail = exc.detail
                        if isinstance(detail, dict):
                            non_field = detail.get('non_field_errors') or []
                            message = non_field[0] if non_field else 'Không thể check-in booking này.'
                        elif isinstance(detail, list) and detail:
                            message = detail[0]
                        else:
                            message = 'Không thể check-in booking này.'
                        messages.error(request, str(message))
                    else:
                        reservation = serializer.validated_data['reservation']
                        checked_in_adults = serializer.validated_data['checked_in_adults']
                        checked_in_children = serializer.validated_data.get('checked_in_children', 0)
                        actual_check_in_date = serializer.validated_data.get('actual_check_in_date')

                        # Tính số ngày check-in sớm
                        early_days = 0
                        if actual_check_in_date and actual_check_in_date < reservation.check_in_date:
                            early_days = (reservation.check_in_date - actual_check_in_date).days

                        reservation.is_checked_in = True
                        reservation.checked_in_at = datetime.now()
                        reservation.checked_in_adults = checked_in_adults
                        reservation.checked_in_children = checked_in_children
                        reservation.payment_status = 'paid'
                        reservation.actual_check_in_date = actual_check_in_date
                        reservation.early_checkin_days = early_days
                        reservation.sync_financial_fields()
                        reservation.save(
                            update_fields=[
                                'is_checked_in',
                                'checked_in_at',
                                'checked_in_adults',
                                'checked_in_children',
                                'payment_status',
                                'actual_check_in_date',
                                'early_checkin_days',
                                'early_checkin_fee',
                                'final_total',
                                'deposit_amount',
                                'balance_due',
                            ]
                        )
                        checked_in_result = reservation
                        messages.success(
                            request,
                            f'Check-in thành công cho {reservation.booking_code}. Đã xác nhận {checked_in_adults + checked_in_children} khách và thu phần còn lại {reservation.balance_due}.',
                        )
            elif action == 'checkout':
                if reservation.is_checked_out:
                    messages.error(request, 'Booking này đã check-out rồi.')
                elif not reservation.is_checked_in:
                    messages.error(request, 'Booking chưa check-in nên chưa thể check-out.')
                else:
                    damage_reported = request.POST.get('damage_reported') in {'1', 'true', 'True', 'on'}
                    damage_notes = (request.POST.get('damage_notes') or '').strip()
                    actual_check_out_str = (request.POST.get('actual_check_out_date') or '').strip()
                    
                    # Parse actual check-out date
                    actual_check_out_date = None
                    if actual_check_out_str:
                        try:
                            actual_check_out_date = datetime.strptime(actual_check_out_str, '%Y-%m-%d').date()
                        except ValueError:
                            messages.error(request, 'Ngày check-out không hợp lệ.')
                            actual_check_out_date = None
                    
                    if actual_check_out_date is None:
                        actual_check_out_date = reservation.check_out_date
                    
                    # Tính số ngày check-out sớm
                    early_checkout_days = 0
                    if actual_check_out_date < reservation.check_out_date:
                        early_checkout_days = (reservation.check_out_date - actual_check_out_date).days
                    
                    is_early_checkout = date.today() < reservation.check_out_date
                    reservation.damage_reported = damage_reported
                    reservation.damage_notes = damage_notes
                    reservation.is_checked_out = True
                    reservation.actual_check_out_date = actual_check_out_date
                    reservation.early_checkout_days = early_checkout_days
                    if not reservation.checkout_at:
                        reservation.checkout_at = datetime.now()
                    reservation.sync_financial_fields()
                    reservation.save(
                        update_fields=[
                            'is_checked_out',
                            'checkout_at',
                            'damage_reported',
                            'damage_notes',
                            'damage_fee',
                            'actual_check_out_date',
                            'early_checkout_days',
                            'early_checkout_refund',
                            'final_total',
                            'deposit_amount',
                            'balance_due',
                        ]
                    )
                    checkout_result = reservation
                    if reservation.email:
                        transaction.on_commit(lambda reservation=reservation: _send_invoice_email(reservation))
                    else:
                        messages.warning(request, 'Khách chưa có email nên chưa thể gửi thông báo hóa đơn tự động.')

                    if damage_reported:
                        message = (
                            f'Check-out thành công cho {reservation.booking_code}. '
                            f'Hư hỏng được ghi nhận, phụ phí 10% là {reservation.damage_fee}. '
                            f'Tổng thanh toán cuối: {reservation.final_total}.'
                        )
                        if is_early_checkout:
                            message += ' Đây là trả phòng sớm, hóa đơn vẫn tính theo booking ban đầu.'
                        if reservation.email:
                            message += ' Hóa đơn đã được gửi vào email của khách.'
                        messages.success(request, message)
                    else:
                        message = (
                            f'Check-out thành công cho {reservation.booking_code}. '
                            f'Tổng thanh toán cuối: {reservation.final_total}.'
                        )
                        if is_early_checkout:
                            message += ' Đây là trả phòng sớm, hóa đơn vẫn tính theo booking ban đầu.'
                        if reservation.email:
                            message += ' Hóa đơn đã được gửi vào email của khách.'
                        messages.success(request, message)

    if reservation is None and booking_code:
        try:
            reservation = _get_reservation_by_booking_code(booking_code)
        except Exception:
            reservation = None

    checkin_warning = None
    if reservation:
        test_payload = {
            'booking_code': reservation.booking_code,
            'checked_in_adults': 1,
            'checked_in_children': 0,
            'actual_check_in_date': str(date.today()),  # Test with today's date for early check-in
        }
        test_serializer = ReservationCheckInSerializer(data=test_payload)
        if not test_serializer.is_valid():
            errors = test_serializer.errors
            if isinstance(errors, dict):
                non_field = errors.get('non_field_errors', [])
                if non_field:
                    checkin_warning = str(non_field[0])
            elif isinstance(errors, list) and errors:
                checkin_warning = str(errors[0])

    return render(
        request,
        'rooms/frontdesk_dashboard.html',
        {
            'reservation': reservation,
            'booking_code': booking_code,
            'checked_in_result': checked_in_result,
            'checkout_result': checkout_result,
            'checkin_warning': checkin_warning,
            'default_check_in_time': DEFAULT_CHECK_IN_TIME,
            'default_check_out_time': DEFAULT_CHECK_OUT_TIME,
            'room_query': room_query,
            'service_query': service_query,
            'available_check_in': available_check_in,
            'available_check_out': available_check_out,
            'available_adults': available_adults,
            'available_rooms': available_rooms,
            'services': services,
            'availability_error': availability_error,
        },
    )


class ReservationDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ReservationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return _reservation_queryset_for_user(self.request.user)


class ReservationListAPIView(generics.ListAPIView):
    serializer_class = ReservationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _reservation_queryset_for_user(self.request.user)

    def post(self, request, *args, **kwargs):
        serializer = ReservationCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        reservation = serializer.save()
        transaction.on_commit(lambda reservation=reservation: _send_booking_confirmation_email(reservation, reason='created'))

        response_data = ReservationDetailSerializer(reservation).data
        response_data['user'] = reservation.user_id
        response_data.update(_build_reservation_invoice_payload(reservation))

        return Response(response_data, status=status.HTTP_201_CREATED)


class ReservationCheckedOutListAPIView(generics.ListAPIView):
    serializer_class = ReservationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        base_queryset = Reservation.objects.filter(is_checked_out=True)
        if _has_admin_booking_access(self.request.user):
            return base_queryset.order_by('-created_at')
        return base_queryset.filter(user=self.request.user).order_by('-created_at')


class RoomListAPIView(generics.ListAPIView):
    serializer_class = RoomSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Room.objects.select_related('category').all()
        params = self.request.query_params

        keyword = (params.get('tuKhoa') or params.get('q') or '').strip()
        category = (params.get('danhMuc') or params.get('category') or '').strip()
        size = (params.get('kichThuoc') or params.get('size') or '').strip()
        min_price = params.get('giaTu') or params.get('price_min')
        max_price = params.get('giaDen') or params.get('price_max')
        min_rating = params.get('danhGia') or params.get('min_rating')

        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(category__name__icontains=keyword)
            )

        if category:
            queryset = queryset.filter(category__name__iexact=category)

        if size:
            queryset = queryset.filter(size__iexact=size)

        if min_price:
            try:
                queryset = queryset.filter(price__gte=Decimal(min_price))
            except Exception:
                pass

        if max_price:
            try:
                queryset = queryset.filter(price__lte=Decimal(max_price))
            except Exception:
                pass

        if min_rating:
            try:
                queryset = queryset.annotate(avg_rating=Avg('feedback__rating')).filter(avg_rating__gte=float(min_rating))
            except Exception:
                pass

        return queryset.order_by('id')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if 'limit' not in request.query_params and 'page' not in request.query_params:
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RoomDetailAPIView(generics.RetrieveAPIView):
    serializer_class = RoomSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

    def get_queryset(self):
        return Room.objects.all()


class RoomCategoryListAPIView(generics.ListAPIView):
    serializer_class = RoomCategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return RoomCategory.objects.all().order_by('name')


class RoomSearchAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RoomSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        check_in = serializer.validated_data['check_in_date']
        check_out = serializer.validated_data['check_out_date']
        adults = serializer.validated_data['adults']
        children = serializer.validated_data.get('children', 0)
        limit = serializer.validated_data.get('limit', 5)

        suitable_rooms = Room.objects.search_suitable_rooms(
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
            limit=limit,
        )
        recommended_combos = Room.objects.recommend_room_combinations(
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
            max_rooms=2,
            limit=3,
        )

        num_nights = (check_out - check_in).days
        rooms_data = []
        for room in suitable_rooms:
            rooms_data.append(
                {
                    **RoomSerializer(room).data,
                    'num_nights': num_nights,
                    'subtotal': str(room.price * num_nights),
                    'gst': str(room.price * num_nights * Decimal('0.18')),
                    'total': str(room.price * num_nights * Decimal('1.18')),
                }
            )

        combo_data = []
        for combo in recommended_combos:
            combo_rooms = []
            for room in combo['rooms']:
                combo_rooms.append(
                    {
                        **RoomSerializer(room).data,
                        'subtotal': str(room.price * num_nights),
                        'gst': str(room.price * num_nights * Decimal('0.18')),
                        'total': str(room.price * num_nights * Decimal('1.18')),
                    }
                )

            combo_data.append(
                {
                    'rooms': combo_rooms,
                    'total_capacity': combo['total_capacity'],
                    'total_price': str(combo['total_price']),
                }
            )

        total_guests = adults + children
        return Response(
            {
                'success': True,
                'search_criteria': {
                    'check_in_date': check_in,
                    'check_out_date': check_out,
                    'adults': adults,
                    'children': children,
                    'total_guests': total_guests,
                    'num_nights': num_nights,
                },
                'results': {'count': len(rooms_data), 'rooms': rooms_data},
                'recommended_combos': combo_data,
                'message': f'Tìm thấy {len(rooms_data)} phòng phù hợp cho {total_guests} khách.',
            },
            status=status.HTTP_200_OK,
        )


class ReservationPaymentAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = ReservationPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return _reservation_queryset_for_user(self.request.user)

    def update(self, request, *args, **kwargs):
        reservation = self.get_object()
        serializer = self.get_serializer(reservation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        reservation = serializer.save()
        if reservation.payment_status == 'paid':
            transaction.on_commit(
                lambda reservation=reservation: _send_booking_confirmation_email(reservation, reason='paid')
            )
        return Response(
            {
                'success': True,
                'message': 'Cập nhật thanh toán thành công.',
                'booking_code': reservation.booking_code,
                'payment': serializer.data,
            }
        )


class AdminDashboardAPIView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request):
        total_rooms = Room.objects.count()
        total_categories = RoomCategory.objects.count()
        total_users = User.objects.count()
        total_reservations = Reservation.objects.count()
        active_reservations = Reservation.objects.filter(is_checked_out=False).count()
        paid_reservations = Reservation.objects.filter(payment_status='paid').count()
        total_revenue = Reservation.objects.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        booked_rooms = Reservation.objects.filter(is_checked_out=False).values('room_id').distinct().count()

        return Response(
            {
                'total_rooms': total_rooms,
                'total_categories': total_categories,
                'total_users': total_users,
                'total_reservations': total_reservations,
                'active_reservations': active_reservations,
                'paid_reservations': paid_reservations,
                'booked_rooms': booked_rooms,
                'total_revenue': total_revenue,
            }
        )


class AdminReservationListAPIView(generics.ListAPIView):
    serializer_class = ReservationDetailSerializer
    permission_classes = [IsStaffOrAdmin]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Reservation.objects.select_related('room', 'user').order_by('-created_at')


class AdminCheckedOutReservationListAPIView(generics.ListAPIView):
    serializer_class = ReturnedReservationSerializer
    permission_classes = [IsStaffOrAdmin]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Reservation.objects.select_related('room', 'user', 'coupon').filter(is_checked_out=True)
        room_id = self.request.query_params.get('room_id')
        user_id = self.request.query_params.get('user_id')
        if room_id:
            queryset = queryset.filter(room_id=room_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset.order_by('-created_at')


class AdminRoomListAPIView(generics.ListAPIView):
    serializer_class = RoomSerializer
    permission_classes = [IsStaffOrAdmin]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Room.objects.all().order_by('id')


class RoomImageUploadAPIView(APIView):
    permission_classes = [IsStaffOrAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        room_id = request.data.get('room_id')
        if not room_id:
            return Response({'error': 'Thiếu room_id.'}, status=status.HTTP_400_BAD_REQUEST)

        room = get_object_or_404(Room, id=room_id)
        images = request.FILES.getlist('images')

        if not images:
            return Response({'error': 'Vui lòng chọn ít nhất 1 ảnh.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(images) > 10:
            return Response({'error': 'Chỉ được upload tối đa 10 ảnh/lần.'}, status=status.HTTP_400_BAD_REQUEST)

        created_records = []

        try:
            with transaction.atomic():
                for image in images:
                    ext = validate_image_file(image)
                    image.name = build_safe_filename(ext)
                    created_records.append(RoomImage.objects.create(room=room, image=image))
        except DjangoValidationError as exc:
            for record in created_records:
                record.delete()
            return Response({'error': str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            for record in created_records:
                record.delete()
            return Response({'error': 'Upload thất bại. File đã được rollback.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'message': 'Upload ảnh phòng thành công.',
                'room_id': room.id,
                'images': [{'id': item.id, 'url': item.image.url} for item in created_records],
            },
            status=status.HTTP_201_CREATED,
        )


def _send_booking_confirmation_email(reservation, reason='created'):
    if not reservation.email:
        return False

    guest_name = ' '.join(part for part in [reservation.first_name, reservation.last_name] if part).strip()
    if not guest_name:
        guest_name = 'Quy khach'

    check_in_display = reservation.check_in_date.strftime('%d/%m/%Y') if reservation.check_in_date else ''
    check_out_display = reservation.check_out_date.strftime('%d/%m/%Y') if reservation.check_out_date else ''
    payment_label = reservation.get_payment_method_display() if hasattr(reservation, 'get_payment_method_display') else reservation.payment_method
    booking_code = reservation.booking_code or f'BK{reservation.id:06d}'

    if reason == 'paid':
        subject = f'Xác nhận thanh toán và đặt phòng {booking_code}'
        if reservation.payment_method == 'momo_qr' or reservation.deposit_paid_via_qr > 0:
            intro = 'Giao dịch chuyển khoản của bạn đã được ghi nhận thành công.'
        else:
            intro = 'Thanh toán của bạn đã được ghi nhận thành công.'
    else:
        subject = f'Xác nhận đặt phòng {booking_code}'
        intro = 'Chúng tôi đã nhận được yêu cầu đặt phòng của bạn.'

    body = (
        f'Xin chào {guest_name},\n\n'
        f'{intro}\n'
        f'Mã booking: {booking_code}\n'
        f'Phòng: {reservation.room.name}\n'
        f'Ngày nhận phòng: {check_in_display}\n'
        f'Giờ check-in mặc định: {DEFAULT_CHECK_IN_TIME}\n'
        f'Ngày trả phòng: {check_out_display}\n'
        f'Giờ check-out mặc định: {DEFAULT_CHECK_OUT_TIME}\n'
        f'Số khách: {(reservation.adults or 0) + (reservation.children or 0)}\n'
        f'Tổng tiền: {reservation.total}\n'
        f'Số tiền cọc khi đặt phòng: {reservation.deposit_amount}\n'
        f'Số tiền còn lại cần thanh toán khi check-in: {reservation.balance_due}\n'
        f'Hình thức thanh toán: {payment_label}\n'
        f'Trạng thái thanh toán: {reservation.payment_status}\n'
    )

    if reason == 'paid' and (reservation.payment_method == 'momo_qr' or reservation.deposit_paid_via_qr > 0):
        body += (
            '\nNếu bạn vừa quét mã QR và chuyển khoản, vui lòng kiểm tra email này như thông báo xác nhận từ khách sạn. '
            'Nếu còn số tiền phải thu, phần còn lại sẽ được thanh toán tại quầy check-in.\n'
        )

    if reservation.coupon:
        body += f'Mã ưu đãi: {reservation.coupon.code}\n'

    body += (
        '\nKhi check-out, nếu nhân viên ghi nhận hư hỏng phòng, hệ thống sẽ cộng thêm 10% trên bill hiện tại.\n'
        '\nNếu bạn cần hỗ trợ thêm, vui lòng phản hồi email này hoặc liên hệ lễ tân.\n\n'
        'Trân trọng,\n'
        'Khách sạn'
    )

    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [reservation.email], fail_silently=True)
        return True
    except Exception:
        logger.warning('Không thể gửi email xác nhận cho booking %s', booking_code)
        return False


def _send_invoice_email(reservation):
    """Gửi hóa đơn chi tiết cho khách hàng khi lễ tân in phiếu"""
    if not reservation.email:
        return False

    guest_name = ' '.join(part for part in [reservation.first_name, reservation.last_name] if part).strip()
    if not guest_name:
        guest_name = 'Quy khach'

    booking_code = reservation.booking_code or f'BK{reservation.id:06d}'
    num_nights = (reservation.check_out_date - reservation.check_in_date).days
    if num_nights <= 0:
        num_nights = 1

    check_in_display = reservation.check_in_date.strftime('%d/%m/%Y') if reservation.check_in_date else ''
    check_out_display = reservation.check_out_date.strftime('%d/%m/%Y') if reservation.check_out_date else ''
    check_in_time = reservation.checked_in_at.strftime('%d/%m/%Y %H:%M') if reservation.checked_in_at else 'Chưa check-in'

    subject = f'Hóa đơn cập nhật phòng {booking_code} - Khách sạn'
    
    body = (
        f'Xin chào {guest_name},\n\n'
        f'Cảm ơn bạn đã lưu trú tại khách sạn chúng tôi.\n'
        f'Dưới đây là hóa đơn chi tiết đã được cập nhật sau khi check-out:\n\n'
        f'--- THÔNG TIN BOOKING ---\n'
        f'Mã booking: {booking_code}\n'
        f'Tên khách: {guest_name}\n'
        f'Email: {reservation.email}\n'
        f'Điện thoại: {reservation.phone or "Chưa cập nhật"}\n\n'
        f'--- THÔNG TIN PHÒNG ---\n'
        f'Phòng: {reservation.room.name}\n'
        f'Ngày nhận phòng: {check_in_display}\n'
        f'Giờ check-in mặc định: {DEFAULT_CHECK_IN_TIME}\n'
        f'Ngày trả phòng: {check_out_display}\n'
        f'Giờ check-out mặc định: {DEFAULT_CHECK_OUT_TIME}\n'
        f'Số đêm: {num_nights}\n'
        f'Số khách: {(reservation.adults or 0) + (reservation.children or 0)} người\n'
        f'Thời gian check-in thực tế: {check_in_time}\n\n'
        f'--- CHI PHÍ ---\n'
        f'Giá phòng/đêm: ₹{reservation.room.price}\n'
        f'Tổng tiền phòng ({num_nights} đêm): ₹{reservation.subtotal}\n'
        f'Thuế (18%): ₹{reservation.gst}\n'
    )

    if reservation.selected_services.exists():
        body += f'Dịch vụ đã chọn:\n'
        service_total = Decimal('0')
        for service in reservation.selected_services.all():
            body += f'  - {service.name}: ₹{service.price}\n'
            service_total += service.price
        body += f'Tổng dịch vụ: ₹{service_total}\n\n'

    body += (
        f'--- TỔNG THANH TOÁN (ĐÃ CẬP NHẬT) ---\n'
        f'Tổng trước dịch vụ: ₹{reservation.subtotal + reservation.gst}\n'
    )

    if reservation.selected_services.exists():
        service_total = reservation.selected_services.aggregate(Sum('price'))['price__sum'] or Decimal('0')
        body += f'Dịch vụ: ₹{service_total}\n'

    if reservation.damage_fee and reservation.damage_fee > 0:
        body += f'Phí hư hỏng (10%): ₹{reservation.damage_fee}\n'

    body += (
        f'Số tiền cọc đã thanh toán: ₹{reservation.deposit_amount}\n'
        f'Số tiền còn phải thanh toán: ₹{reservation.balance_due}\n'
        f'TỔNG CỘNG: ₹{reservation.final_total}\n\n'
    )

    if reservation.damage_reported and reservation.damage_notes:
        body += f'Ghi chú hư hỏng: {reservation.damage_notes}\n\n'

    body += (
        'Cảm ơn quý khách đã tin tưởng và lưu trú tại khách sạn chúng tôi.\n'
        'Chúc bạn có một ngày tốt lành!\n\n'
        'Trân trọng,\n'
        'Khách sạn'
    )

    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [reservation.email], fail_silently=True)
        reservation.invoice_notified_at = timezone.now()
        reservation.save(update_fields=['invoice_notified_at'])
        logger.info('Gửi hóa đơn email cho booking %s', booking_code)
        return True
    except Exception:
        logger.warning('Không thể gửi hóa đơn email cho booking %s', booking_code)
        return False


def _send_qr_payment_received_email(reservation, amount_received):
    if not reservation.email:
        return False

    guest_name = ' '.join(part for part in [reservation.first_name, reservation.last_name] if part).strip()
    if not guest_name:
        guest_name = 'Quy khach'

    booking_code = reservation.booking_code or f'BK{reservation.id:06d}'
    payment_label = reservation.get_payment_method_display() if hasattr(reservation, 'get_payment_method_display') else reservation.payment_method
    remaining_balance = max(reservation.final_total - amount_received, Decimal('0.00'))

    subject = f'Đã ghi nhận thanh toán MoMo cho booking {booking_code}'
    if amount_received >= reservation.final_total:
        intro = 'Chúng tôi đã ghi nhận bạn thanh toán đầy đủ qua chuyển khoản.'
    else:
        intro = 'Chúng tôi đã ghi nhận khoản thanh toán cọc qua chuyển khoản.'

    body = (
        f'Xin chào {guest_name},\n\n'
        f'{intro}\n'
        f'Mã booking: {booking_code}\n'
        f'Phòng: {reservation.room.name}\n'
        f'Số tiền nhận được: {amount_received}\n'
        f'Tổng tiền booking: {reservation.final_total}\n'
        f'Số tiền còn lại cần thanh toán: {remaining_balance}\n'
        f'Hình thức thanh toán: {payment_label}\n'
    )

    if remaining_balance > 0:
        body += 'Phần còn lại sẽ được thanh toán tại check-in.\n'
    else:
        body += 'Booking của bạn đã được thanh toán đầy đủ.\n'

    body += (
        '\nNếu bạn vừa quét mã và chuyển khoản xong, email này là xác nhận hệ thống đã ghi nhận giao dịch.\n\n'
        'Trân trọng,\n'
        'Khách sạn'
    )

    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [reservation.email], fail_silently=True)
        logger.info('Gửi email xác nhận thanh toán chuyển khoản cho booking %s', booking_code)
        return True
    except Exception:
        logger.warning('Không thể gửi email xác nhận thanh toán chuyển khoản cho booking %s', booking_code)
        return False


def _extract_momo_booking_code(payload):
    candidates = [
        payload.get('booking_code'),
        payload.get('bookingCode'),
        payload.get('orderId'),
        payload.get('order_id'),
        payload.get('orderInfo'),
        payload.get('extraData'),
        payload.get('requestId'),
    ]

    for candidate in candidates:
        if not candidate:
            continue
        value = str(candidate).strip()
        if not value:
            continue
        if 'BK' in value:
            start = value.find('BK')
            token = value[start:]
            for separator in [' ', '&', ',', '|', ';']:
                token = token.split(separator)[0]
            return token
        for separator in ['|', '-', ' ']:
            value = value.split(separator)[0]
        return value
    return ''


class MoMoPaymentWebhookAPIView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        booking_code = _extract_momo_booking_code(payload)
        if not booking_code:
            return Response(
                {'success': False, 'message': 'Không tìm thấy mã booking trong payload.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reservation = _get_reservation_by_booking_code(booking_code)

        result_code = str(payload.get('resultCode', payload.get('result_code', '0'))).strip().lower()
        is_success = result_code in {'0', '00', 'success', 'true'}
        amount_raw = payload.get('amount', payload.get('transAmount', payload.get('payAmount', 0)))

        try:
            amount_received = Decimal(str(amount_raw or '0')).quantize(Decimal('0.01'))
        except Exception:
            return Response(
                {'success': False, 'message': 'Số tiền thanh toán không hợp lệ.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount_received <= 0:
            return Response(
                {'success': False, 'message': 'Số tiền thanh toán phải lớn hơn 0.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not is_success:
            return Response(
                {
                    'success': False,
                    'message': 'Giao dịch chuyển khoản chưa thành công.',
                    'booking_code': reservation.booking_code,
                },
                status=status.HTTP_200_OK,
            )

        recorded_amount = min(amount_received, reservation.final_total)

        if reservation.deposit_paid_via_qr >= recorded_amount and reservation.payment_status == 'paid':
            return Response(
                {
                    'success': True,
                    'message': 'Giao dịch đã được ghi nhận trước đó.',
                    'booking_code': reservation.booking_code,
                    'deposit_paid_via_qr': str(reservation.deposit_paid_via_qr),
                    'payment_status': reservation.payment_status,
                },
                status=status.HTTP_200_OK,
            )

        reservation.deposit_paid_via_qr = recorded_amount
        if amount_received >= reservation.final_total:
            reservation.payment_status = 'paid'
            reservation.balance_paid_at_checkin = Decimal('0.00')
        else:
            reservation.payment_status = 'pending'

        reservation.sync_financial_fields()
        reservation.save(
            update_fields=[
                'deposit_paid_via_qr',
                'balance_paid_at_checkin',
                'payment_status',
                'final_total',
                'deposit_amount',
                'balance_due',
            ]
        )

        transaction.on_commit(
            lambda reservation=reservation, recorded_amount=recorded_amount: _send_qr_payment_received_email(
                reservation,
                recorded_amount,
            )
        )

        response_message = 'Đã ghi nhận thanh toán chuyển khoản.'
        if amount_received >= reservation.final_total:
            response_message = 'Đã ghi nhận thanh toán đầy đủ qua chuyển khoản.'
        else:
            response_message = 'Đã ghi nhận thanh toán cọc qua chuyển khoản. Phần còn lại sẽ thanh toán tại check-in.'

        return Response(
            {
                'success': True,
                'message': response_message,
                'booking_code': reservation.booking_code,
                'amount_received': str(recorded_amount),
                'deposit_paid_via_qr': str(reservation.deposit_paid_via_qr),
                'balance_due': str(reservation.balance_due),
                'payment_status': reservation.payment_status,
            },
            status=status.HTTP_200_OK,
        )


class BankTransferPaymentStatusAPIView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, booking_code):
        reservation = _get_reservation_by_booking_code(booking_code)
        deposit_paid = reservation.deposit_paid_via_qr or Decimal('0.00')
        return Response(
            {
                'success': True,
                'booking_code': reservation.booking_code,
                'deposit_paid_via_qr': str(deposit_paid),
                'final_total': str(reservation.final_total),
                'balance_due': str(reservation.balance_due),
                'payment_status': reservation.payment_status,
                'is_deposit_confirmed': deposit_paid > 0,
                'is_fully_paid': reservation.payment_status == 'paid' or deposit_paid >= reservation.final_total,
            },
            status=status.HTTP_200_OK,
        )


def _send_cancellation_email(reservation):
    if not reservation.email:
        return False

    guest_name = ' '.join(part for part in [reservation.first_name, reservation.last_name] if part).strip()
    if not guest_name:
        guest_name = 'Quy khach'

    booking_code = reservation.booking_code or f'BK{reservation.id:06d}'
    subject = f'Xác nhận hủy booking {booking_code} - Khách sạn'
    body = (
        f'Xin chào {guest_name},\n\n'
        f'Chúng tôi xác nhận booking {booking_code} đã được hủy thành công.\n'
        f'Tiền cọc của bạn sẽ bị giữ lại theo chính sách áp dụng.\n\n'
        f'Nếu cần hỗ trợ thêm, vui lòng liên hệ lễ tân của khách sạn.\n\n'
        f'Trân trọng,\n'
        f'Khách sạn'
    )

    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [reservation.email], fail_silently=True)
        logger.info('Gửi email xác nhận hủy booking %s', booking_code)
        return True
    except Exception:
        logger.warning('Không thể gửi email xác nhận hủy booking %s', booking_code)
        return False


class AdminServiceListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsStaffOrAdmin]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Service.objects.all().order_by('order', 'name')
        active = self.request.query_params.get('active')
        if active in {'true', 'false'}:
            queryset = queryset.filter(active=(active == 'true'))
        return queryset


class AdminServiceDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsStaffOrAdmin]
    lookup_field = 'id'

    def get_queryset(self):
        return Service.objects.all()


def _parse_selected_services(request):
    service_ids = request.POST.getlist('service_ids')
    if not service_ids:
        return Service.objects.none(), Decimal('0.00')

    selected_services = Service.objects.filter(id__in=service_ids, active=True).order_by('order', 'name')
    service_total = sum((service.price for service in selected_services), Decimal('0.00'))
    return selected_services, service_total


def _build_booking_payload(room, check_in, check_out):
    check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
    check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()

    if check_in_date < date.today():
        raise ValueError('Check-in date cannot be in the past.')
    if check_out_date <= check_in_date:
        raise ValueError('Check-out date must be after check-in date.')

    num_nights = (check_out_date - check_in_date).days
    subtotal = room.price * num_nights
    gst = subtotal * Decimal('0.18')
    return {
        'check_in_date': check_in_date,
        'check_out_date': check_out_date,
        'num_nights': num_nights,
        'subtotal': subtotal,
        'gst': gst,
    }


def _guest_capacity_error(room, adults, children=0):
    try:
        adults = int(adults or 0)
    except (TypeError, ValueError):
        adults = 0
    try:
        children = int(children or 0)
    except (TypeError, ValueError):
        children = 0

    if room.can_accommodate(adults=adults, children=children):
        return ''

    errors = []
    if adults > room.capacity_adults:
        errors.append(f'Vượt số người lớn: tối đa {room.capacity_adults}, bạn chọn {adults}.')
    if children > room.capacity_children:
        errors.append(f'Vượt số trẻ em: tối đa {room.capacity_children}, bạn chọn {children}.')

    total_guests = adults + children
    if total_guests > room.total_capacity:
        errors.append(f'Vượt tổng số khách: tối đa {room.total_capacity}, bạn chọn {total_guests}.')

    if errors:
        return ' '.join(errors)

    return (
        f'Phòng này chỉ nhận tối đa {room.total_capacity} khách '
        f'({room.capacity_adults} người lớn, {room.capacity_children} trẻ em).'
    )


def room_list(request):
    category_name = request.GET.get('category', 'all').lower()
    categories = RoomCategory.objects.all()
    if category_name == 'all':
        rooms = Room.objects.all()
    else:
        rooms = Room.objects.filter(category__name__iexact=category_name)

    return render(
        request,
        'rooms/rooms.html',
        {
            'rooms': rooms,
            'categories': categories,
            'selected_category': category_name,
        },
    )


def room_detail(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    similar_rooms = Room.objects.exclude(id=room_id)
    feedback_form = FeedbackForm(user=request.user)
    return render(
        request,
        'rooms/roomdetail.html',
        {
            'room': room,
            'similar_rooms': similar_rooms,
            'feedback_form': feedback_form,
        },
    )


def service_list(request):
    services = Service.objects.filter(active=True).order_by('order', 'name')
    return render(request, 'rooms/services.html', {'services': services, 'page_title': 'Dịch vụ khách sạn'})


def service_detail(request, slug):
    service = get_object_or_404(Service, slug=slug, active=True)
    related_services = Service.objects.filter(active=True).exclude(id=service.id).order_by('order', 'name')[:3]
    return render(request, 'rooms/service_detail.html', {'service': service, 'related_services': related_services})


@login_required
def service_selection(request):
    if request.method != 'POST':
        return redirect('rooms:room_list')

    room_id = request.POST.get('room_id')
    check_in = request.POST.get('check_in')
    check_out = request.POST.get('check_out')
    adults = request.POST.get('adults', '1')
    children = request.POST.get('children', '0')

    if not room_id or not check_in or not check_out:
        messages.error(request, 'Vui lòng chọn lại thông tin phòng và ngày nhận/trả phòng.')
        return redirect('rooms:room_list')

    room = get_object_or_404(Room, id=room_id)
    try:
        booking_payload = _build_booking_payload(room, check_in, check_out)
        adults = int(adults)
        children = int(children)
    except (ValueError, TypeError):
        messages.error(request, 'Thông tin đặt phòng không hợp lệ.')
        return redirect('rooms:room_detail', room_id=room.id)

    capacity_error = _guest_capacity_error(room, adults=adults, children=children)
    if capacity_error:
        messages.error(request, capacity_error)
        return redirect('rooms:room_detail', room_id=room.id)

    services = Service.objects.filter(active=True).order_by('order', 'name')
    return render(
        request,
        'rooms/services.html',
        {
            'room': room,
            'services': services,
            'check_in': check_in,
            'check_out': check_out,
            'adults': adults,
            'children': children,
            'num_nights': booking_payload['num_nights'],
            'subtotal': booking_payload['subtotal'],
            'gst': booking_payload['gst'],
        },
    )


def room_list_filtered(request):
    check_in = request.GET.get('check_in')
    check_out = request.GET.get('check_out')
    adults = request.GET.get('adults', '1')
    children = request.GET.get('children', '0')

    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        adults = int(adults)
        children = int(children)
        if check_in_date < date.today() or check_out_date <= check_in_date or adults <= 0:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, 'Invalid search parameters.')
        return redirect('home')

    suitable_rooms = Room.objects.search_suitable_rooms(
        check_in=check_in_date,
        check_out=check_out_date,
        adults=adults,
        children=children,
        limit=None,
    )

    recommended_combos = Room.objects.recommend_room_combinations(
        check_in=check_in_date,
        check_out=check_out_date,
        adults=adults,
        children=children,
        max_rooms=2,
        limit=3,
    )

    return render(
        request,
        'rooms/roomsfilter.html',
        {
            'rooms': suitable_rooms,
            'recommended_combos': recommended_combos,
            'check_in': check_in,
            'check_out': check_out,
            'adults': adults,
            'children': children,
            'total_guests': adults + children,
            'num_nights': (check_out_date - check_in_date).days,
        },
    )


def room_combo_detail(request):
    room_ids_raw = request.GET.get('room_ids', '')
    room_ids = []

    try:
        room_ids = [int(room_id.strip()) for room_id in room_ids_raw.split(',') if room_id.strip()]
    except ValueError:
        room_ids = []

    if len(room_ids) < 2:
        messages.error(request, 'Vui lòng chọn đủ 2 phòng để xem phương án ghép.')
        return redirect('rooms:room_list')

    room_map = {room.id: room for room in Room.objects.filter(id__in=room_ids)}
    combo_rooms = [room_map[room_id] for room_id in room_ids if room_id in room_map]

    if len(combo_rooms) < 2:
        messages.error(request, 'Không tìm thấy đủ phòng để hiển thị phương án ghép.')
        return redirect('rooms:room_list')

    check_in = request.GET.get('check_in')
    check_out = request.GET.get('check_out')
    adults = request.GET.get('adults')
    children = request.GET.get('children', '0')
    num_nights = None

    try:
        if check_in and check_out:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            if check_out_date > check_in_date:
                num_nights = (check_out_date - check_in_date).days
    except ValueError:
        pass

    total_capacity = sum(room.total_capacity or room.capacity for room in combo_rooms)
    total_price_per_night = sum(room.price for room in combo_rooms)
    total_stay_price = total_price_per_night * num_nights if num_nights else None

    return render(
        request,
        'rooms/room_combo_detail.html',
        {
            'combo_rooms': combo_rooms,
            'total_capacity': total_capacity,
            'total_price_per_night': total_price_per_night,
            'total_stay_price': total_stay_price,
            'check_in': check_in,
            'check_out': check_out,
            'adults': adults,
            'children': children,
            'num_nights': num_nights,
        },
    )


@login_required
def room_search(request):
    if request.method == 'GET':
        room_id = request.GET.get('room_id')
        check_in = request.GET.get('check_in')
        check_out = request.GET.get('check_out')
        adults = request.GET.get('adults')
        children = request.GET.get('children', 0)

        if not check_in or not check_out or not adults:
            messages.error(request, 'Vui lòng chọn ngày nhận phòng, ngày trả phòng và số người lớn.')
            return redirect('rooms:room_detail', room_id=room_id)

        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            adults = int(adults)
            children = int(children)
            total_guests = adults + children
            if adults <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Thông tin ngày hoặc số lượng khách không hợp lệ.')
            return redirect('rooms:room_detail', room_id=room_id)

        if check_in_date < date.today():
            messages.error(request, 'Ngày check-in không được nhỏ hơn hôm nay.')
            return redirect('rooms:room_detail', room_id=room_id)

        if check_out_date <= check_in_date:
            messages.error(request, 'Ngày check-out phải sau ngày check-in.')
            return redirect('rooms:room_detail', room_id=room_id)

        selected_room = get_object_or_404(Room, id=room_id)
        capacity_error_detail = ''
        if not selected_room.can_accommodate(adults=adults, children=children):
            is_available = False
            capacity_exceeded = True
            capacity_error_detail = _guest_capacity_error(selected_room, adults=adults, children=children)
        else:
            capacity_exceeded = False
            is_available = selected_room.is_available(check_in_date, check_out_date)

        available_rooms = Room.objects.available_rooms(check_in_date, check_out_date, total_guests)
        other_available_rooms = available_rooms.exclude(id=selected_room.id)
        suitable_rooms = Room.objects.search_suitable_rooms(
            check_in=check_in_date,
            check_out=check_out_date,
            adults=adults,
            children=children,
            limit=None,
        )
        recommended_combos = Room.objects.recommend_room_combinations(
            check_in=check_in_date,
            check_out=check_out_date,
            adults=adults,
            children=children,
            max_rooms=2,
            limit=3,
        )

        return render(
            request,
            'rooms/roomsearch.html',
            {
                'selected_room': selected_room,
                'is_available': is_available,
                'capacity_exceeded': capacity_exceeded,
                'capacity_error_detail': capacity_error_detail,
                'other_available_rooms': other_available_rooms,
                'suitable_rooms': suitable_rooms,
                'recommended_combos': recommended_combos,
                'check_in': check_in,
                'check_out': check_out,
                'adults': adults,
                'children': children,
                'total_guests': total_guests,
            },
        )

    return redirect('rooms:room_list')


@login_required
def room_booking(request):
    if request.method != 'POST':
        return redirect('rooms:room_list')

    room_id = request.POST.get('room_id')
    check_in = request.POST.get('check_in')
    check_out = request.POST.get('check_out')
    adults_raw = request.POST.get('adults', 1)
    children_raw = request.POST.get('children', 0)
    coupon_code = request.POST.get('coupon_code', '').strip()
    payment_method = _normalize_payment_method(request.POST.get('mphb_gateway_id', 'cash'))
    selected_services, service_total = _parse_selected_services(request)

    try:
        room = get_object_or_404(Room, id=room_id)
        booking_payload = _build_booking_payload(room, check_in, check_out)
        adults = int(adults_raw)
        children = int(children_raw)
        check_in_date = booking_payload['check_in_date']
        check_out_date = booking_payload['check_out_date']
        num_nights = booking_payload['num_nights']
    except (ValueError, TypeError):
        messages.error(request, 'Thông tin ngày hoặc số lượng khách không hợp lệ.')
        return redirect('rooms:room_list')

    capacity_error = _guest_capacity_error(room, adults=adults, children=children)
    if capacity_error:
        messages.error(request, capacity_error)
        return redirect('rooms:room_detail', room_id=room.id)

    subtotal = booking_payload['subtotal']
    gst = booking_payload['gst']
    discount = Decimal('0.00')
    coupon = None

    if coupon_code:
        try:
            coupon = Coupon.objects.get(
                code=coupon_code,
                active=True,
                valid_from__lte=date.today(),
                valid_to__gte=date.today(),
            )
            discount = (subtotal * coupon.discount_percentage) / Decimal('100')
            if 'apply_coupon' in request.POST:
                messages.success(request, f'Coupon "{coupon_code}" applied! You saved ₹{discount}')
        except Coupon.DoesNotExist:
            if 'apply_coupon' in request.POST:
                messages.error(request, 'Invalid or expired coupon code.')
                coupon_code = ''
                coupon = None

    total = subtotal + gst + service_total - discount
    form = BookingForm(request.POST or None)

    if 'book_now' in request.POST:
        if form.is_valid():
            if not room.is_available(check_in_date, check_out_date):
                messages.error(request, 'Sorry, this room was just booked by someone else for these dates.')
                return redirect('rooms:room_list')

            try:
                with transaction.atomic():
                    reservation = form.save(commit=False)
                    reservation.room = room
                    reservation.user = request.user if request.user.is_authenticated else None
                    reservation.check_in_date = check_in_date
                    reservation.check_out_date = check_out_date
                    reservation.adults = adults
                    reservation.children = children
                    reservation.subtotal = subtotal
                    reservation.gst = gst
                    reservation.discount_applied = discount
                    reservation.service_total = service_total
                    reservation.total = total
                    reservation.coupon = coupon
                    reservation.payment_method = payment_method
                    reservation.sync_financial_fields()
                    reservation.save()

                    if selected_services.exists():
                        reservation.selected_services.set(selected_services)

                transaction.on_commit(
                    lambda reservation=reservation: _send_booking_confirmation_email(reservation, reason='created')
                )

                messages.success(request, f'Booking successful! Mã đặt phòng của bạn là {reservation.booking_code}.')
                return redirect('rooms:booking_confirmation', reservation_id=reservation.id)
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors in the form below.')

    return render(
        request,
        'rooms/roombooking.html',
        {
            'form': form,
            'room': room,
            'check_in': check_in,
            'check_out': check_out,
            'adults': adults,
            'children': children,
            'num_nights': num_nights,
            'subtotal': subtotal,
            'gst': gst,
            'service_total': service_total,
            'discount': discount,
            'total': total,
            'deposit_amount': total * Decimal('0.30'),
            'balance_due': total * Decimal('0.70'),
            'coupon_code': coupon_code,
            'selected_services': selected_services,
        },
    )


@ensure_csrf_cookie
def booking_confirmation(request, reservation_id):
    reservation = get_object_or_404(
        Reservation.objects.select_related('room', 'user', 'coupon').prefetch_related('selected_services'),
        id=reservation_id,
    )
    context = _build_reservation_invoice_context(reservation)
    context['can_print_frontdesk_slip'] = _has_admin_booking_access(request.user)
    return render(request, 'rooms/bookingconfirmation.html', context)


@login_required
def frontdesk_print_slip(request, booking_code):
    if not _has_admin_booking_access(request.user):
        messages.error(request, 'Bạn không có quyền truy cập phiếu in lễ tân.')
        return redirect('home')

    reservation = _get_reservation_by_booking_code(booking_code)
    context = _build_reservation_invoice_context(reservation)
    context['printed_at'] = datetime.now()
    
    email_sent = _send_invoice_email(reservation)
    if email_sent:
        messages.success(request, f'Hóa đơn đã được gửi tới email của khách: {reservation.email}')
    else:
        messages.warning(request, f'Không thể gửi email hóa đơn cho khách (email: {reservation.email}). Vui lòng kiểm tra email khách hàng.')
    
    return render(request, 'rooms/frontdesk_print_slip.html', context)


@login_required
def my_bookings(request):
    bookings = (
        Reservation.objects.filter(user=request.user)
        .select_related('room')
        .prefetch_related('selected_services')
        .order_by('-created_at')
    )
    return render(request, 'rooms/mybookings.html', {'bookings': bookings})


@login_required
def cancel_reservation(request, reservation_id):
    if request.method != 'POST':
        return redirect('rooms:my_bookings')

    reservation = get_object_or_404(
        Reservation.objects.select_related('room'),
        id=reservation_id,
        user=request.user,
    )

    if reservation.is_checked_out:
        messages.error(request, 'Booking này đã check-out hoặc đã được hủy trước đó.')
        return redirect('rooms:my_bookings')

    if not reservation.can_cancel_online:
        messages.error(request, 'Chỉ có thể hủy đến hết ngày check-in. Sau ngày check-in sẽ không được hủy và tiền cọc bị mất.')
        return redirect('rooms:my_bookings')

    cancelled_at = timezone.now()
    cancellation_note = (
        f"[CANCELLED {cancelled_at.strftime('%d/%m/%Y %H:%M')}] "
        f"Khách hủy phòng. Mất cọc: {reservation.deposit_amount}."
    )

    reservation.is_checked_out = True
    reservation.checkout_at = cancelled_at
    reservation.damage_reported = False
    reservation.damage_notes = ''
    reservation.damage_fee = Decimal('0.00')
    reservation.balance_due = Decimal('0.00')
    reservation.final_total = reservation.deposit_amount
    reservation.note = f"{(reservation.note or '').strip()}\n{cancellation_note}".strip()
    reservation.save(
        update_fields=[
            'is_checked_out',
            'checkout_at',
            'damage_reported',
            'damage_notes',
            'damage_fee',
            'balance_due',
            'final_total',
            'note',
        ]
    )

    if reservation.email:
        transaction.on_commit(lambda reservation=reservation: _send_cancellation_email(reservation))

    messages.success(
        request,
        f'Đã hủy phòng thành công cho booking {reservation.booking_code}. Tiền cọc {reservation.deposit_amount} được giữ lại và không hoàn lại.',
    )
    return redirect('rooms:my_bookings')


def home(request):
    rooms = Room.objects.all()
    blogs = Blog.objects.all()
    feedbacks = Feedback.objects.all().order_by('created_at')[:3]
    featured_services = Service.objects.filter(active=True).order_by('order', 'name')[:4]

    return render(
        request,
        'index.html',
        {
            'rooms': rooms,
            'blogs': blogs,
            'feedbacks': feedbacks,
            'featured_services': featured_services,
        },
    )


def about_page(request):
    return render(request, 'about.html')


@login_required
def book_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    today = date.today()
    default_check_in = today
    default_check_out = today + timedelta(days=1)
    default_adults = 1

    check_in = default_check_in.strftime('%Y-%m-%d')
    check_out = default_check_out.strftime('%Y-%m-%d')
    adults = default_adults

    if request.method == 'POST':
        check_in = request.POST.get('check_in') or check_in
        check_out = request.POST.get('check_out') or check_out
        adults = request.POST.get('adults') or adults
        form = BookingForm(request.POST)
        if form.is_valid():
            try:
                check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
                check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
                adults = int(adults)
            except (ValueError, TypeError):
                messages.error(request, 'Invalid booking dates or guest count.')
                return redirect('rooms:room_detail', room_id=room_id)

            capacity_error = _guest_capacity_error(room, adults=adults, children=0)
            if capacity_error:
                messages.error(request, capacity_error)
                return redirect('rooms:room_detail', room_id=room_id)

            if check_in_date < today:
                messages.error(request, 'Ngày nhận phòng không được nhỏ hơn hôm nay.')
                return redirect('rooms:room_detail', room_id=room_id)

            num_nights = (check_out_date - check_in_date).days
            if num_nights <= 0:
                messages.error(request, 'Check-out date must be after check-in date.')
                return redirect('rooms:room_detail', room_id=room_id)

            subtotal = room.price * num_nights
            gst = subtotal * Decimal('0.18')
            total = subtotal + gst

            if not room.is_available(check_in_date, check_out_date):
                messages.error(request, 'The room is no longer available.')
                return redirect('rooms:room_detail', room_id=room_id)

            reservation = form.save(commit=False)
            reservation.room = room
            reservation.user = request.user
            reservation.check_in_date = check_in_date
            reservation.check_out_date = check_out_date
            reservation.adults = adults
            reservation.subtotal = subtotal
            reservation.gst = gst
            reservation.total = total
            reservation.sync_financial_fields()
            reservation.save()

            transaction.on_commit(
                lambda reservation=reservation: _send_booking_confirmation_email(reservation, reason='created')
            )

            messages.success(request, f'Booking successful! Mã đặt phòng của bạn là {reservation.booking_code}.')
            return redirect('rooms:booking_confirmation', reservation_id=reservation.id)
    else:
        form = BookingForm()

    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        adults = int(adults)
    except (ValueError, TypeError):
        check_in_date = default_check_in
        check_out_date = default_check_out
        adults = default_adults

    num_nights = max(1, (check_out_date - check_in_date).days)
    subtotal = room.price * num_nights
    gst = subtotal * Decimal('0.18')
    total = subtotal + gst

    return render(
        request,
        'rooms/roombooking.html',
        {
            'form': form,
            'room': room,
            'check_in': check_in_date.strftime('%Y-%m-%d'),
            'check_out': check_out_date.strftime('%Y-%m-%d'),
            'adults': adults,
            'num_nights': num_nights,
            'subtotal': subtotal,
            'gst': gst,
            'total': total,
            'deposit_amount': total * Decimal('0.30'),
            'balance_due': total * Decimal('0.70'),
            'coupon_code': '',
        },
    )


def check_room_availability_api(request):
    room_id = request.GET.get('id')
    check_in = request.GET.get('in')
    check_out = request.GET.get('out')

    is_booked = Reservation.objects.filter(
        room_id=room_id,
        check_in_date__lt=check_out,
        check_out_date__gt=check_in,
        is_checked_out=False,
    ).exists()
    return JsonResponse({'is_available': not is_booked})

@login_required(login_url='accounts:login_page')
def checkout_reservation(request, reservation_id):
    if request.method != 'POST':
        return redirect('rooms:room_list')

    reservation = get_object_or_404(Reservation, id=reservation_id)

    # Check if user has permission (customer can only checkout their own, staff can checkout any)
    if not (request.user.is_staff or reservation.user_id == request.user.id):
        messages.error(request, 'Bạn không có quyền thực hiện hành động này.')
        return redirect('rooms:booking_confirmation', reservation_id=reservation.id)

    if not reservation.is_checked_in:
        messages.error(request, 'Booking chưa check-in nên chưa thể check-out.')
        return redirect('rooms:booking_confirmation', reservation_id=reservation.id)

    damage_reported = request.POST.get('damage_reported') in {'1', 'true', 'True', 'on'}
    damage_notes = (request.POST.get('damage_notes') or '').strip()
    is_early_checkout = date.today() < reservation.check_out_date

    reservation.is_checked_out = True
    if not reservation.checkout_at:
        reservation.checkout_at = datetime.now()
    reservation.damage_reported = damage_reported
    reservation.damage_notes = damage_notes
    reservation.sync_financial_fields()
    reservation.save(
        update_fields=[
            'is_checked_out',
            'checkout_at',
            'damage_reported',
            'damage_notes',
            'damage_fee',
            'final_total',
            'deposit_amount',
            'balance_due',
        ]
    )

    if reservation.email:
        transaction.on_commit(lambda reservation=reservation: _send_invoice_email(reservation))
    else:
        messages.warning(request, 'Khách chưa có email nên chưa thể gửi thông báo hóa đơn tự động.')

    if reservation.damage_reported:
        base_message = (
            f'Đã trả phòng {reservation.room.name}. Có phát sinh phụ phí hư hỏng 10%: '
            f'{reservation.damage_fee}. Tổng thanh toán cuối: {reservation.final_total}.'
        )
        if is_early_checkout:
            base_message += ' Đây là trả phòng sớm, hóa đơn vẫn tính theo booking ban đầu.'
        if reservation.email:
            base_message += ' Hóa đơn đã được cập nhật và gửi vào email của khách.'
        messages.success(
            request,
            base_message,
        )
    else:
        if is_early_checkout:
            checkout_message = (
                f'Đã trả phòng sớm cho {reservation.room.name}. Hóa đơn vẫn giữ theo booking ban đầu: '
                f'{reservation.final_total}.'
            )
            if reservation.email:
                checkout_message += ' Hóa đơn đã được cập nhật và gửi vào email của khách.'
            messages.success(
                request,
                checkout_message,
            )
        else:
            checkout_message = f'Đã trả phòng {reservation.room.name} thành công!'
            if reservation.email:
                checkout_message += ' Hóa đơn đã được cập nhật và gửi vào email của khách.'
            messages.success(request, checkout_message)
    
    # Redirect to feedback page after successful checkout
    return redirect('feedback:feedback_after_checkout', reservation_id=reservation.id)



@login_required(login_url='accounts:login_page')
def admin_room_image_upload_page(request):
    if not request.user.is_staff:
        messages.error(request, 'Bạn không có quyền truy cập trang này.')
        return redirect('home')

    rooms = Room.objects.all().order_by('name')
    return render(request, 'rooms/admin_room_image_upload.html', {'rooms': rooms})


def room_catalog_page(request):
    categories = RoomCategory.objects.all().order_by('name')
    return render(request, 'rooms/room_catalog_api.html', {'categories': categories})
