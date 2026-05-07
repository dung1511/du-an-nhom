# Feedback System After Checkout

## Overview
This document describes the new feedback system that allows customers to submit feedback and ratings after checking out of their rooms.

## Features

### 1. **Web Interface**
After a customer completes checkout, they are automatically redirected to a feedback form where they can:
- Enter their name and email (pre-filled if logged in)
- Enter their country
- Rate the room on a 1-5 star scale
- Write detailed feedback/comments

### 2. **Feedback Data Model**
The `Feedback` model now includes:
- **User**: Link to the authenticated user (if applicable)
- **Room**: The room that was rented
- **Reservation**: Link to the specific booking (for tracking which reservation the feedback relates to)
- **Name & Email**: Customer information
- **Country**: Customer's country
- **Rating**: 1-5 star rating
- **Comment**: Detailed feedback text
- **Created At**: Timestamp of submission

### 3. **Routes & Endpoints**

#### Web Routes:
```
/feedback/checkout/<reservation_id>/       - Feedback form after checkout
/feedback/thanks/<reservation_id>/         - Thank you page after submission
/feedback/submit/<room_id>/                - General feedback submission (legacy)
/feedback/list/                            - List all feedback
```

#### API Endpoints:
```
/feedback/api/list/                        - List all feedback (GET)
/feedback/api/<id>/                        - Get feedback detail (GET)
/feedback/api/submit/                      - Submit feedback (POST)
/feedback/api/room/<room_id>/              - Get feedback for a room (GET)
/feedback/api/reservation/<reservation_id>/ - Get feedback for a reservation (GET)
```

### 4. **API Usage Examples**

#### Submit Feedback via API
```bash
POST /feedback/api/submit/
Content-Type: application/json

{
    "booking_code": "BK000123",
    "name": "John Doe",
    "email": "john@example.com",
    "country": "Vietnam",
    "rating": 5,
    "comment": "Great experience! Will definitely come back."
}
```

#### Get Feedback by Room
```bash
GET /feedback/api/room/1/

Response:
{
    "room": "Deluxe Room",
    "room_id": 1,
    "total_feedbacks": 12,
    "average_rating": 4.5,
    "feedbacks": [...]
}
```

#### Get Feedback by Reservation
```bash
GET /feedback/api/reservation/123/

Response:
{
    "status": "success",
    "data": {
        "id": 5,
        "user_name": "John Doe",
        "email": "john@example.com",
        "room": 1,
        "room_name": "Deluxe Room",
        "booking_code": "BK000123",
        "rating": 5,
        "comment": "...",
        "created_at": "2026-05-02T10:30:00Z"
    }
}
```

### 5. **Workflow**

1. **Customer checks out** → System redirects to feedback page
2. **Customer fills feedback form** → Includes room info, booking code
3. **Customer submits** → Feedback is saved with reservation link
4. **Thank you page** → Customer sees confirmation and can explore more rooms
5. **Admin sees feedback** → In Django admin with booking code visible

### 6. **Admin Interface**
In Django admin (`/admin/feedback/feedback/`):
- View all feedback with booking codes
- Filter by rating, date, or room
- Search by customer name or email
- See full customer details and comments

### 7. **Templates**

#### feedback_form.html
- Shows reservation details (room name, booking code, dates)
- Beautiful star rating selector
- Form fields for name, email, country, and comment
- Mobile responsive design

#### feedback_thanks.html
- Confirmation message
- Shows reservation details
- Links to browse other rooms or see all feedback
- Animated success indicator

## Database Migration
Run the following to apply database changes:
```bash
python manage.py migrate feedback
```

## Notes
- Feedback is linked to specific reservations using OneToOne relationship
- Booking code is extracted from reservation for easy lookup
- Both authenticated and anonymous customers can submit feedback
- Feedback is optional but strongly encouraged
- The system maintains historical feedback data for analytics

## Future Enhancements
- Email notification to admin when feedback is submitted
- Sentiment analysis of feedback text
- Feedback dashboard with statistics
- Response system for admin to reply to feedback
- Photo uploads with feedback
- Feedback verification badge for verified stays
