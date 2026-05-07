import pytest
from django.urls import reverse

from rooms.tests.factories import RoomFactory
from feedback.models import Feedback


@pytest.mark.django_db
def test_feedback_list_page_renders_form(client):
    response = client.get(reverse('feedback:feedback_list'))
    assert response.status_code == 200
    assert 'Gửi feedback của bạn' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_feedback_list_page_submission_creates_feedback(client):
    room = RoomFactory()

    response = client.post(
        reverse('feedback:feedback_list'),
        {
            'room': room.id,
            'name': 'Mon Giau',
            'email': 'mon@example.com',
            'country': 'Vietnam',
            'rating': 5,
            'comment': 'Trang feedback rất tiện.',
        },
    )

    assert response.status_code == 302
    assert response.url == reverse('feedback:feedback_list')
    assert Feedback.objects.filter(room=room, email='mon@example.com').exists()