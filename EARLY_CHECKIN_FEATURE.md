# Early Check-in Feature Documentation

## Overview
Guests can now check-in before their scheduled check-in date and will be charged an additional fee based on the number of early days.

## Features

### 1. **Early Check-in Policy**
- Guests can check-in up to **7 days early** from the scheduled check-in date
- Each day of early check-in is charged at **50% of the daily room rate**
- Early check-in fee is automatically calculated and added to the final bill

### 2. **Pricing Formula**
```
Early Check-in Fee = (Room Daily Rate × 0.50) × Number of Early Days

Example:
- Room Rate: 1,000,000 VND/night
- Check-in Date: May 10
- Actual Check-in Date: May 8 (2 days early)
- Early Check-in Fee = (1,000,000 × 0.50) × 2 = 1,000,000 VND
```

### 3. **API Endpoint**

#### Check-in with Early Date
```
POST /api/reservations/checkin/

Request Body:
{
    "booking_code": "BK000123",
    "checked_in_adults": 2,
    "checked_in_children": 0,
    "actual_check_in_date": "2026-05-08"  // Optional field
}

Response:
{
    "success": true,
    "message": "Check-in thành công cho booking BK000123. Check-in sớm 2 ngày. Phí check-in sớm: 1000000.00 VND.",
    "booking_code": "BK000123",
    "guest_name": "John Doe",
    "room": "Deluxe Room",
    "checked_in_guests": 2,
    "early_checkin_days": 2,
    "early_checkin_fee": "1000000.00",
    "amount_due_collected": "500000.00",
    "final_total": "3500000.00",
    "payment_status": "paid"
}
```

### 4. **Validation Rules**

1. **Maximum 7 days early**: Cannot check-in more than 7 days before scheduled date
   - Error: `"Chỉ có thể check-in sớm tối đa 7 ngày (từ YYYY-MM-DD)"`

2. **Cannot check-in after scheduled date**: Actual date must be <= scheduled date
   - Error: `"Ngày check-in thực tế không được muộn hơn ngày check-in dự kiến"`

3. **Must have available rooms**: Room must be available on the early check-in date
   - Checked against existing reservations

4. **Guest capacity**: Checked-in guests cannot exceed:
   - Booked guest count
   - Room capacity

### 5. **Database Fields**

New fields added to `Reservation` model:
- **actual_check_in_date** (DateField): The actual date guest checked in
- **early_checkin_days** (PositiveIntegerField): Number of days early (0 if on-time)
- **early_checkin_fee** (DecimalField): Calculated fee for early check-in

### 6. **Reservation Invoice Impact**

When calculating `final_total`:
```
final_total = total + damage_fee + early_checkin_fee
```

The early check-in fee is included in all financial calculations and sent to the customer's email invoice.

### 7. **Admin Panel**

In Django admin (`/admin/rooms/reservation/`):
- View `actual_check_in_date` for each reservation
- See `early_checkin_days` count
- Track `early_checkin_fee` collected

### 8. **Examples**

#### Standard Check-in (No Early Days)
```json
{
    "booking_code": "BK000123",
    "checked_in_adults": 2,
    "checked_in_children": 1
}
// actual_check_in_date will default to scheduled check_in_date
// early_checkin_days = 0
// early_checkin_fee = 0
```

#### Early Check-in (3 Days Early)
```json
{
    "booking_code": "BK000456",
    "checked_in_adults": 1,
    "checked_in_children": 0,
    "actual_check_in_date": "2026-05-07"
}
// Scheduled check-in: 2026-05-10
// early_checkin_days = 3
// early_checkin_fee = calculated as (room_rate × 0.5 × 3)
```

#### Error Case - Too Early
```json
{
    "booking_code": "BK000789",
    "checked_in_adults": 2,
    "checked_in_children": 0,
    "actual_check_in_date": "2026-04-28"  // 12 days before scheduled
}
// Response: 400 Bad Request
// Error: "Chỉ có thể check-in sớm tối đa 7 ngày (từ 2026-05-02)"
```

## Model Changes

```python
class Reservation(models.Model):
    # ... existing fields ...
    
    # Early check-in fields
    actual_check_in_date = models.DateField(null=True, blank=True)
    early_checkin_days = models.PositiveIntegerField(default=0)
    early_checkin_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def calculate_early_checkin_fee(self):
        """Tính phí check-in sớm: 50% giá phòng cho mỗi ngày"""
        if not self.actual_check_in_date or not self.check_in_date:
            return Decimal('0.00')
        
        days_early = (self.check_in_date - self.actual_check_in_date).days
        if days_early <= 0:
            return Decimal('0.00')
        
        daily_rate = self.room.price
        early_fee = (daily_rate * Decimal('0.50')) * Decimal(days_early)
        return early_fee
    
    def sync_financial_fields(self):
        # ... existing logic ...
        self.early_checkin_fee = self.calculate_early_checkin_fee()
        self.final_total = self.total + self.damage_fee + self.early_checkin_fee
```

## Testing

### Test Cases

1. **Normal Check-in**
   - No early check-in date provided
   - Should use scheduled date
   - early_checkin_fee = 0

2. **Early Check-in (1 day)**
   - Provide date 1 day before
   - Should calculate 50% daily rate
   - Verify early_checkin_fee > 0

3. **Early Check-in (3 days)**
   - Provide date 3 days before
   - Should calculate 3 × (50% daily rate)
   - Verify final_total includes fee

4. **Invalid - Too Early**
   - Provide date 10 days before
   - Should reject with error message

5. **Invalid - After Scheduled**
   - Provide date after scheduled date
   - Should reject with error message

## Future Enhancements

- Configurable early check-in fee percentage
- Configurable maximum early check-in days
- Early check-in discounts for loyal customers
- Peak season early check-in surcharges
- Early check-in availability calendar
- SMS/Email notification of early check-in option
