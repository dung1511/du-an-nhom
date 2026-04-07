import uuid
from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

ALLOWED_MIME_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

ALLOWED_IMAGE_FORMATS = {
    "JPEG": "jpg",
    "PNG": "png",
    "WEBP": "webp",
}

MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # 2MB


def validate_image_file(uploaded_file, max_size=MAX_UPLOAD_SIZE):
    if not uploaded_file:
        raise ValidationError("Thiếu file upload.")

    if uploaded_file.size > max_size:
        raise ValidationError("Kích thước file vượt quá 2MB.")

    content_type = (uploaded_file.content_type or "").lower()
    if content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError("Định dạng file không hợp lệ. Chỉ hỗ trợ JPG, PNG, WEBP.")

    original_ext = Path(uploaded_file.name).suffix.lower().lstrip(".")
    if original_ext and original_ext not in {"jpg", "jpeg", "png", "webp"}:
        raise ValidationError("Phần mở rộng file không hợp lệ.")

    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image_format = image.format
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValidationError("File upload không phải ảnh hợp lệ.")
    finally:
        uploaded_file.seek(0)

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("Ảnh không đúng định dạng cho phép.")

    return ALLOWED_IMAGE_FORMATS[image_format]


def build_safe_filename(extension):
    normalized_ext = extension.lower().lstrip(".")
    return f"{uuid.uuid4().hex}.{normalized_ext}"
