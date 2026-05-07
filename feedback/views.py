from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import TemplateView
from django.db import models
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .forms import FeedbackForm, FeedbackListForm
from .models import Feedback
from .serializers import FeedbackSerializer, FeedbackCreateSerializer, FeedbackListSerializer
from rooms.models import Room, Reservation


def submit_feedback(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        form = FeedbackForm(request.POST, user=request.user)
        if form.is_valid():
            feedback = form.save(commit=False)
            if request.user.is_authenticated:
                # For authenticated users, link to user and use profile data
                feedback.user = request.user
                feedback.name = request.user.get_full_name()
                feedback.email = request.user.email
            else:
                # For non-authenticated users, use form data
                feedback.name = form.cleaned_data['name']
                feedback.email = form.cleaned_data['email']
            feedback.room = room
            feedback.save()
            messages.success(request, 'Feedback submitted successfully.')
            return redirect('feedback:feedback_list')
        else:
            messages.error(request, 'Invalid form submission. Please try again.')
            return redirect('rooms:room_detail', room_id=room_id)
    return redirect('rooms:room_detail', room_id=room_id)


def feedback_list(request):
    feedbacks = Feedback.objects.all().order_by('-created_at')
    form = FeedbackListForm(request.POST or None, user=request.user)

    if request.method == 'POST':
        if form.is_valid():
            feedback = form.save(commit=False)
            if request.user.is_authenticated:
                feedback.user = request.user
                feedback.name = request.user.get_full_name() or request.user.username
                feedback.email = request.user.email
            feedback.save()
            messages.success(request, 'Cảm ơn bạn đã gửi feedback.')
            return redirect('feedback:feedback_list')
        messages.error(request, 'Không thể gửi feedback, vui lòng kiểm tra lại thông tin.')

    return render(request, 'feedback/feedback_list.html', {'feedbacks': feedbacks, 'form': form})


def feedback_after_checkout(request, reservation_id):
    """Page for submitting feedback after checkout"""
    reservation = get_object_or_404(Reservation, id=reservation_id, is_checked_out=True)
    
    if request.method == 'POST':
        form = FeedbackForm(request.POST, user=request.user)
        if form.is_valid():
            feedback = form.save(commit=False)
            if request.user.is_authenticated:
                feedback.user = request.user
                feedback.name = request.user.get_full_name()
                feedback.email = request.user.email
            else:
                feedback.name = form.cleaned_data.get('name', '')
                feedback.email = form.cleaned_data.get('email', '')
            
            feedback.room = reservation.room
            feedback.reservation = reservation
            feedback.save()
            messages.success(request, 'Cảm ơn bạn đã đánh giá! Your feedback helps us improve.')
            return redirect('feedback:feedback_thanks', reservation_id=reservation_id)
        else:
            messages.error(request, 'Invalid form submission. Please try again.')
    else:
        form = FeedbackForm(user=request.user)
    
    context = {
        'form': form,
        'reservation': reservation,
        'room': reservation.room,
    }
    return render(request, 'feedback/feedback_form.html', context)


def feedback_thanks(request, reservation_id):
    """Thank you page after feedback submission"""
    reservation = get_object_or_404(Reservation, id=reservation_id, is_checked_out=True)
    context = {
        'reservation': reservation,
        'room': reservation.room,
    }
    return render(request, 'feedback/feedback_thanks.html', context)


# ==================== API Views ====================

class FeedbackListAPIView(generics.ListAPIView):
    """List all feedback for rooms"""
    queryset = Feedback.objects.all()
    serializer_class = FeedbackListSerializer
    permission_classes = [AllowAny]
    ordering = ['-created_at']


class FeedbackDetailAPIView(generics.RetrieveAPIView):
    """Get feedback detail"""
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [AllowAny]


class FeedbackCreateAPIView(generics.CreateAPIView):
    """Create feedback after checkout using booking code"""
    serializer_class = FeedbackCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'status': 'success',
                'message': 'Feedback submitted successfully!',
                'data': FeedbackSerializer(serializer.instance).data
            },
            status=status.HTTP_201_CREATED
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def feedback_by_room(request, room_id):
    """Get all feedback for a specific room"""
    room = get_object_or_404(Room, id=room_id)
    feedbacks = Feedback.objects.filter(room=room).order_by('-created_at')
    
    serializer = FeedbackListSerializer(feedbacks, many=True)
    return Response({
        'room': room.name,
        'room_id': room.id,
        'total_feedbacks': feedbacks.count(),
        'average_rating': feedbacks.aggregate(models.Avg('rating'))['rating__avg'] or 0,
        'feedbacks': serializer.data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def feedback_by_reservation(request, reservation_id):
    """Get feedback for a specific reservation"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    feedback = Feedback.objects.filter(reservation=reservation).first()
    
    if feedback:
        serializer = FeedbackSerializer(feedback)
        return Response({
            'status': 'success',
            'data': serializer.data
        })
    else:
        return Response({
            'status': 'not_found',
            'message': 'No feedback found for this reservation'
        }, status=status.HTTP_404_NOT_FOUND)
