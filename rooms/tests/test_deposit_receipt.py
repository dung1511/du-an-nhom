import io
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import base64
from django.contrib.auth import get_user_model
import pytest
from rest_framework.test import APIClient
from rooms.models import Reservation
from decimal import Decimal

User = get_user_model()

@pytest.mark.django_db
def test_upload_deposit_receipt_api_and_notify(settings):
    settings.ADMINS = [("Admin", "admin@example.com")]
    settings.DEFAULT_FROM_EMAIL = 'noreply@example.com'

    # create reservation
    # create room for FK
    from rooms.models import Room
    room = Room.objects.create(name='Test', capacity=2, capacity_adults=2, capacity_children=0, total_capacity=2, description='x', price=100)

    reservation = Reservation.objects.create(
        room=room,
        check_in_date='2026-06-01',
        check_out_date='2026-06-02',
        subtotal=Decimal('100.00'),
        gst=Decimal('18.00'),
        total=Decimal('118.00'),
    )

    client = APIClient()
    url = reverse('rooms:api_upload_deposit_receipt', args=[reservation.id])

    # 1x1 PNG image bytes
    png_b64 = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII='
    img_bytes = base64.b64decode(png_b64)
    img = SimpleUploadedFile('receipt.png', img_bytes, content_type='image/png')
    resp = client.post(url, {'deposit_receipt': img, 'booking_code': reservation.booking_code}, format='multipart')
    if resp.status_code != 200:
        print('RESP:', resp.status_code, resp.data)
    assert resp.status_code == 200
    reservation.refresh_from_db()
    assert reservation.deposit_receipt
    assert reservation.deposit_receipt_uploaded_at is not None

@pytest.mark.django_db
def test_admin_confirm_deposit_api(client, django_user_model):
    # create a staff user
    staff = django_user_model.objects.create_user(username='staff', password='pass')
    staff.is_staff = True
    staff.save()

    # create reservation with a fake receipt
    from rooms.models import Room
    room = Room.objects.create(name='Test2', capacity=2, capacity_adults=2, capacity_children=0, total_capacity=2, description='x', price=100)

    reservation = Reservation.objects.create(
        room=room,
        check_in_date='2026-06-01',
        check_out_date='2026-06-02',
        subtotal=Decimal('100.00'),
        gst=Decimal('18.00'),
        total=Decimal('118.00'),
    )
    # attach an empty file
    reservation.deposit_receipt = SimpleUploadedFile('r.jpg', b'content', content_type='image/jpeg')
    reservation.save()

    client.force_login(staff)
    url = reverse('rooms:api_admin_confirm_deposit', args=[reservation.id])
    resp = client.post(url)
    assert resp.status_code == 200
    reservation.refresh_from_db()
    assert reservation.deposit_confirmed is True
    assert reservation.payment_status == 'paid'
