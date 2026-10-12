"""Thư mục lưu file upload (CV) và việc phục vụ file qua đường dẫn /uploads."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings

UPLOAD_ROOT: Path = settings.UPLOAD_DIR
CV_DIR: Path = UPLOAD_ROOT / "cvs"
UPLOAD_URL_PREFIX = "/uploads"


def ensure_upload_dirs() -> None:
    CV_DIR.mkdir(parents=True, exist_ok=True)


def mount_uploads(app: FastAPI) -> None:
    """Cho phép mở file đã upload qua http://<core>/uploads/cvs/<user_id>/<tên file>.pdf."""
    ensure_upload_dirs()
    app.mount(UPLOAD_URL_PREFIX, StaticFiles(directory=UPLOAD_ROOT), name="uploads")
