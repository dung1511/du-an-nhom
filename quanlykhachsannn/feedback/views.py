from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import FeedbackForm
from .models import Feedback
from rooms.models import Room

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
    return render(request, 'feedback/feedback_list.html', {'feedbacks': feedbacks})