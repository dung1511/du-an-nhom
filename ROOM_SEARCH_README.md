# 🏨 API Tìm Kiếm & Đề Xuất Phòng - Tóm Tắt

## ✨ Những Gì Mới Được Tạo

### 1️⃣ API Endpoint Mới

```
POST /rooms/api/rooms/search/
```

**Tính Năng:**
- 🔍 Tìm kiếm phòng theo ngày & số lượng khách
- 👥 Hỗ trợ người lớn (adults) + trẻ em (children)
- ⭐ Đề xuất phòng phù hợp nhất (sắp xếp tối ưu)
- 💰 Tính giá tự động (bao gồm GST 18%)

### 2️⃣ Request Example

```json
{
  "check_in_date": "2024-04-10",
  "check_out_date": "2024-04-12",
  "adults": 2,
  "children": 1,
  "limit": 2
}
```

### 3️⃣ Response Example

```json
{
  "success": true,
  "search_criteria": {
    "total_guests": 3,
    "num_nights": 2
  },
  "results": {
    "count": 2,
    "rooms": [
      {
        "id": 1,
        "name": "Deluxe Room",
        "capacity_adults": 2,
        "capacity_children": 2,
        "total_capacity": 4,
        "price": "150.00",
        "total": "354.00"  // Bao gồm giá + GST
      },
      {
        "id": 3,
        "name": "Family Suite",
        "capacity_adults": 3,
        "capacity_children": 3,
        "total_capacity": 6,
        "price": "200.00",
        "total": "472.00"
      }
    ]
  },
  "message": "Tìm thấy 2 phòng phù hợp cho 3 khách."
}
```

---

## 🎯 Ví Dụ Thực Tế

### Tìm phòng cho 5 khách (2 người lớn + 3 trẻ em)

```javascript
fetch('http://localhost:8000/rooms/api/rooms/search/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    check_in_date: "2024-04-20",
    check_out_date: "2024-04-23",
    adults: 2,
    children: 3,
    limit: 2
  })
})
.then(r => r.json())
.then(data => {
  console.log(`✅ Tìm thấy ${data.results.count} phòng:`);
  data.results.rooms.forEach(room => {
    console.log(`• ${room.name}: ${room.total} VND`);
  });
});
```

**Kết quả:**
```
✅ Tìm thấy 2 phòng:
• Family Suite: 1,416,000 VND (3 đêm)
• Premium Family Room: 1,240,500 VND (3 đêm)
```

---

## 📊 Logic Tìm Kiếm

```
1. Validate Input
   ✓ check_in >= hôm nay
   ✓ check_out > check_in
   ✓ adults >= 1
   ✓ total_guests <= 10

2. Search Database
   ✓ total_capacity >= (adults + children)
   ✓ capacity_adults >= adults
   ✓ capacity_children >= children
   ✓ Phòng không được đặt trong khoảng thời gian

3. Sort Results
   ✓ Phòng nhỏ nhất vừa đủ (smallest fit)
   ✓ Giá rẻ nhất

4. Calculate Price
   ✓ subtotal = price × num_nights
   ✓ gst = subtotal × 18%
   ✓ total = subtotal + gst

5. Return Data
   ✓ JSON response
   ✓ Limited to 2-10 rooms
```

---

## 🔧 Cách Sử Dụng

### Via Python

```python
import requests

response = requests.post(
  'http://localhost:8000/rooms/api/rooms/search/',
  json={
    'check_in_date': '2024-04-10',
    'check_out_date': '2024-04-12',
    'adults': 2,
    'children': 0,
    'limit': 5
  }
)

data = response.json()
for room in data['results']['rooms']:
  print(f"{room['name']}: {room['total']} VND")
```

### Via JavaScript

```javascript
const searchData = {
  check_in_date: "2024-04-10",
  check_out_date: "2024-04-12",
  adults: 2,
  limit: 3
};

const response = await fetch('/rooms/api/rooms/search/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(searchData)
});

const data = await response.json();
console.log(data.message);
```

### Via cURL

```bash
curl -X POST http://localhost:8000/rooms/api/rooms/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "check_in_date": "2024-04-10",
    "check_out_date": "2024-04-12",
    "adults": 2,
    "limit": 5
  }'
```

---

## 📁 File Tài Liệu

| File | Nội Dung |
|------|---------|
| `API_ROOM_SEARCH_DOCUMENTATION.md` | 📚 Tài liệu chi tiết (endpoint, errors, examples) |
| `room_search_demo.html` | 🎨 Demo giao diện web (responsive, mobile) |
| `INSTALLATION_GUIDE.md` | 📖 Hướng dẫn sử dụng & tuỳ chỉnh |
| `API_CHECKOUT_DOCUMENTATION.md` | 📝 API checkout phòng (từ session trước) |

---

## 🏗️ Thay Đổi Code

### Model Changes (`models.py`)
```python
# Thêm method mới
def search_suitable_rooms(self, check_in, check_out, adults, children=0, limit=None):
  # Tìm phòng phù hợp
  # Sắp xếp theo: total_capacity, price
  # Trả về QuerySet
```

### Serializers (`serializers.py`)
```python
# Thêm
- RoomSerializer: Thông tin phòng
- RoomSearchSerializer: Validate input tìm kiếm
```

### Views (`views.py`)
```python
# Thêm
- RoomSearchAPIView: POST endpoint
```

### URLs (`urls.py`)
```python
path('api/rooms/search/', views.RoomSearchAPIView.as_view(), name='api_rooms_search'),
```

---

## ✅ Test API

### Test Case 1: Tìm 2 người

```bash
curl -X POST http://localhost:8000/rooms/api/rooms/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "check_in_date": "2024-04-10",
    "check_out_date": "2024-04-12",
    "adults": 2,
    "limit": 5
  }'
```

### Test Case 2: Tìm 3 người (gia đình)

```bash
curl -X POST http://localhost:8000/rooms/api/rooms/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "check_in_date": "2024-04-10",
    "check_out_date": "2024-04-12",
    "adults": 2,
    "children": 1,
    "limit": 2
  }'
```

### Test Case 3: Ngày không hợp lệ

```bash
curl -X POST http://localhost:8000/rooms/api/rooms/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "check_in_date": "2020-01-01",
    "check_out_date": "2020-01-02",
    "adults": 1,
    "limit": 5
  }'
```

**Response:**
```json
{
  "errors": {
    "check_in_date": ["Ngày nhận phòng không được nhỏ hơn hôm nay."]
  }
}
```

---

## 💡 Mẹo & Trickss

| Mẹo | Mô Tả |
|-----|-------|
| 🎯 Độ chính xác | Luôn chỉ định `children` để có kết quả tốt nhất |
| ⚡ Speed | Giảm `limit` xuống 2-3 để query nhanh hơn |
| 💰 Giá rẻ | API tự sắp xếp theo giá, không cần sort lại |
| 📱 Mobile | Dùng demo HTML có responsive design |
| 🔄 Integration | Copy code từ docs vào ứng dụng |

---

## 🐛 Troubleshooting

### Lỗi: "Không tìm thấy phòng"
- ✅ Kiểm tra có phòng trống không
- ✅ Kiểm tra sức chứa có phù hợp không
- ✅ Thử ngày khác

### Lỗi: "Ngày không hợp lệ"
- ✅ Sử dụng định dạng `YYYY-MM-DD`
- ✅ Ngày phải >= hôm nay
- ✅ check_out > check_in

### Lỗi: 404 Not Found
- ✅ URL phải là `/rooms/api/rooms/search/`
- ✅ Method phải là `POST`
- ✅ Headers phải có `Content-Type: application/json`

---

## 📈 Sắp Tới

- ✏️ Thêm filter theo category
- ✏️ Thêm filter theo price range
- ✏️ Thêm authentication
- ✏️ Thêm cache/caching
- ✏️ Thêm rate limiting

---

## 📞 Support

**Tài Liệu:**
- 📚 Đầy đủ: `API_ROOM_SEARCH_DOCUMENTATION.md`
- 📖 Cài đặt: `INSTALLATION_GUIDE.md`
- 🎨 Demo: `room_search_demo.html`

**Sử dụng:**
- ✅ cURL, JavaScript, Python examples
- ✅ HTML form input validation
- ✅ Xử lý lỗi chi tiết

---

## 🎉 Summary

Bạn đã có một API tìm kiếm & đề xuất phòng **hoàn chỉnh** với:

✅ Logic tìm kiếm thông minh (đề xuất phòng phù hợp nhất)
✅ Validation input toàn diện
✅ Tính giá tự động
✅ Giao diện demo responsive
✅ Tài liệu chi tiết
✅ Ví dụ code sử dụng

**Bắt đầu dùng ngay!** 🚀

```bash
POST /rooms/api/rooms/search/
```
