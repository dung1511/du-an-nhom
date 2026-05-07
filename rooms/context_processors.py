# Import model Reservation từ models.py
from .models import Reservation


# Hàm context processor dùng để truyền dữ liệu booking_count
# ra tất cả template trong Django
def booking_count(request):

    # Kiểm tra người dùng đã đăng nhập chưa
    if request.user.is_authenticated:

        # Đếm số lượng booking của user hiện tại
        # Reservation.objects.filter(...)
        # -> Lọc các booking theo user đang đăng nhập
        #
        # .count()
        # -> Đếm tổng số booking tìm được
        count = Reservation.objects.filter(
            user=request.user
        ).count()

    else:
        # Nếu chưa đăng nhập thì số booking = 0
        count = 0

    # Trả dữ liệu về template dưới dạng dictionary
    # booking_count sẽ được dùng trực tiếp trong HTML
    return {
        'booking_count': count
    }