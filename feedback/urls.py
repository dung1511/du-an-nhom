from django.urls import path
from .views import submit_feedback, feedback_list

app_name = 'feedback'

urlpatterns = [
    path('submit/<int:room_id>/', submit_feedback, name='submit_feedback'),
    path('list/', feedback_list, name='feedback_list'),
]