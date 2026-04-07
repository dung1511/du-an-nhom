# 🧪 Hướng Dẫn Viết Automated Tests

## 📦 Bước 1: Cài Đặt Testing Tools

```bash
pip install pytest pytest-django pytest-cov factory-boy
```

## 📁 Bước 2: Tạo Structure Tests

```
quanlykhachsannn/
├── rooms/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py           # pytest configuration
│   │   ├── factories.py           # test data factories
│   │   ├── test_models.py         # model tests
│   │   ├── test_views.py          # API view tests
│   │   ├── test_serializers.py    # serializer tests
│   │   └── test_forms.py          # form tests
│   ├── models.py
│   ├── views.py
│   └── ...
└── pytest.ini
```

## 📝 Bước 3: File Cấu Hình

### File `pytest.ini`
```ini
[pytest]
DJANGO_SETTINGS_MODULE = quanlykhachsannn.settings
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*
addopts = --cov=rooms --cov=accounts --cov-report=html --cov-report=term-missing
testpaths = rooms/tests accounts/tests
```

### File `rooms/tests/conftest.py`
```python
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

@pytest.fixture
def api_client():
    """Tạo API client cho tests"""
    return APIClient()

@pytest.fixture
def user(db):
    """Tạo user test"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def authenticated_client(api_client, user):
    """Tạo API client với authentication"""
    api_client.force_authenticate(user=user)
    return api_client
```

### File `rooms/tests/factories.py`
```python
import factory
from datetime import date, timedelta
from django.contrib.auth.models import User
from rooms.models import Room, RoomCategory, Coupon, Reservation, Service

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = "testpass123"


class RoomCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RoomCategory
    
    category = "Deluxe"
    category_description = "Luxury room"


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Room
    
    room_title = "Test Room"
    slug = "test-room"
    category = factory.SubFactory(RoomCategoryFactory)
    room_description = "Test description"
    price = 150.00
    max_adult = 2
    max_children = 1
    bed = 1
    bath = 1
    wifi = True
    tv = True
    kitchen = True
    ac = True
    parking = True
    working_desk = True
    balcony = True
    room_size = "D"


class CouponFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Coupon
    
    code = factory.Sequence(lambda n: f"COUPON{n}")
    discount_price = 20.00
    is_active = True


class ServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Service
    
    name = factory.Sequence(lambda n: f"Service{n}")
    price = 50.00
    image_url = "https://example.com/image.jpg"


class ReservationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reservation
    
    user = factory.SubFactory(UserFactory)
    room = factory.SubFactory(RoomFactory)
    check_in_date = date.today() + timedelta(days=1)
    check_out_date = date.today() + timedelta(days=3)
    num_nights = 2
    adults = 2
    children = 0
    first_name = "Nguyễn"
    last_name = "Văn A"
    email = "test@example.com"
    phone = "0123456789"
    address = "123 Đường A"
    city = "Hà Nội"
    state = "Hà Nội"
    postcode = "100000"
    subtotal = 300.00
    gst = 54.00
    total = 354.00
    payment_method = "cards"
    is_checked_out = False
```

## 🧪 Bước 4: Viết Tests

### File `rooms/tests/test_models.py`
```python
import pytest
from datetime import date, timedelta
from rooms.models import Room, Coupon, Reservation
from .factories import (
    RoomFactory, RoomCategoryFactory, CouponFactory, 
    ReservationFactory, UserFactory
)

@pytest.mark.django_db
class TestRoom:
    """Tests cho Room model"""
    
    def test_room_creation(self):
        """Test tạo room"""
        room = RoomFactory(room_title="Luxury Suite", price=200.00)
        assert room.room_title == "Luxury Suite"
        assert room.price == 200.00
    
    def test_room_string_representation(self):
        """Test string representation của room"""
        room = RoomFactory()
        assert str(room) == room.room_title
    
    def test_room_is_available(self):
        """Test check room availability"""
        room = RoomFactory()
        check_in = date.today() + timedelta(days=5)
        check_out = date.today() + timedelta(days=7)
        # Implement based on your model logic
        # assert room.is_available(check_in, check_out)


@pytest.mark.django_db
class TestCoupon:
    """Tests cho Coupon model"""
    
    def test_coupon_creation(self):
        """Test tạo coupon"""
        coupon = CouponFactory(code="SAVE20", discount_price=20.00)
        assert coupon.code == "SAVE20"
        assert coupon.is_active == True
    
    def test_inactive_coupon(self):
        """Test coupon không hoạt động"""
        coupon = CouponFactory(is_active=False)
        assert coupon.is_active == False


@pytest.mark.django_db
class TestReservation:
    """Tests cho Reservation model"""
    
    def test_reservation_creation(self):
        """Test tạo reservation"""
        user = UserFactory()
        room = RoomFactory()
        reservation = ReservationFactory(user=user, room=room)
        assert reservation.user == user
        assert reservation.room == room
        assert reservation.is_checked_out == False
    
    def test_reservation_total_calculation(self):
        """Test tính toán total"""
        reservation = ReservationFactory(subtotal=300.00, gst=54.00)
        # Implement based on your model logic
        # assert reservation.total == 354.00
    
    def test_num_nights_calculation(self):
        """Test tính số đêm"""
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=4)
        reservation = ReservationFactory(
            check_in_date=check_in,
            check_out_date=check_out
        )
        assert reservation.num_nights == 3
```

### File `rooms/tests/test_views.py`
```python
import pytest
from datetime import date, timedelta
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rooms.models import Room, Reservation
from .factories import (
    RoomFactory, UserFactory, ReservationFactory, CouponFactory
)

@pytest.mark.django_db
class TestRoomSearchAPIView:
    """Tests cho Room Search API"""
    
    def test_search_rooms_valid_criteria(self):
        """Test tìm kiếm phòng với criteria hợp lệ"""
        client = APIClient()
        
        # Tạo test data
        room = RoomFactory(max_adult=2, max_children=1)
        
        url = reverse('room-search')  # Adjust based on your URL name
        data = {
            'check_in_date': (date.today() + timedelta(days=1)).isoformat(),
            'check_out_date': (date.today() + timedelta(days=3)).isoformat(),
            'adults': 2,
            'children': 0,
            'limit': 5
        }
        
        response = client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] == True
    
    def test_search_rooms_invalid_dates(self):
        """Test tìm kiếm phòng với ngày không hợp lệ"""
        client = APIClient()
        
        url = reverse('room-search')
        data = {
            'check_in_date': (date.today() - timedelta(days=1)).isoformat(),  # Ngày quá khứ
            'check_out_date': date.today().isoformat(),
            'adults': 1,
            'children': 0
        }
        
        response = client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_search_rooms_checkout_before_checkin(self):
        """Test check-out trước check-in"""
        client = APIClient()
        
        url = reverse('room-search')
        data = {
            'check_in_date': (date.today() + timedelta(days=5)).isoformat(),
            'check_out_date': (date.today() + timedelta(days=2)).isoformat(),
            'adults': 1,
            'children': 0
        }
        
        response = client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestReservationAPIView:
    """Tests cho Reservation API"""
    
    def test_create_reservation_authenticated(self):
        """Test tạo reservation khi đã đăng nhập"""
        client = APIClient()
        user = UserFactory()
        client.force_authenticate(user=user)
        
        room = RoomFactory()
        url = reverse('reservation-list')  # Adjust based on your URL name
        data = {
            'room': room.id,
            'check_in_date': (date.today() + timedelta(days=1)).isoformat(),
            'check_out_date': (date.today() + timedelta(days=3)).isoformat(),
            'adults': 2,
            'children': 0,
            'first_name': 'Nguyễn',
            'last_name': 'Văn A',
            'email': 'test@example.com',
            'phone': '0123456789',
            'address': '123 Street',
            'city': 'Hà Nội',
            'state': 'Hà Nội',
            'postcode': '100000'
        }
        
        response = client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_create_reservation_unauthenticated(self):
        """Test tạo reservation khi chưa đăng nhập"""
        client = APIClient()
        
        url = reverse('reservation-list')
        data = {'room': 1, 'adults': 2}
        
        response = client.post(url, data, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_reservation_list(self):
        """Test lấy danh sách reservation"""
        client = APIClient()
        user = UserFactory()
        client.force_authenticate(user=user)
        
        # Tạo test reservations
        ReservationFactory(user=user)
        ReservationFactory(user=user)
        
        url = reverse('reservation-list')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2


@pytest.mark.django_db
class TestCheckoutAPIView:
    """Tests cho Checkout API"""
    
    def test_checkout_valid_reservation(self):
        """Test checkout reservation hợp lệ"""
        client = APIClient()
        user = UserFactory()
        client.force_authenticate(user=user)
        
        reservation = ReservationFactory(user=user)
        url = reverse('reservation-checkout', kwargs={'pk': reservation.id})
        data = {'is_checked_out': True}
        
        response = client.put(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_checked_out'] == True
```

## 🚀 Bước 5: Chạy Tests

```bash
# Chạy tất cả tests
pytest

# Chạy tests với coverage report
pytest --cov

# Chạy tests cho một file cụ thể
pytest rooms/tests/test_models.py

# Chạy tests cho một class cụ thể
pytest rooms/tests/test_models.py::TestRoom

# Chạy tests cho một method cụ thể
pytest rooms/tests/test_models.py::TestRoom::test_room_creation

# Chạy tests với verbose output
pytest -v

# Chạy tests và stop ở lỗi đầu tiên
pytest -x
```

## 📊 Kiểm Tra Coverage

```bash
# Generate coverage report
pytest --cov=rooms --cov=accounts --cov-report=html

# View report
# Mở file htmlcov/index.html trong browser
```

## ✅ Checklist Viết Tests

- [ ] Test models (create, update, delete, validation)
- [ ] Test API endpoints (GET, POST, PUT, DELETE)
- [ ] Test authentication & permissions
- [ ] Test form validation
- [ ] Test error responses
- [ ] Test edge cases & invalid inputs
- [ ] Test business logic
- [ ] Achieve 70%+ coverage

## 📝 Template Test Method

```python
@pytest.mark.django_db
def test_descriptive_test_name(authenticated_client):
    """Mô tả chính xác cái bạn đang test
    
    Given: Setup initial state
    When: Perform action
    Then: Assert expected outcome
    """
    # ARRANGE - Chuẩn bị dữ liệu
    test_data = RoomFactory()
    
    # ACT - Thực hiện action
    response = authenticated_client.get('/api/rooms/')
    
    # ASSERT - Kiểm tra kết quả
    assert response.status_code == 200
    assert len(response.data) > 0
```

---

**Mục tiêu**: Viết tests để đạt 70-80% code coverage cho core features
