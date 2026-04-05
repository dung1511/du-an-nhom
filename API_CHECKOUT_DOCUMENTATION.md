# API Tài Liệu - Chức Năng Trả Phòng (Checkout)

## Tổng Quan

API trả phòng cho phép khách hàng hoàn thành quá trình trả phòng. Tất cả các endpoints đều yêu cầu xác thực (authentication).

---

## Endpoints

### 1. Lấy Danh Sách Đặt Phòng

**Endpoint:** `GET /rooms/api/reservations/`

**Quyền Truy Cập:** `IsAuthenticated`

**Mô Tả:** Lấy danh sách tất cả các đặt phòng của người dùng đã đăng nhập.

**Ví Dụ Request:**
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/rooms/api/reservations/
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "room_name": "Deluxe Room",
    "room_price": "150.00",
    "check_in_date": "2024-04-10",
    "check_out_date": "2024-04-12",
    "num_nights": 2,
    "adults": 2,
    "children": 0,
    "first_name": "Nguyễn",
    "last_name": "Văn A",
    "email": "nguyenvana@example.com",
    "phone": "0123456789",
    "address": "123 Đường A",
    "city": "Hà Nội",
    "state": "Hà Nội",
    "postcode": "100000",
    "subtotal": "300.00",
    "gst": "54.00",
    "discount_applied": "0.00",
    "total": "354.00",
    "payment_method": "cards",
    "is_checked_out": false,
    "created_at": "2024-04-01T10:30:00Z"
  }
]
```

---

### 2. Xem Chi Tiết Đặt Phòng

**Endpoint:** `GET /rooms/api/reservations/{id}/`

**Quyền Truy Cập:** `IsAuthenticated`

**Mô Tả:** Xem chi tiết của một đặt phòng cụ thể.

**Tham Số:**
- `id` (integer, required): ID của đặt phòng

**Ví Dụ Request:**
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/rooms/api/reservations/1/
```

**Response (200 OK):**
```json
{
  "id": 1,
  "room_name": "Deluxe Room",
  "room_price": "150.00",
  "check_in_date": "2024-04-10",
  "check_out_date": "2024-04-12",
  "num_nights": 2,
  "adults": 2,
  "children": 0,
  "first_name": "Nguyễn",
  "last_name": "Văn A",
  "email": "nguyenvana@example.com",
  "phone": "0123456789",
  "address": "123 Đường A",
  "city": "Hà Nội",
  "state": "Hà Nội",
  "postcode": "100000",
  "subtotal": "300.00",
  "gst": "54.00",
  "discount_applied": "0.00",
  "total": "354.00",
  "payment_method": "cards",
  "is_checked_out": false,
  "created_at": "2024-04-01T10:30:00Z"
}
```

---

### 3. Trả Phòng (Checkout)

**Endpoint:** `PUT /rooms/api/reservations/{id}/checkout/`

**Quyền Truy Cập:** `IsAuthenticated`

**Mô Tả:** Đánh dấu phòng là đã trả (checkout).

**Tham Số:**
- `id` (integer, required): ID của đặt phòng

**Điều Kiện Thực Hiện:**
- Phòng chưa được trả trước đó (`is_checked_out` = `false`)
- Ngày hiện tại phải >= ngày trả phòng dự kiến
- Người yêu cầu phải là chủ sở hữu của đặt phòng

**Ví Dụ Request:**
```bash
curl -X PUT \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/rooms/api/reservations/1/checkout/
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Trả phòng Deluxe Room thành công!",
  "reservation": {
    "id": 1,
    "room_name": "Deluxe Room",
    "check_in_date": "2024-04-10",
    "check_out_date": "2024-04-12",
    "checkout_date": "2024-04-12",
    "user": 1,
    "first_name": "Nguyễn",
    "last_name": "Văn A",
    "email": "nguyenvana@example.com",
    "phone": "0123456789",
    "total": "354.00",
    "is_checked_out": true
  }
}
```

**Error Response (400 Bad Request) - Phòng Đã Trả:**
```json
{
  "error": "Phòng này đã được trả rồi."
}
```

**Error Response (400 Bad Request) - Chưa Đến Ngày Trả:**
```json
{
  "error": "Chưa đến ngày trả phòng (2024-04-12). Vui lòng quay lại vào ngày hết hạn."
}
```

**Error Response (403 Forbidden):**
```json
{
  "detail": "Không có quyền truy cập đặt phòng này."
}
```

---

### 4. Tạo Đơn Đặt Phòng

**Endpoint:** `POST /rooms/api/bookings/`

**Quyền Truy Cập:** `IsAuthenticated`

**Mô Tả:** Tạo một đơn đặt phòng mới.

**Request Body:**
```json
{
  "room_id": 1,
  "check_in_date": "2024-04-10",
  "check_out_date": "2024-04-12",
  "adults": 2,
  "children": 0,
  "first_name": "Nguyễn",
  "last_name": "Văn A",
  "email": "nguyenvana@example.com",
  "phone": "0123456789",
  "address": "123 Đường A",
  "city": "Hà Nội",
  "state": "Hà Nội",
  "postcode": "100000",
  "adhar_id": "123456789",
  "payment_method": "cards",
  "coupon_code": ""
}
```

**Response (201 Created):**
```json
{
  "id": 2,
  "room": 1,
  "check_in_date": "2024-04-10",
  "check_out_date": "2024-04-12",
  "adults": 2,
  "children": 0,
  "first_name": "Nguyễn",
  "last_name": "Văn A",
  "email": "nguyenvana@example.com",
  "phone": "0123456789",
  "address": "123 Đường A",
  "city": "Hà Nội",
  "state": "Hà Nội",
  "postcode": "100000",
  "adhar_id": "123456789",
  "note": "",
  "payment_method": "cards",
  "subtotal": "300.00",
  "gst": "54.00",
  "discount_applied": "0.00",
  "total": "354.00",
  "created_at": "2024-04-01T10:30:00Z"
}
```

---

## Lỗi Chung

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Nguyên Nhân:** Token xác thực không được cung cấp hoặc không hợp lệ.

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

**Nguyên Nhân:** Đặt phòng với ID được chỉ định không tồn tại.

---

## Ví Dụ Sử Dụng

### JavaScript (Fetch API)

#### Lấy Danh Sách Đặt Phòng
```javascript
const token = 'YOUR_TOKEN_HERE';

fetch('http://localhost:8000/rooms/api/reservations/', {
  method: 'GET',
  headers: {
    'Authorization': `Token ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
```

#### Trả Phòng
```javascript
const reservationId = 1;
const token = 'YOUR_TOKEN_HERE';

fetch(`http://localhost:8000/rooms/api/reservations/${reservationId}/checkout/`, {
  method: 'PUT',
  headers: {
    'Authorization': `Token ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => {
  if (data.success) {
    console.log('Checkout thành công:', data.message);
  } else {
    console.log('Lỗi:', data.error);
  }
})
.catch(error => console.error('Error:', error));
```

### Python (Requests Library)

#### Lấy Danh Sách Đặt Phòng
```python
import requests

token = 'YOUR_TOKEN_HERE'
headers = {'Authorization': f'Token {token}'}

response = requests.get(
    'http://localhost:8000/rooms/api/reservations/',
    headers=headers
)

print(response.json())
```

#### Trả Phòng
```python
import requests

token = 'YOUR_TOKEN_HERE'
reservation_id = 1
headers = {'Authorization': f'Token {token}'}

response = requests.put(
    f'http://localhost:8000/rooms/api/reservations/{reservation_id}/checkout/',
    headers=headers
)

result = response.json()
if result.get('success'):
    print(result['message'])
else:
    print(result.get('error'))
```

---

## Status Code

| Code | Ý Nghĩa |
|------|---------|
| 200 | OK - Yêu cầu thành công |
| 201 | Created - Tài nguyên được tạo thành công |
| 400 | Bad Request - Dữ liệu không hợp lệ |
| 401 | Unauthorized - Không được xác thực |
| 403 | Forbidden - Không có quyền truy cập |
| 404 | Not Found - Tài nguyên không tìm thấy |
| 500 | Internal Server Error - Lỗi máy chủ |

---

## Ghi Chú

1. **Token Authentication**: Đảm bảo bạn có token hợp lệ. Nếu chưa có, hãy sử dụng endpoint login.

2. **Date Format**: Tất cả các ngày phải ở định dạng `YYYY-MM-DD`.

3. **Timezone**: Ngày được so sánh với ngày hiện tại trên máy chủ (UTC).

4. **Checkout Date Validation**: Không thể trả phòng trước ngày trả phòng dự kiến.

5. **User Restriction**: Người dùng chỉ có thể truy cập các đặt phòng của chính họ.

---

## Troubleshooting

### Lỗi "Không có quyền truy cập"
- Kiểm tra xem token có hợp lệ không
- Kiểm tra xem đặt phòng có thuộc về người dùng đó không

### Lỗi "Phòng đã được trả rồi"
- Phòng này đã được checkout trước đó
- Không thể checkout lại

### Lỗi "Chưa đến ngày trả phòng"
- Ngày hiện tại phải >= ngày trả phòng dự kiến
- Vui lòng thử lại vào hoặc sau ngày trả phòng
