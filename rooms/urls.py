# rooms/urls.py
from django.urls import path
from . import views

app_name = 'rooms'

urlpatterns = [
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/<int:room_id>/', views.room_detail, name='room_detail'),
    path('roomsearch/', views.room_search , name='room_search'),
    path('roombooking/', views.room_booking , name='room_booking'),
    path('booking-confirmation/<int:reservation_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('rooms/filter/', views.room_list_filtered, name='room_list_filtered'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
<<<<<<< HEAD
=======

    path('book-room/<int:room_id>/', views.book_room, name='book_room'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
>>>>>>> f22798a4e339a890b18717753c45a9181ca0757b
]   