# API Tài Liệu - Tìm Kiếm và Đề Xuất Phòng

## Tổng Quan

API tìm kiếm phòng cho phép tìm kiếm các phòng phù hợp dựa trên tiêu chí: ngày nhận phòng, ngày trả phòng, số người lớn, số trẻ em. Hệ thống sẽ tự động đề xuất các phòng phù hợp được sắp xếp theo độ tối ưu nhất (phòng nhỏ nhất vừa đủ + giá rẻ nhất).

---

## Endpoint Tìm Kiếm Phòng

### Endpoint: `POST /rooms/api/rooms/search/`

**Quyền Truy Cập:** `AllowAny` (không cần xác thực)

**Mô Tả:** Tìm kiếm các phòng phù hợp và đề xuất danh sách phòng được sắp xếp tối ưu.

---

## Request

### URL
```
POST http://localhost:8000/rooms/api/rooms/search/
```

### Headers
```
Content-Type: application/json
```

### Body Parameters

| Tham Số | Kiểu | Bắt Buộc | Mô Tả | Ví Dụ |
|---------|------|---------|-------|--------|
| `check_in_date` | Date | ✅ Yes | Ngày nhận phòng (YYYY-MM-DD) | `2024-04-10` |
| `check_out_date` | Date | ✅ Yes | Ngày trả phòng (YYYY-MM-DD) | `2024-04-12` |
| `adults` | Integer | ✅ Yes | Số người lớn (≥ 1) | `2` |
| `children` | Integer | ❌ No | Số trẻ em (≥ 0, default: 0) | `1` |
| `limit` | Integer | ❌ No | Số lượng phòng đề xuất (1-10, default: 5) | `2` |

---

## Response

### Success Response (200 OK)

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
        "capacity": 4,
        "size": "D",
        "capacity_adults": 2,
        "capacity_children": 2,
        "total_capacity": 4,
        "description": "Phòng đôi sang trọng với tầm nhìn ra biển",
        "price": "150.00",
        "image": "/media/rooms/deluxe.jpg",
        "num_nights": 2,
        "subtotal": "300.00",
        "gst": "54.00",
        "total": "354.00"
      },
      {
        "id": 3,
        "name": "Family Suite",
        "capacity": 6,
        "size": "T",
        "capacity_adults": 3,
        "capacity_children": 3,
        "total_capacity": 6,
        "description": "Phòng gia đình rộng rãi với 2 phòng ngủ",
        "price": "200.00",
        "image": "/media/rooms/family.jpg",
        "num_nights": 2,
        "subtotal": "400.00",
        "gst": "72.00",
        "total": "472.00"
      }
    ]
  },
  "message": "Tìm thấy 2 phòng phù hợp cho 3 khách."
}
```

### Error Response (400 Bad Request)

```json
{
  "errors": {
    "check_in_date": [
      "Ngày nhận phòng không được nhỏ hơn hôm nay."
    ]
  }
}
```

---

## Lỗi Xác Thực

### 1. Ngày Không Hợp Lệ

**Lỗi:** Ngày nhận phòng trong quá khứ
```json
{
  "errors": {
    "check_in_date": [
      "Ngày nhận phòng không được nhỏ hơn hôm nay."
    ]
  }
}
```

### 2. Ngày Trả Phòng Không Hợp Lệ

**Lỗi:** Ngày trả phòng trước hoặc bằng ngày nhận phòng
```json
{
  "errors": {
    "check_out_date": [
      "Ngày trả phòng phải sau ngày nhận phòng."
    ]
  }
}
```

### 3. Số Người Không Hợp Lệ

**Lỗi:** Số người lớn bằng 0
```json
{
  "errors": {
    "adults": [
      "Số người lớn phải >= 1."
    ]
  }
}
```

### 4. Tổng Số Khách Vượt Quá Giới Hạn

**Lỗi:** Tổng số khách (adults + children) > 10
```json
{
  "errors": {
    "non_field_errors": [
      "Tổng số khách không được vượt quá 10 người."
    ]
  }
}
```

---

## Tiêu Chí Tìm Kiếm

### 1. **Phòng Trống**
   - Phòng không được đặt trong khoảng thời gian check-in → check-out

### 2. **Sức Chứa Phù Hợp**
   - `total_capacity >= total_guests` (tổng sức chứa)
   - `capacity_adults >= adults` (sức chứa người lớn)
   - `capacity_children >= children` (sức chứa trẻ em)

### 3. **Sắp Xếp Kết Quả**
   - **Ưu tiên 1:** Phòng nhỏ nhất vừa đủ (total_capacity)
   - **Ưu tiên 2:** Giá rẻ nhất

---

## Ví Dụ Sử Dụng

### JavaScript (Fetch API)

#### Ví Dụ 1: Tim kiếm cho 2 người lớn

```javascript
const searchData = {
  check_in_date: "2024-04-10",
  check_out_date: "2024-04-12",
  adults: 2,
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
  if (data.success) {
    console.log(`Tìm thấy ${data.results.count} phòng`);
    data.results.rooms.forEach(room => {
      console.log(`${room.name}: ${room.total} VND`);
    });
  }
})
.catch(error => console.error('Error:', error));
```

#### Ví Dụ 2: Tìm kiếm cho gia đình (2 người lớn + 2 trẻ em)

```javascript
const searchData = {
  check_in_date: "2024-04-20",
  check_out_date: "2024-04-23",
  adults: 2,
  children: 2,
  limit: 3
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
  console.log(data.message);
  console.log('Tiêu chí tìm kiếm:', data.search_criteria);
  console.log('Kết quả:', data.results.rooms);
})
.catch(error => console.error('Error:', error));
```

#### Ví Dụ 3: Hiển thị kết quả trên giao diện

```javascript
async function searchRooms() {
  const checkIn = document.getElementById('check_in').value;
  const checkOut = document.getElementById('check_out').value;
  const adults = parseInt(document.getElementById('adults').value);
  const children = parseInt(document.getElementById('children').value) || 0;

  const response = await fetch('http://localhost:8000/rooms/api/rooms/search/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      check_in_date: checkIn,
      check_out_date: checkOut,
      adults: adults,
      children: children,
      limit: 5
    })
  });

  const data = await response.json();

  if (data.success) {
    const roomsContainer = document.getElementById('rooms-list');
    roomsContainer.innerHTML = '';

    data.results.rooms.forEach(room => {
      const roomElement = document.createElement('div');
      roomElement.className = 'room-card';
      roomElement.innerHTML = `
        <img src="${room.image}" alt="${room.name}">
        <h3>${room.name}</h3>
        <p>Sức chứa: ${room.total_capacity} người (${room.capacity_adults} người lớn, ${room.capacity_children} trẻ em)</p>
        <p class="price">Tổng: ${room.total} VND (${data.search_criteria.num_nights} đêm)</p>
        <button onclick="bookRoom(${room.id})">Đặt Phòng</button>
      `;
      roomsContainer.appendChild(roomElement);
    });
  } else {
    document.getElementById('rooms-list').innerHTML = `<p class="error">${data.message}</p>`;
  }
}
```

### Python (Requests Library)

#### Ví Dụ 1: Tìm kiếm cho 5 người (2 người lớn + 3 trẻ em)

```python
import requests

search_data = {
    "check_in_date": "2024-04-10",
    "check_out_date": "2024-04-12",
    "adults": 2,
    "children": 3,
    "limit": 2
}

response = requests.post(
    'http://localhost:8000/rooms/api/rooms/search/',
    json=search_data
)

data = response.json()

if data['success']:
    print(data['message'])
    print(f"\nTiêu chí tìm kiếm:")
    print(f"  - Ngày: {data['search_criteria']['check_in_date']} -> {data['search_criteria']['check_out_date']}")
    print(f"  - Số khách: {data['search_criteria']['adults']} người lớn + {data['search_criteria']['children']} trẻ em = {data['search_criteria']['total_guests']} người")
    print(f"  - Số đêm: {data['search_criteria']['num_nights']}")
    
    print(f"\nPhòng Đề Xuất ({data['results']['count']} phòng):")
    for room in data['results']['rooms']:
        print(f"\n[{room['id']}] {room['name']}")
        print(f"    Sức chứa: {room['total_capacity']} người ({room['capacity_adults']} người lớn, {room['capacity_children']} trẻ em)")
        print(f"    Giá/đêm: {room['price']} VND")
        print(f"    Tổng ({room['num_nights']} đêm): {room['total']} VND")
else:
    print(f"Lỗi: {data['errors']}")
```

#### Ví Dụ 2: Tìm kiếm phòng hệ thống

```python
import requests
from datetime import datetime, timedelta

# Khoảng ngày
today = datetime.now().date()
tomorrow = today + timedelta(days=1)
checkout = today + timedelta(days=3)

# Các tiêu chí tìm kiếm
search_scenarios = [
    {"adults": 1, "children": 0},  # 1 người
    {"adults": 2, "children": 0},  # 2 người
    {"adults": 2, "children": 1},  # 3 người (gia đình)
    {"adults": 2, "children": 2},  # 4 người (gia đình lớn)
]

for scenario in search_scenarios:
    response = requests.post(
        'http://localhost:8000/rooms/api/rooms/search/',
        json={
            "check_in_date": today.isoformat(),
            "check_out_date": checkout.isoformat(),
            "adults": scenario['adults'],
            "children": scenario['children'],
            "limit": 3
        }
    )
    
    data = response.json()
    total = scenario['adults'] + scenario['children']
    print(f"\n{'='*50}")
    print(f"Tìm kiếm cho {total} khách ({scenario['adults']} người lớn + {scenario['children']} trẻ em)")
    print(f"{'='*50}")
    
    if data['success']:
        print(f"✓ {data['message']}")
        for room in data['results']['rooms']:
            print(f"  • {room['name']}: {room['total']} VND")
    else:
        print(f"✗ Lỗi: {data['errors']}")
```

### cURL

```bash
# Tìm kiếm cho 5 người (2 người lớn + 3 trẻ em)
curl -X POST http://localhost:8000/rooms/api/rooms/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "check_in_date": "2024-04-10",
    "check_out_date": "2024-04-12",
    "adults": 2,
    "children": 3,
    "limit": 2
  }'
```

---

## Lưu Ý Quan Trọng

1. **Định Dạng Ngày:** Tất cả ngày phải ở định dạng `YYYY-MM-DD`
2. **Phòng Trống:** Chỉ tìm kiếm phòng chưa được đặt trong khoảng thời gian
3. **Sắp Xếp:** Kết quả được sắp xếp theo độ phù hợp (phòng nhỏ nhất vừa đủ + giá rẻ)
4. **Giới Hạn:** Mặc định đề xuất 5 phòng, tối đa 10 phòng
5. **Tính Giá:** Giá hiển thị là giá chiết khấu (có GST 18%)

---

## Comparision: API vs Web View

| Tính Năng | API | Web View |
|----------|-----|---------|
| Dễ tích hợp | ✅ Dễ | ⚠️ Cần template |
| Xây dựng giao diện tùy chỉnh | ✅ Có | ❌ Không |
| Tự động hoá | ✅ Có | ❌ Không |
| Realtime updates | ✅ Có thể | ❌ Khó |
| Sử dụng trên mobile | ✅ Tốt | ⚠️ Tùy template |

---

## Troubleshooting

### Lỗi: "Ngày nhận phòng không được nhỏ hơn hôm nay"
**Nguyên nhân:** Cố gắng tìm kiếm ngày trong quá khứ
**Giải Pháp:** Sử dụng ngày hiện tại hoặc tương lai

### Lỗi: "Ngày trả phòng phải sau ngày nhận phòng"
**Nguyên nhân:** Ngày trả phòng trước ngày nhận phòng
**Giải Pháp:** Đảm bảo `check_out_date` > `check_in_date`

### Lỗi: "Không tìm thấy phòng"
**Nguyên nhân:** Có thể tất cả phòng đã được đặt hoặc không đủ sức chứa
**Giải Pháp:** 
- Thử ngày khác
- Thử số lượng khách khác
- Thử không filter children

### Lỗi 404 Not Found
**Nguyên nhân:** Endpoint không tồn tại
**Giải Pháp:** Kiểm tra URL đúng: `/rooms/api/rooms/search/`
