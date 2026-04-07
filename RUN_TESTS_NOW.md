# 🧪 Quick Start - Run Tests & Continue Testing

## ▶️ Run Tests RIGHT NOW

```bash
# Navigate to project
cd "c:/Users/ASUS/Downloads/du-an-nhom-feature-admin-room (2)/du-an-nhom-feature-admin-room/du-an-nhom-feature-admin-room"

# Run ALL tests
"C:/Users/ASUS/AppData/Local/Python/pythoncore-3.14-64/python.exe" -m pytest

# Run MODEL tests only
"C:/Users/ASUS/AppData/Local/Python/pythoncore-3.14-64/python.exe" -m pytest rooms/tests/test_models.py -v

# Run with coverage (generates HTML report)
"C:/Users/ASUS/AppData/Local/Python/pythoncore-3.14-64/python.exe" -m pytest --cov
```

---

## 📊 Current Test Status

```
✅ 20 tests created & passing
✅ 100% coverage for room models
✅ Test infrastructure ready
📁 API test file ready (rooms/tests/test_views.py)
```

---

## 🎯 Quick Template - Add More Tests

### To add a new test in test_models.py:

```python
@pytest.mark.django_db
def test_my_feature():
    """Test description here"""
    # ARRANGE - Create test data
    user = UserFactory(email="test@example.com")
    room = RoomFactory()
    
    # ACT - Do something
    reservation = ReservationFactory(user=user, room=room)
    
    # ASSERT - Check result
    assert reservation.user == user
    assert reservation.room == room
```

---

## 📝 Available Fixtures (from conftest.py)

```python
def test_something(api_client):              # API client
    response = api_client.get('/api/rooms/')

def test_something(user):                    # Test user
    assert user.username == 'testuser'
    
def test_something(authenticated_client):   # Auth'd API client
    response = authenticated_client.get('/api/reservations/')
```

---

## 🏭 Available Factories (from factories.py)

```python
user = UserFactory()                              
room = RoomFactory(name="Suite", price=200)
res = ReservationFactory(user=user, room=room)
coupon = CouponFactory(code="SAVE20")
service = ServiceFactory(name="Airport Shuttle")

# Create multiple
rooms = RoomFactory.create_batch(5)
reservations = ReservationFactory.create_batch(3, user=user)
```

---

## 🔗 Where Are Tests?

- **Models**: `rooms/tests/test_models.py` ✅ (20 tests done)
- **APIs**: `rooms/tests/test_views.py` 📝 (ready to implement)
- **Forms**: `rooms/tests/test_forms.py` 📝 (template)
- **Config**: `pytest.ini` ✅ (ready)
- **Fixtures**: `rooms/tests/conftest.py` ✅ (ready)
- **Data**: `rooms/tests/factories.py` ✅ (ready)

---

## 📚 Example: Test an API

File: `rooms/tests/test_views.py`

```python
@pytest.mark.django_db
def test_search_rooms(api_client):
    """Test room search API"""
    # Create test data
    room = RoomFactory(capacity=4)
    
    # Make request
    response = api_client.post('/rooms/api/rooms/search/', {
        'check_in_date': '2026-04-15',
        'check_out_date': '2026-04-17',
        'adults': 2,
        'children': 0
    })
    
    # Check response
    assert response.status_code == 200
    assert len(response.data['rooms']) >= 1
```

---

## 🚀 Next: Implement API Tests

1. **Open**: `rooms/tests/test_views.py`
2. **Uncomment** the test classes: `TestRoomSearchAPIView`, `TestReservationListCreateAPIView`
3. **Fix URL names** to match your `rooms/urls.py`:
   ```python
   # Find actual URL name from rooms/urls.py
   url = reverse('room-search')  # Check your actual URL name
   ```
4. **Run tests**:
   ```bash
   pytest rooms/tests/test_views.py::TestRoomSearchAPIView -v
   ```

---

## 📊 Coverage Report

**View HTML report:**
```bash
explorer htmlcov/index.html  # Opens in Windows Explorer
```

**Target Coverage:**
- Models: ✅ 100% (done)
- Views: 🚀 To do (aim for 70%+)
- Forms: 🚀 To do (aim for 60%+)
- Overall: Target 70%+

---

## ⚡ Quick Commands

```bash
# Run quick test
pytest rooms/tests/test_models.py -q

# Run with details
pytest rooms/tests/test_models.py -v

# Run specific test
pytest rooms/tests/test_models.py::test_room_creation -v

# Run and stop on first failure
pytest -x

# Run and show print statements
pytest -s

# Run single file
pytest rooms/tests/test_models.py

# Run all tests
pytest

#  Run with coverage
pytest --cov

# Generate new coverage report
pytest --cov --cov-report=html
```

---

## 📋 Test Files Overview

| File | Status | Tests | Coverage |
|------|--------|-------|----------|
| test_models.py | ✅ Done | 20 | 100% |
| test_views.py | 📝 Ready | ~30 | 0% |
| test_forms.py | 📝 Ready | ~10 | 0% |
| **Total** | - | **~60** | - |

---

## ✨ Pro Tips

1. **Use factories instead of fixtures** - easier to customize per test
2. **Test one thing per test** - makes debugging easier
3. **Use descriptive test names** - should describe what's being tested
4. **Use @pytest.mark.django_db** on any test that uses database
5. **Don't mock too much** - test actual functionality

---

## 🆘 Troubleshooting

**Tests not running?**
```bash
# Check Django settings
"C:/Users/ASUS/AppData/Local/Python/pythoncore-3.14-64/python.exe" manage.py shell

# Run migrations
"C:/Users/ASUS/AppData/Local/Python/pythoncore-3.14-64/python.exe" manage.py migrate
```

**Import errors?**
- Check `__init__.py` exists in all test directories
- Check `pytest.ini` has correct DJANGO_SETTINGS_MODULE

**Tests slow?**
- Cover fewer files with `--cov=rooms` flag
- Use `-q` flag for quiet mode

---

## 🎓 Resources

- **pytest docs**: https://docs.pytest.org
- **pytest-django**: https://pytest-django.readthedocs.io
- **factory-boy**: https://factoryboy.readthedocs.io
- **DRF testing**: https://www.django-rest-framework.org/api-guide/testing/

---

## 🎯 Goal: 70%+ Test Coverage

**Progress:**
- Phase 1 ✅: Models (20 tests, 100% coverage)
- Phase 2 🚀: Views (API tests)
- Phase 3 🚀: Forms & Serializers
- Phase 4 🚀: Integration tests

**Current**: 27% → **Target**: 70%+

Start with Phase 2! Need help? Check TESTING_GUIDE.md

---

**Last Updated**: 2026-04-07
**Status**: Ready to expand tests ✅
