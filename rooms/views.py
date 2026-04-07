from datetime import date, datetime, timedelta
from decimal import Decimal

from blog.models import Blog
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Avg, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from feedback.forms import FeedbackForm
from feedback.models import Feedback
from rest_framework import generics, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import BookingForm
from .models import Coupon, Reservation, Room, RoomCategory, RoomImage, Service
from .serializers import (
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
from .upload_security import build_safe_filename, validate_image_file


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


class ReservationCheckoutAPIView(generics.UpdateAPIView):
    serializer_class = ReservationCheckoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user)

    def get_object(self):
        reservation = super().get_object()
        if reservation.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied('Không có quyền truy cập đặt phòng này.')
        return reservation

    def update(self, request, *args, **kwargs):
        reservation = self.get_object()

        if reservation.is_checked_out:
            return Response({'error': 'Phòng này đã được trả rồi.'}, status=status.HTTP_400_BAD_REQUEST)

        if date.today() < reservation.check_out_date:
            return Response(
                {'error': f'Chưa đến ngày trả phòng ({reservation.check_out_date}). Vui lòng quay lại vào ngày hết hạn.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(reservation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                'success': True,
                'message': f'Trả phòng {reservation.room.name} thành công!',
                'reservation': serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ReservationDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ReservationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user)


class ReservationListAPIView(generics.ListAPIView):
    serializer_class = ReservationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user).order_by('-created_at')


class ReservationCheckedOutListAPIView(generics.ListAPIView):
    serializer_class = ReservationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        base_queryset = Reservation.objects.filter(is_checked_out=True)
        if self.request.user.is_staff:
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
                'message': f'Tìm thấy {len(rooms_data)} phòng phù hợp cho {total_guests} khách.',
            },
            status=status.HTTP_200_OK,
        )


class ReservationPaymentAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = ReservationPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        if self.request.user.is_staff:
            return Reservation.objects.all().order_by('-created_at')
        return Reservation.objects.filter(user=self.request.user).order_by('-created_at')

    def update(self, request, *args, **kwargs):
        reservation = self.get_object()
        serializer = self.get_serializer(reservation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'message': 'Cập nhật thanh toán thành công.', 'payment': serializer.data})


class AdminDashboardAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

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
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Reservation.objects.select_related('room', 'user').order_by('-created_at')


class AdminCheckedOutReservationListAPIView(generics.ListAPIView):
    serializer_class = ReturnedReservationSerializer
    permission_classes = [permissions.IsAdminUser]
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
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Room.objects.all().order_by('id')


class RoomImageUploadAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]
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


class AdminServiceListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Service.objects.all().order_by('order', 'name')
        active = self.request.query_params.get('active')
        if active in {'true', 'false'}:
            queryset = queryset.filter(active=(active == 'true'))
        return queryset


class AdminServiceDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAdminUser]
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

    return render(
        request,
        'rooms/roomsfilter.html',
        {
            'rooms': suitable_rooms,
            'check_in': check_in,
            'check_out': check_out,
            'adults': adults,
            'children': children,
            'total_guests': adults + children,
            'num_nights': (check_out_date - check_in_date).days,
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
        if total_guests > selected_room.capacity:
            is_available = False
            capacity_exceeded = True
        else:
            capacity_exceeded = False
            is_available = selected_room.is_available(check_in_date, check_out_date)

        available_rooms = Room.objects.available_rooms(check_in_date, check_out_date, total_guests)
        other_available_rooms = available_rooms.exclude(id=selected_room.id)

        return render(
            request,
            'rooms/roomsearch.html',
            {
                'selected_room': selected_room,
                'is_available': is_available,
                'capacity_exceeded': capacity_exceeded,
                'other_available_rooms': other_available_rooms,
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
    adults = int(request.POST.get('adults', 1))
    children = int(request.POST.get('children', 0))
    coupon_code = request.POST.get('coupon_code', '').strip()
    payment_method = request.POST.get('mphb_gateway_id', 'pay_on_arrival')
    selected_services, service_total = _parse_selected_services(request)

    try:
        room = get_object_or_404(Room, id=room_id)
        booking_payload = _build_booking_payload(room, check_in, check_out)
        check_in_date = booking_payload['check_in_date']
        check_out_date = booking_payload['check_out_date']
        num_nights = booking_payload['num_nights']
    except (ValueError, TypeError):
        messages.error(request, 'Invalid date format.')
        return redirect('rooms:room_list')

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
                    reservation.save()

                    if selected_services.exists():
                        reservation.selected_services.set(selected_services)

                messages.success(request, 'Booking successful! We are looking forward to seeing you.')
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
            'coupon_code': coupon_code,
            'selected_services': selected_services,
        },
    )


def booking_confirmation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    num_nights = (reservation.check_out_date - reservation.check_in_date).days
    if num_nights <= 0:
        num_nights = 1

    return render(request, 'rooms/bookingconfirmation.html', {'reservation': reservation, 'num_nights': num_nights})


@login_required
def my_bookings(request):
    bookings = (
        Reservation.objects.filter(user=request.user)
        .select_related('room')
        .prefetch_related('selected_services')
        .order_by('-created_at')
    )
    return render(request, 'rooms/mybookings.html', {'bookings': bookings})


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
            reservation.save()

            messages.success(request, 'Booking successful! Welcome!')
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

def checkout_reservation(request, reservation_id):
    if request.method != 'POST':
        return redirect('rooms:room_list')

    reservation = get_object_or_404(Reservation, id=reservation_id)
    reservation.is_checked_out = True
    reservation.save(update_fields=['is_checked_out'])

    messages.success(request, f'Đã trả phòng {reservation.room.name} thành công!')
    return redirect('rooms:room_list')


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
