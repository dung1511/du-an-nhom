# Auto-Checkout Feature - Settings Configuration

## 📝 Thêm vào `quanlykhachsannn/settings.py`

Thêm 2 cấu hình này vào file settings.py (có thể thêm vào cuối file hoặc phần app-specific):

```python
# ============================================================================
# AUTO-CHECKOUT & AUTO-CANCEL NO-SHOW CONFIGURATION
# ============================================================================

# Giờ check-in mặc định (format HH:MM)
# - Dùng để tính thời điểm auto-cancel
# - Mặc định: 08:00 (8 giờ sáng)
# - Ví dụ: DEFAULT_CHECK_IN_TIME = '14:00' (2 chiều)
DEFAULT_CHECK_IN_TIME = '08:00'

# Thời gian chờ trước khi tự động hủy (tính bằng giờ)
# - Auto-cancel = check_in_time + grace_hours
# - Mặc định: 6 giờ
# - Ví dụ: Check-in 08:00 + grace 6 giờ = tự động cancel lúc 14:00 nếu chưa check-in
NO_SHOW_GRACE_HOURS = 6

# ============================================================================
```

### 🎯 Ví dụ đầy đủ:

```python
# At the end of settings.py

# ============================================================================
# AUTO-CHECKOUT & AUTO-CANCEL NO-SHOW CONFIGURATION
# ============================================================================

DEFAULT_CHECK_IN_TIME = '08:00'  # Check-in starts at 08:00 AM
NO_SHOW_GRACE_HOURS = 6          # Auto-cancel after 6 hours of grace period

# ============================================================================
```

---

## 🧪 Kiểm tra cấu hình

Chạy Python shell để verify settings được load đúng:

```bash
python manage.py shell

>>> from django.conf import settings
>>> print(f"DEFAULT_CHECK_IN_TIME: {settings.DEFAULT_CHECK_IN_TIME}")
>>> print(f"NO_SHOW_GRACE_HOURS: {settings.NO_SHOW_GRACE_HOURS}")
```

**Expected Output:**
```
DEFAULT_CHECK_IN_TIME: 08:00
NO_SHOW_GRACE_HOURS: 6
```

---

## 📅 Scheduling Setup (Chọn 1 cách)

### Quick Start - Linux/Mac (Cron)

```bash
# Edit crontab
crontab -e

# Add this line (runs every hour at minute 0)
0 * * * * cd /path/to/project && /usr/bin/python3 manage.py auto_cancel_no_shows >> /var/log/auto_checkout.log 2>&1
```

### Quick Start - Windows (Task Scheduler)

1. Open `Task Scheduler`
2. Create Basic Task → Name: "Hotel Auto-Checkout"
3. Trigger: Daily, Time: 09:00, Repeat: Every 1 hour
4. Action: Start program
   - Program: `C:\Python\python.exe`
   - Arguments: `manage.py auto_cancel_no_shows`
   - Start in: `C:\path\to\project`

---

## 🚀 Run Now (Manual Test)

```bash
python manage.py auto_cancel_no_shows
```

---

## ✅ Checklist

- [ ] Added `DEFAULT_CHECK_IN_TIME` to settings.py
- [ ] Added `NO_SHOW_GRACE_HOURS` to settings.py
- [ ] Ran `python manage.py shell` to verify settings
- [ ] Set up scheduling (Cron / Task Scheduler)
- [ ] Ran manual test: `python manage.py auto_cancel_no_shows`
- [ ] Checked for no errors in output
