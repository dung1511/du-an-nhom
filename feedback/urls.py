from django.urls import path
from .views import (
    submit_feedback, 
    feedback_list,
    feedback_after_checkout,
    feedback_thanks,
    FeedbackListAPIView,
    FeedbackDetailAPIView,
    FeedbackCreateAPIView,
    feedback_by_room,
    feedback_by_reservation,
)

app_name = 'feedback'

urlpatterns = [
    # Web routes
    path('submit/<int:room_id>/', submit_feedback, name='submit_feedback'),
    path('list/', feedback_list, name='feedback_list'),
    path('checkout/<int:reservation_id>/', feedback_after_checkout, name='feedback_after_checkout'),
    path('thanks/<int:reservation_id>/', feedback_thanks, name='feedback_thanks'),
    
    # API routes
    path('api/list/', FeedbackListAPIView.as_view(), name='api_feedback_list'),
    path('api/<int:pk>/', FeedbackDetailAPIView.as_view(), name='api_feedback_detail'),
    path('api/submit/', FeedbackCreateAPIView.as_view(), name='api_feedback_create'),
    path('api/room/<int:room_id>/', feedback_by_room, name='api_feedback_by_room'),
    path('api/reservation/<int:reservation_id>/', feedback_by_reservation, name='api_feedback_by_reservation'),
]
