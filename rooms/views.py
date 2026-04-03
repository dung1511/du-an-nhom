from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from urllib3 import request
from .models import Room, RoomCategory, Reservation , Coupon
from .forms import BookingForm
from feedback.forms import FeedbackForm
from blog.models import Blog
from feedback.models import Feedback
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.contrib import messages
from django.db import transaction

def room_list(request):
    category_name = request.GET.get('category', 'all').lower()
    categories = RoomCategory.objects.all()
    
    if category_name == 'all':
        rooms = Room.objects.all()
    else:
        rooms = Room.objects.filter(category__name__iexact=category_name)
    
    context = {
        'rooms': rooms,
        'categories': categories,
        'selected_category': category_name,
    }
    return render(request, 'rooms/rooms.html', context)

def room_detail(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    similar_rooms = Room.objects.exclude(id=room_id)
    feedback_form = FeedbackForm(user=request.user)
    
    context = {
        'room': room,
        'similar_rooms': similar_rooms,
        'feedback_form': feedback_form,
    }
    return render(request, 'rooms/roomdetail.html', context)



def room_list_filtered(request):
    check_in = request.GET.get('check_in')
    check_out = request.GET.get('check_out')
    adults = request.GET.get('adults', '1')

    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        adults = int(adults)
        if check_in_date < date.today() or check_out_date <= check_in_date or adults <= 0:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, 'Invalid search parameters.')
        return redirect('home')

    available_rooms = Room.objects.available_rooms(check_in_date, check_out_date, adults)

    context = {
        'rooms': available_rooms,
        'check_in': check_in,
        'check_out': check_out,
        'adults': adults,
        }
    return render(request, 'rooms/roomsfilter.html', context)

@login_required
def room_search(request):
    if request.method == 'GET':
        room_id = request.GET.get('room_id')
        check_in = request.GET.get('check_in')
        check_out = request.GET.get('check_out')
        adults = request.GET.get('adults')
        children = request.GET.get('children', 0)

        # Kiểm tra bắt buộc nhập
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

        today = date.today()
        if check_in_date < today:
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

        context = {
            'selected_room': selected_room,
            'is_available': is_available,
            'capacity_exceeded': capacity_exceeded,
            'other_available_rooms': other_available_rooms,
            'check_in': check_in,
            'check_out': check_out,
            'adults': adults,
            'children': children,
            'total_guests': total_guests,
        }
        return render(request, 'rooms/roomsearch.html', context)

    return redirect('rooms:room_list')

@login_required
def room_booking(request):
    # Chỉ chấp nhận phương thức POST (khi khách nhấn từ trang Detail hoặc trang Booking)
    if request.method != 'POST':
        return redirect('rooms:room_list')

    # 1. LẤY DỮ LIỆU TỪ POST
    room_id = request.POST.get('room_id')
    print(f"DEBUG: Check-in từ form: {request.POST.get('check_in')}")
    check_in = request.POST.get('check_in')
    check_out = request.POST.get('check_out')
    adults = int(request.POST.get('adults', 1))
    children = int(request.POST.get('children', 0))
    coupon_code = request.POST.get('coupon_code', '').strip()
    payment_method = request.POST.get('mphb_gateway_id', 'pay_on_arrival')

    # 2. KIỂM TRA DỮ LIỆU CƠ BẢN (TRY-EXCEPT)
    try:
        room = get_object_or_404(Room, id=room_id)
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        
        if check_in_date < date.today():
            messages.error(request, 'Check-in date cannot be in the past.')
            return redirect('rooms:room_detail', room_id=room.id)
            
        if check_out_date <= check_in_date:
            messages.error(request, 'Check-out date must be after check-in date.')
            return redirect('rooms:room_detail', room_id=room.id)

        num_nights = (check_out_date - check_in_date).days
    except (ValueError, TypeError):
        messages.error(request, 'Invalid date format.')
        return redirect('rooms:room_list')

    # 3. TÍNH TOÁN GIÁ CƠ BẢN
    subtotal = room.price * num_nights
    gst = subtotal * Decimal('0.18')
    total = subtotal + gst
    discount = Decimal('0.00')
    coupon = None

    # 4. XỬ LÝ MÃ GIẢM GIÁ (COUPON)
    if coupon_code:
        try:
            coupon = Coupon.objects.get(
                code=coupon_code,
                active=True,
                valid_from__lte=date.today(), # Kiểm tra ngày hiện tại có nằm trong hạn dùng ko
                valid_to__gte=date.today()
            )
            discount = (subtotal * coupon.discount_percentage) / Decimal('100')
            total -= discount
            if 'apply_coupon' in request.POST:
                messages.success(request, f'Coupon "{coupon_code}" applied! You saved ₹{discount}')
        except Coupon.DoesNotExist:
            if 'apply_coupon' in request.POST:
                messages.error(request, 'Invalid or expired coupon code.')
                coupon_code = "" # Xóa code sai để tránh nhầm lẫn

    # Tạo form với dữ liệu POST để giữ lại thông tin khách đã nhập
    form = BookingForm(request.POST or None)

    # 5. XỬ LÝ KHI BẤM "BOOK NOW"
    if 'book_now' in request.POST:
        if form.is_valid():
            # Kiểm tra phòng trống lần cuối (Phòng tránh trường hợp có người khác vừa đặt xong)
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
                    reservation.total = total
                    reservation.coupon = coupon
                    reservation.payment_method = payment_method
                    reservation.save()

                messages.success(request, 'Booking successful! We are looking forward to seeing you.')
                return redirect('rooms:booking_confirmation', reservation_id=reservation.id)
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
        else:
            # In lỗi ra console để lập trình viên dễ debug
            print("Form Errors:", form.errors)
            messages.error(request, 'Please correct the errors in the form below.')

    # 6. TRẢ VỀ CONTEXT (Dùng chung cho cả Apply Coupon và khi Book Now bị lỗi form)
    context = {
        'form': form,
        'room': room,
        'check_in': check_in,
        'check_out': check_out,
        'adults': adults,
        'children': children,
        'num_nights': num_nights,
        'subtotal': subtotal,
        'gst': gst,
        'discount': discount,
        'total': total,
        'coupon_code': coupon_code,
    }
    return render(request, 'rooms/roombooking.html', context)

def booking_confirmation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Dòng này cực kỳ quan trọng
    num_nights = (reservation.check_out_date - reservation.check_in_date).days
    if num_nights <= 0: num_nights = 1 
    
    context = {
        'reservation': reservation,
        'num_nights': num_nights  # Biến này phải khớp với tên trong HTML
    }
    return render(request, 'rooms/bookingconfirmation.html', context)

@login_required
def my_bookings(request):
    # Fetch bookings for the logged-in user, ordered by created_at (newest first)
    bookings = Reservation.objects.filter(user=request.user).order_by('-created_at')
    context = {'bookings': bookings}
    return render(request, 'rooms/mybookings.html', context)


def home(request):
    rooms = Room.objects.all()
    blogs = Blog.objects.all()
    feedbacks = Feedback.objects.all().order_by('created_at')[:3]
    context = {
        'rooms': rooms,
        'blogs': blogs,
        'feedbacks': feedbacks,
    }
    return render(request, 'index.html', context)

def about_page(request):
    return render(request, 'about.html')


@login_required
def book_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    # default booking values (today/tomorrow, 1 guest)
    today = date.today()
    default_check_in = today
    default_check_out = today + timedelta(days=1)
    default_adults = 1

    # Always have these set for context, even on GET
    check_in = default_check_in.strftime('%Y-%m-%d')
    check_out = default_check_out.strftime('%Y-%m-%d')
    adults = default_adults

    if request.method == "POST":
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

    # Build context for booking page (used for rendering the form and totals)
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

    context = {
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
    }

    return render(request, 'rooms/roombooking.html', context)

def check_room_availability_api(request):
    room_id = request.GET.get('id')
    check_in = request.GET.get('in')
    check_out = request.GET.get('out')
    
    # Logic kiểm tra trùng lịch
    is_booked = Reservation.objects.filter(
        room_id=room_id,
        check_in_date__lt=check_out,
        check_out_date__gt=check_in
    ).exists()
    
    return JsonResponse({'is_available': not is_booked})

# views.py
def checkout_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Đánh dấu đã trả phòng
    reservation.is_checked_out = True
    reservation.save()
    
    messages.success(request, f"Phòng {reservation.room.name} đã được trả và hiện đang trống.")
    return redirect('rooms:my_bookings') # Hoặc trang quản lý của bạn

# views.py
def checkout_reservation(request, reservation_id):
    if request.method == 'POST':
        reservation = get_object_or_404(Reservation, id=reservation_id)
        reservation.is_checked_out = True # Đánh dấu đã trả phòng
        reservation.save()
        
        messages.success(request, f"Đã trả phòng {reservation.room.name} thành công!")
        return redirect('rooms:room_list') # Hoặc trang bạn muốn quay lại
    
    return redirect('rooms:room_list')