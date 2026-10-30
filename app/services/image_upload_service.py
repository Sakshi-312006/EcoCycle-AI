"""Pillar 1: Secure Image Upload Service.

Handles multipart image uploads from Flutter camera/gallery with:
- Strict MIME type verification
- Magic byte (file signature) validation
- File size bounds checking (reject empty and oversized files)
- Cryptographic UUID server-side filename generation (no client filename trust)
- Path traversal mitigation and local disk containment
- Stable URL generation for Flutter development and production
"""

import os
from pathlib import Path
from typing import Tuple
import uuid
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.schemas.waste_workflow import ImageUploadResponse

# File magic bytes signatures for robust binary inspection
MAGIC_SIGNATURES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],  # With 'WEBP' at offset 8-12
}

MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class ImageUploadService:
    """Service providing secure storage and validation for waste identification photos."""

    @staticmethod
    def _validate_image_bytes(header: bytes, content_type: str) -> None:
        """Verify binary file signature matches expected image format."""
        if content_type == "image/jpeg":
            if not header.startswith(b"\xff\xd8\xff"):
                raise ValidationException("Invalid image content. File header does not match JPEG signature.")
        elif content_type == "image/png":
            if not header.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValidationException("Invalid image content. File header does not match PNG signature.")
        elif content_type == "image/webp":
            if not (header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP"):
                raise ValidationException("Invalid image content. File header does not match WebP signature.")
        else:
            raise ValidationException(f"Unsupported image MIME type: '{content_type}'.")

    @classmethod
    async def save_upload(cls, file: UploadFile) -> ImageUploadResponse:
        """Validate and securely persist uploaded waste photograph."""
        # 1. Content-Type Header Verification
        content_type = (file.content_type or "").lower().strip()
        if content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise ValidationException(
                f"Unsupported file type '{content_type or 'unknown'}'. "
                f"Allowed formats: {', '.join(settings.ALLOWED_IMAGE_TYPES)}."
            )

        # 2. Read contents and check size bounds
        content = await file.read()
        size_bytes = len(content)

        # Reject empty file
        if size_bytes == 0:
            raise ValidationException("Uploaded image file is empty (0 bytes). Please capture or select a valid image.")

        # Reject oversized file
        if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
            raise ValidationException(
                f"File size ({size_bytes / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of {max_mb:.1f} MB."
            )

        # 3. Magic Bytes Binary Inspection
        cls._validate_image_bytes(content[:32], content_type)

        # 4. Generate Safe Server-Side Filename (Ignore original user filename to prevent traversal)
        file_id = uuid.uuid4()
        ext = MIME_TO_EXT.get(content_type, ".jpg")
        safe_filename = f"{file_id.hex}{ext}"

        # 5. Resolve and Contain Destination Path
        storage_dir = Path(settings.STORAGE_LOCAL_PATH).resolve()
        storage_dir.mkdir(parents=True, exist_ok=True)

        destination_path = (storage_dir / safe_filename).resolve()

        # Path traversal guard: verify destination is strictly a child of storage_dir
        try:
            destination_path.relative_to(storage_dir)
        except ValueError:
            raise ValidationException("Unsafe file path detected. Storage destination cannot escape upload directory.")

        # 6. Write file to disk
        with open(destination_path, "wb") as f:
            f.write(content)

        # 7. Formulate stable static URL
        file_url = f"/static/uploads/{safe_filename}"

        return ImageUploadResponse(
            file_id=file_id,
            filename=safe_filename,
            file_url=file_url,
            content_type=content_type,
            size_bytes=size_bytes,
        )

