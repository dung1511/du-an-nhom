# rooms/urls.py
from django.urls import path
from . import views

app_name = 'rooms'

urlpatterns = [
    # API endpoints (REST Framework)
    path('api/bookings/', views.ReservationListCreateAPIView.as_view(), name='api_booking_create'),
    path('api/rooms/', views.RoomListAPIView.as_view(), name='api_rooms_list'),
    path('api/rooms/<int:id>/', views.RoomDetailAPIView.as_view(), name='api_room_detail'),
    path('api/room-categories/', views.RoomCategoryListAPIView.as_view(), name='api_room_categories'),
    path('api/reservations/', views.ReservationListAPIView.as_view(), name='api_reservations_list'),
    path('api/reservations/checked-out/', views.ReservationCheckedOutListAPIView.as_view(), name='api_checked_out_reservations_list'),
    path('api/reservations/<int:id>/', views.ReservationDetailAPIView.as_view(), name='api_reservation_detail'),
    path('api/reservations/<int:id>/checkout/', views.ReservationCheckoutAPIView.as_view(), name='api_checkout'),
    path('api/reservations/<int:id>/payment/', views.ReservationPaymentAPIView.as_view(), name='api_payment'),
    path('api/rooms/search/', views.RoomSearchAPIView.as_view(), name='api_rooms_search'),
    path('api/admin/dashboard/', views.AdminDashboardAPIView.as_view(), name='api_admin_dashboard'),
    path('api/admin/reservations/', views.AdminReservationListAPIView.as_view(), name='api_admin_reservations'),
    path('api/admin/checked-out-reservations/', views.AdminCheckedOutReservationListAPIView.as_view(), name='api_admin_checked_out_reservations'),
    path('api/admin/rooms/', views.AdminRoomListAPIView.as_view(), name='api_admin_rooms'),
    
    # Web views
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/<int:room_id>/', views.room_detail, name='room_detail'),
    path('roomsearch/', views.room_search , name='room_search'),
    path('roombooking/', views.room_booking , name='room_booking'),
    path('booking-confirmation/<int:reservation_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('rooms/filter/', views.room_list_filtered, name='room_list_filtered'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('book-room/<int:room_id>/', views.book_room, name='book_room'),
    path('checkout/<int:reservation_id>/', views.checkout_reservation, name='checkout_reservation'),
]   