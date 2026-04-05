# Hướng Dẫn Sử Dụng - Chức Năng Tìm Kiếm & Đề Xuất Phòng

## 📋 Tóm Tắt Tính Năng

Hệ thống tìm kiếm và đề xuất phòng mới cho phép:

✅ **Tìm kiếm phòng dựa trên:**
- Ngày nhận phòng & ngày trả phòng
- Số người lớn
- Số trẻ em
- Sức chứa phòng (xác nhận người lớn + trẻ em)

✅ **Đề xuất phòng thông minh:**
- Sắp xếp theo độ phù hợp nhất (phòng nhỏ nhất vừa đủ)
- Giá rẻ nhất trong nhóm phù hợp
- Giới hạn số lượng đề xuất (tối đa 10)

✅ **API RESTful:**
- Dễ tích hợp vào ứng dụng mobile/web
- Hỗ trợ JSON
- Xử lý lỗi chi tiết

---

## 🚀 Cách Sử Dụng

### 1. **API Endpoint**

#### Tìm Kiếm Phòng
```
POST /rooms/api/rooms/search/
```

**Request:**
```json
{
  "check_in_date": "2024-04-10",
  "check_out_date": "2024-04-12",
  "adults": 2,
  "children": 1,
  "limit": 5
}
```

**Response:**
```json
{
  "success": true,
  "search_criteria": {
    "check_in_date": "2024-04-10",
    "check_out_date": "2024-04-12",
    "adults": 2,
    "children": 1,
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
        "num_nights": 2,
        "subtotal": "300.00",
        "gst": "54.00",
        "total": "354.00"
      },
      // ... phòng khác
    ]
  },
  "message": "Tìm thấy 2 phòng phù hợp cho 3 khách."
}
```

### 2. **Giao Diện Web Demo**

Truy cập: `/templates/rooms/room_search_demo.html`

- Giao diện đẹp, tương thích mobile
- Hiển thị kết quả real-time
- Tính giá tự động (bao gồm GST 18%)

### 3. **Sử Dụng via curl**

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

### 4. **Sử Dụng via JavaScript**

```javascript
const searchData = {
  check_in_date: "2024-04-10",
  check_out_date: "2024-04-12",
  adults: 2,
  children: 1,
  limit: 5
};

fetch('http://localhost:8000/rooms/api/rooms/search/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(searchData)
})
.then(response => response.json())
.then(data => {
  console.log(`Tìm thấy ${data.results.count} phòng`);
  data.results.rooms.forEach(room => {
    console.log(`${room.name}: ${room.total} VND`);
  });
});
```

### 5. **Sử Dụng via Python**

```python
import requests

response = requests.post(
  'http://localhost:8000/rooms/api/rooms/search/',
  json={
    'check_in_date': '2024-04-10',
    'check_out_date': '2024-04-12',
    'adults': 2,
    'children': 1,
    'limit': 5
  }
)

data = response.json()
for room in data['results']['rooms']:
  print(f"{room['name']}: {room['total']} VND")
```

---

## 📊 Ví Dụ Thực Tế

### Ví Dụ 1: Tìm phòng cho 5 khách (2 người lớn + 3 trẻ em)

```json
{
  "check_in_date": "2024-04-20",
  "check_out_date": "2024-04-23",
  "adults": 2,
  "children": 3,
  "limit": 2
}
```

**Kết quả đề xuất:**
1. Family Suite (6 người) - 400K/đêm
2. Premium Family Room (5 người) - 350K/đêm

### Ví Dụ 2: Tìm phòng cho cặp đôi (2 người lớn)

```json
{
  "check_in_date": "2024-04-10",
  "check_out_date": "2024-04-12",
  "adults": 2,
  "children": 0,
  "limit": 5
}
```

**Kết quả đề xuất:**
1. Double Bedroom (2 người)
2. Deluxe Room (4 người)
3. Suite (4 người)
4. Family Suite (6 người)
5. Premium Family Room (5 người)

### Ví Dụ 3: Tìm phòng cho 1 khách

```json
{
  "check_in_date": "2024-04-15",
  "check_out_date": "2024-04-16",
  "adults": 1,
  "children": 0,
  "limit": 3
}
```

**Kết quả đề xuất:**
1. Single Room (1 người) - 100K/đêm
2. Double Bedroom (2 người) - 150K/đêm
3. Deluxe Room (4 người) - 150K/đêm

---

## 🔧 Điều Chỉnh Tùy Chỉnh

### Thay Đổi Sắp Xếp Kết Quả

Hiện tại sắp xếp theo:
1. Dung tích nhỏ nhất (phòng tối nhất vừa đủ)
2. Giá rẻ nhất

**Để thay đổi**, sửa trong `rooms/models.py`:
```python
# Sắp xếp theo giá thay vì dung tích
suitable_rooms = suitable_rooms.order_by('price', 'total_capacity')
```

### Thay Đổi Giới Hạn Số Phòng Đề Xuất

**Default:** 5 phòng
**Max:** 10 phòng

**Để thay đổi**, sửa trong `rooms/serializers.py`:
```python
class RoomSearchSerializer(serializers.Serializer):
    limit = serializers.IntegerField(min_value=1, max_value=20, required=False, default=10)
```

### Thay Đổi Tỷ Lệ GST

**Hiện tại:** 18%

**Để thay đổi**, sửa trong `rooms/views.py`:
```python
'gst': str(room.price * num_nights * Decimal('0.15')),  # 15% GST
```

---

## 📁 File Tạo Mới

| File | Mô Tả |
|------|-------|
| `API_ROOM_SEARCH_DOCUMENTATION.md` | Tài liệu API chi tiết |
| `room_search_demo.html` | Giao diện web demo |
| `INSTALLATION_GUIDE.md` | Hướng dẫn cài đặt (file này) |

---

## ✨ Cải Tiến RoomManager

### Phương Thức Cũ: `available_rooms()`
```python
def available_rooms(self, check_in, check_out, adults):
    # Chỉ check capacity >= adults
    return self.filter(capacity__gte=adults).exclude(id__in=reserved_rooms)
```

### Phương Thức Mới: `search_suitable_rooms()`
```python
def search_suitable_rooms(self, check_in, check_out, adults, children=0, limit=None):
    # Check:
    # - total_capacity >= (adults + children)
    # - capacity_adults >= adults
    # - capacity_children >= children
    # Sắp xếp: Phòng nhỏ nhất + rẻ nhất
    # Giới hạn: limit phòng
```

---

## 🔍 Tiêu Chí Kiếm Kiếm Chi Tiết

### 1. Phòng Trống
```
Không được đặt (is_checked_out=False) trong khoảng:
check_in_date < check_out_date và
check_out_date > check_in_date
```

### 2. Sức Chứa
```
- total_capacity >= (adults + children)
- capacity_adults >= adults
- capacity_children >= children

Ví dụ: Tìm 2 người lớn + 2 trẻ em = 4 khách
-> Phòng phải có:
   - total_capacity >= 4
   - capacity_adults >= 2
   - capacity_children >= 2
```

### 3. Sắp Xếp
```
ORDER BY total_capacity, price

Ví dụ:
1. Phòng 4 người - 150K (phù hợp nhất + rẻ)
2. Phòng 5 người - 180K
3. Phòng 6 người - 200K
```

---

## 🐛 Xử Lý Lỗi

| Lỗi | Nguyên Nhân | Giải Pháp |
|-----|----------|----------|
| "Ngày nhận phòng không được nhỏ hơn hôm nay" | Chọn ngày trong quá khứ | Chọn ngày hiện tại hoặc tương lai |
| "Ngày trả phòng phải sau ngày nhận phòng" | check_out <= check_in | Đảm bảo check_out > check_in |
| "Số người lớn phải >= 1" | adults = 0 | Chọn >= 1 người lớn |
| "Tổng số khách không được vượt quá 10" | adults + children > 10 | Giảm số khách xuống <= 10 |
| 404 Not Found | Endpoint sai | Dùng: `/rooms/api/rooms/search/` |

---

## 📈 Quy Trình Tìm Kiếm

```
Request → Validate → Search DB → Sort → Format → Response
  ↓         ↓          ↓        ↓      ↓        ↓
Input     Check     Find     Sort   Add      JSON
Data      Valid    Rooms    By    Price     Output
          Date     &      Size    Info
          Limit   Check
          Guest   Empty
          Num
```

---

## 💡 Mẹo Sử Dụng

1. **Để có kết quả tốt nhất:** Luôn chỉ định cả `adults` và `children`
2. **Để tiết kiệm bandwidth:** Giảm `limit` xuống 2-3
3. **Để tìm phòng rẻ:** Kiếm cùng lúc và so sánh giá
4. **Để debug:** Kiểm tra response có `success: true` không

---

## 🔐 Bảo Mật

- ✅ Xác thực không bắt buộc cho tìm kiếm (public API)
- ✅ Validate dữ liệu input
- ✅ Lọc phòng đã trả (is_checked_out=False)
- ✅ SQL injection protection (Django ORM)

---

## 📞 Hỗ Trợ

### Câu Hỏi Thường Gặp

**Q: API này có hỗ trợ authentication không?**
A: Hiện tại không (AllowAny), nhưng có thể thêm trong tương lai bằng cách thay `permission_classes = [permissions.IsAuthenticated]`

**Q: Giữ liệu được cache không?**
A: Không, mỗi request đều query database trực tiếp

**Q: Có thể sắp xếp theo danh mục (category) không?**
A: Chưa, nhưng có thể thêm tham số `category` vào request nếu cần

**Q: Rate limiting có không?**
A: Không hiện tại, nên thêm nếu dự kiến traffic cao

---

## 🎯 Bước Tiếp Theo

- [ ] Thêm authentication vào search API
- [ ] Thêm filter theo category
- [ ] Thêm filter theo price range
- [ ] Thêm cache để optimize performance
- [ ] Thêm rate limiting
- [ ] Thêm analytics/logs cho search patterns

---

## 📝 Ghi Chú

- Tất cả ngày phải ở định dạng `YYYY-MM-DD`
- GST mặc định là 18%
- Timezone: Server sử dụng UTC
- Phòng được sắp xếp theo độ phù hợp tối ưu nhất
