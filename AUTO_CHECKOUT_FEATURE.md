# Tính Năng Auto-Checkout & Auto-Cancel No-Show

## 📋 Giới Thiệu

Tính năng này tự động **check-out, hủy đơn đặt phòng, và cập nhật trạng thái phòng** khi khách không đến nhận phòng đúng giờ.

### Luồng hoạt động:
```
Check-in date tới + Quá giờ grace period (6 giờ mặc định)
    ↓
Kiểm tra: Khách đã check-in?
    ↓
KHÔNG → Auto-checkout + Auto-cancel + Cập nhật trạng thái phòng → Phòng trở thành CÓ SẴN
    ↓
Gửi email thông báo cho admin & khách
```

---

## 🔧 Cài Đặt

### 1. File Đã Được Cập Nhật

**Location:** `rooms/management/commands/auto_cancel_no_shows.py`

**Chức năng:**
- ✅ Auto-checkout: Đánh dấu `is_checked_out=True` + ghi `checkout_at` timestamp
- ✅ Set `actual_check_out_date` = ngày hôm nay
- ✅ Auto-cancel: Gọi `cancel_reservation()` với reason = 'no_show_auto_cancel'
- ✅ Cập nhập trạng thái phòng: Phòng tự động trở thành "CÓ SẴN" (vì `is_checked_out=True`)
- ✅ Email notifications: Thông báo cho admin & khách

### 2. Cấu hình trong Settings

**File:** `quanlykhachsannn/settings.py`

```python
# Giờ check-in mặc định (format HH:MM)
DEFAULT_CHECK_IN_TIME = '08:00'

# Thời gian chờ trước khi tự động hủy (giờ)
NO_SHOW_GRACE_HOURS = 6
```

**Mặc định:**
- Check-in: 08:00 sáng
- Grace period: 6 giờ → Auto-cancel lúc 14:00 (2 chiều) nếu không check-in

---

## 🚀 Cách Sử Dụng

### A. Chạy Thủ Công (Manual)

Chạy lệnh này bất cứ lúc nào:

```bash
python manage.py auto_cancel_no_shows
```

**Output mẫu:**
```
Auto-cancel & auto-checkout completed.
  - 3 reservation(s) auto-checked-out
  - 3 reservation(s) canceled
  - Room status(es) updated to AVAILABLE
```

---

### B. Lên Lịch Tự Động (Recommended)

#### **Option 1: Linux/Mac - Cron Job (Tốt nhất)**

**Setup:**

```bash
# Mở crontab editor
crontab -e

# Thêm dòng sau (chạy mỗi giờ)
0 * * * * cd /path/to/project && python manage.py auto_cancel_no_shows >> /var/log/auto_checkout.log 2>&1

# Hoặc chạy mỗi 30 phút để nhanh hơn
*/30 * * * * cd /path/to/project && python manage.py auto_cancel_no_shows >> /var/log/auto_checkout.log 2>&1
```

**Ý nghĩa:**
- `0 * * * *` = Chạy vào phút thứ 0 của mỗi giờ (08:00, 09:00, ...)
- `*/30 * * * *` = Chạy mỗi 30 phút

---

#### **Option 2: Windows - Task Scheduler**

**Bước 1:** Mở Task Scheduler
- Nhấn `Win + R`
- Gõ `taskschd.msc`

**Bước 2:** Tạo Task mới
- Click **Create Basic Task**
- **Name:** "Hotel Auto-Checkout"
- **Description:** "Automatically cancel & checkout no-show reservations"

**Bước 3:** Set Trigger (Lên lịch)
- **Trigger:** "Daily" hoặc "Hourly"
- **Repeat every:** 1 hour
- **Start time:** 09:00 (sớm hơn grace period để an toàn)

**Bước 4:** Set Action (Hành động)
- **Action:** "Start a program"
- **Program:** `C:\Python39\python.exe` (hoặc đường dẫn Python của bạn)
- **Arguments:** `manage.py auto_cancel_no_shows`
- **Start in:** `C:\path\to\project` (đường dẫn project)

---

#### **Option 3: Celery + Beat (Nếu dùng Celery)**

**1. Cài đặt Celery:**

```bash
pip install celery redis
```

**2. Tạo file `rooms/tasks.py`:**

```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def run_auto_checkout():
    """Scheduled task to auto-checkout & cancel no-shows"""
    call_command('auto_cancel_no_shows')
    return "Auto-checkout completed"
```

**3. Cấu hình Celery Beat trong `quanlykhachsannn/settings.py`:**

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'auto-checkout-hourly': {
        'task': 'rooms.tasks.run_auto_checkout',
        'schedule': crontab(minute=0),  # Chạy mỗi giờ vào phút thứ 0
    },
}
```

**4. Start Celery Beat:**

```bash
celery -A quanlykhachsannn beat -l info
```

---

#### **Option 4: APScheduler (Đơn giản nhất, không cần Redis)**

**1. Cài đặt:**

```bash
pip install django-apscheduler
```

**2. Thêm vào `INSTALLED_APPS` trong settings.py:**

```python
INSTALLED_APPS = [
    ...
    'django_apscheduler',
]
```

**3. Tạo file `rooms/apps.py` - thêm scheduler setup:**

```python
from django.apps import AppConfig
from django.core.management import call_command

class RoomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rooms'

    def ready(self):
        from django_apscheduler.scheduler import DjangoAPScheduler
        import atexit
        
        scheduler = DjangoAPScheduler()
        
        def auto_checkout_task():
            call_command('auto_cancel_no_shows')
        
        # Chạy mỗi giờ vào phút thứ 0
        scheduler.add_job(
            auto_checkout_task,
            'cron',
            minute=0,
            name='Auto-checkout no-show reservations'
        )
        
        # Tắt scheduler khi Django tắt
        atexit.register(lambda: scheduler.shutdown())
        
        # Bắt đầu scheduler
        scheduler.start()
```

---

## 📊 Database Fields Được Cập Nhập

Khi auto-checkout xảy ra, các fields sau sẽ được cập nhập:

| Field | Giá trị |
|-------|--------|
| `is_checked_out` | `True` |
| `checkout_at` | Timestamp hiện tại |
| `actual_check_out_date` | Ngày hôm nay (check-in date) |
| `is_canceled` | `True` |
| `canceled_at` | Timestamp hiện tại |
| `canceled_reason` | `'no_show_auto_cancel'` |

**Room Status Update:**
- Phòng tự động trở thành **"CÓ SẴN"** vì:
  - `is_checked_out = True` ✓
  - `check_out_date` đã qua ✓
  - Không còn overlapping reservations

---

## 📧 Email Notifications

### Email cho Admin:
```
Subject: Auto-cancelled booking BK000123 (no-show)

Content:
Reservation BK000123 (id=123) was auto-checked-out and cancelled due to no-show on 2026-05-06.
Guest: Mong Mo - mong.mo@example.com
Room: Room 302 - Deluxe
Room status has been updated to AVAILABLE.
```

### Email cho Khách:
```
Subject: Booking BK000123 đã bị hủy (không tới)

Content:
Chào Mong,

Đặt phòng BK000123 đã được tự động check-out và hủy vì không nhận phòng đúng ngày (2026-05-06).

Phòng: Room 302 - Deluxe
Trạng thái phòng đã được cập nhật thành CÓ SẴN.

Nếu có thắc mắc, vui lòng liên hệ với chúng tôi.
```

---

## 🧪 Test Feature

### 1. Test Thủ Công (Không cần chờ giờ thực tế)

**Bước 1:** Tạo một Reservation:
- Check-in date: Hôm nay
- Guest: Chưa check-in
- Payment status: Pending

**Bước 2:** Chạy command:
```bash
python manage.py auto_cancel_no_shows
```

**Bước 3:** Kiểm tra:
```bash
# Kiểm tra trong shell Django
python manage.py shell

>>> from rooms.models import Reservation
>>> res = Reservation.objects.get(id=123)
>>> print(f"is_checked_out: {res.is_checked_out}")
>>> print(f"is_canceled: {res.is_canceled}")
>>> print(f"checkout_at: {res.checkout_at}")
>>> print(f"canceled_at: {res.canceled_at}")
```

**Expected Output:**
```
is_checked_out: True
is_canceled: True
checkout_at: 2026-05-06 14:30:45.123456+00:00
canceled_at: 2026-05-06 14:30:45.123456+00:00
```

### 2. Test với Logging

Thêm logging để tracking:

```python
# In settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'auto_checkout.log',
        },
    },
    'loggers': {
        'rooms': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

---

## ⚙️ Cấu hình Nâng Cao

### Thay đổi Grace Period

Mặc định: 6 giờ

```python
# In settings.py
NO_SHOW_GRACE_HOURS = 8  # Thay thành 8 giờ
```

### Thay đổi Check-in Time

Mặc định: 08:00

```python
# In settings.py
DEFAULT_CHECK_IN_TIME = '14:00'  # Check-in lúc 2 chiều
```

---

## 📋 Checklist Triển Khai

- [ ] Đã cập nhập `auto_cancel_no_shows.py`
- [ ] Cấu hình `DEFAULT_CHECK_IN_TIME` trong settings.py
- [ ] Cấu hình `NO_SHOW_GRACE_HOURS` trong settings.py
- [ ] Chọn 1 phương pháp scheduling (Cron / Task Scheduler / APScheduler / Celery)
- [ ] Cài đặt scheduling cho phương pháp đã chọn
- [ ] Test thủ công với 1 Reservation
- [ ] Xác nhận email thông báo được gửi
- [ ] Monitor logs trong 1 tuần đầu
- [ ] Adjust grace period nếu cần

---

## 🔍 Troubleshooting

### Email không được gửi?
- Kiểm tra `settings.EMAIL_BACKEND` và `DEFAULT_FROM_EMAIL`
- Kiểm tra SMTP settings (host, port, user, password)

### Command không chạy scheduled?
- Kiểm tra cron job status: `sudo service cron status`
- Kiểm tra Task Scheduler logs (Windows)
- Kiểm tra Celery logs

### Room status vẫn còn "Đã đặt"?
- Xác nhận `is_checked_out = True` được set
- Check query: `Room.availability_status` property

---

## 📞 Support

Nếu có vấn đề, kiểm tra:
1. Logs từ auto-checkout command
2. Database: `is_checked_out` field có `True` không
3. Email settings có correct không
4. Check-in date có correct không

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-06 | Initial implementation - Auto-checkout + Auto-cancel + Room status update |

