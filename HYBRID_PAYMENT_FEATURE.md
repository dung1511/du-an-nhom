# Hybrid Payment System

## Overview
Hệ thống thanh toán hybrid cho phép khách hàng:
1. Thanh toán deposit qua QR MoMo
2. Thanh toán phần còn lại tại check-in
3. Hoặc thanh toán toàn bộ ngay qua QR hoặc tại lễ tân

## Features

### 1. **Flexible Payment Options**
Tất cả payment methods (Tiền mặt, Thẻ, UPI) đều có QR code để thanh toán qua MoMo

#### Option 1: QR Payment
- Khách chuyển khoản deposit/full qua QR MoMo
- Lệ tân confirm tiền nhận được
- Phần còn lại (nếu có) thanh toán tại check-in

#### Option 2: Cash Payment at Desk
- Thanh toán trực tiếp tại lễ tân
- Deposit + Balance due cộng lại

### 2. **Payment Breakdown**

```
Tổng tiền = Base Total + Early Check-in Fee - Early Checkout Refund
         = 5,000,000 + 1,000,000 - 0 = 6,000,000 VND

Deposit Amount (30%) = 1,800,000 VND
Balance Due = 4,200,000 VND
```

### 3. **QR Code Generation**
- Tự động tạo QR code cho tất cả booking
- QR chứa: Tên người nhận, Số MoMo, Số tiền, Mã booking
- Ví dụ:
```
MoMo payment
Receiver: Paradise Hotel
Phone: 0123456789
Amount: 6000000
Note: BK000124 - Booking Reference
```

### 4. **Database Fields**

New fields in Reservation model:
- `deposit_paid_via_qr` (DecimalField): Tiền deposit thanh toán qua QR
- `balance_paid_at_checkin` (DecimalField): Tiền còn lại thanh toán tại check-in

### 5. **Payment Flow**

#### Booking Page (bookingconfirmation.html)
1. Show payment options for all methods:
   - QR MoMo (để thanh toán deposit)
   - Tiền mặt (tại lễ tân)
   - Thẻ/UPI (hiển thị QR option)

2. Khách lựa chọn:
   - Quét QR để chuyển khoản deposit ngay
   - Hoặc thanh toán toàn bộ khi check-in

#### Frontdesk Page
1. Check payment status:
   - Tiền đã nhận qua QR (if any)
   - Tiền còn phải thu tại check-in

2. Check-in logic:
   - Xác nhận số tiền khách cần thanh toán
   - Cập nhật payment status (paid/partial/pending)

### 6. **Invoice Display**

Hóa đơn hiển thị:
```
--------- PAYMENT SUMMARY ---------
Base Total:              5,000,000 VND
Early Check-in Fee:      1,000,000 VND
Early Checkout Refund:         0 VND
                        -----------
Final Total:             6,000,000 VND

Deposit (30%):           1,800,000 VND
Remaining Balance:       4,200,000 VND

Paid via QR:             1,800,000 VND
To Pay at Check-in:      4,200,000 VND
```

### 7. **API Support**

```json
GET /rooms/api/reservations/<id>/
{
    "final_total": "6000000.00",
    "deposit_amount": "1800000.00",
    "balance_due": "4200000.00",
    "deposit_paid_via_qr": "0.00",
    "balance_paid_at_checkin": "4200000.00",
    "payment_status": "pending",
    "payment_method": "cash",
    "momo_qr_url": "https://api.qrserver.com/v1/create-qr-code/?size=280x280&data=..."
}
```

### 8. **Template Variables** (bookingconfirmation.html)

```django
{{ momo_qr_url }}           # QR code image URL
{{ momo_receiver_name }}     # Tên người nhận
{{ momo_receiver_phone }}    # Số MoMo
{{ deposit_amount }}         # Số tiền deposit
{{ balance_due }}            # Tiền còn lại
{{ final_total }}            # Tổng tiền
{{ booking_code }}           # Mã booking
{{ payment_method }}         # Phương thức thanh toán
```

## Implementation

### Changes Made:
1. **Model** (rooms/models.py):
   - Added: `deposit_paid_via_qr`, `balance_paid_at_checkin`
   
2. **Template** (bookingconfirmation.html):
   - Updated payment section to show:
     - QR Payment option (for all methods)
     - Hybrid payment explanation
     - Cash payment option
     - Payment breakdown

3. **Views** (rooms/views.py):
   - _build_momo_qr_url() already generates QR for all methods
   - Ready for payment status tracking

## Future Enhancements

1. **Payment Confirmation Email**
   - Send receipt when QR payment detected
   - Show remaining balance due

2. **Admin Payment Tracking**
   - Dashboard to see QR vs desk payments
   - Reconciliation feature

3. **Mobile Payment**
   - In-app payment gateway
   - Real-time payment status

4. **Automatic QR Payment Detection**
   - Webhook integration with MoMo API
   - Auto-update payment status
   - Notification to customer

## Testing

### Test Case 1: Full QR Payment
- Booking: 6,000,000 VND
- Customer scans QR and transfers 6,000,000 VND
- Payment Status: PAID

### Test Case 2: Partial QR + Desk Payment
- Booking: 6,000,000 VND (Deposit: 1,800,000, Balance: 4,200,000)
- Customer transfers 1,800,000 VND via QR
- Pays remaining 4,200,000 at check-in
- Payment Status: PAID

### Test Case 3: Full Desk Payment
- Booking: 6,000,000 VND
- Customer pays cash at desk
- Payment Status: PAID
