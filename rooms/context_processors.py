from .models import Reservation

def booking_count(request):
    if request.user.is_authenticated:
        count = Reservation.objects.filter(user=request.user).count()
    else:
        count = 0
    return {'booking_count': count}