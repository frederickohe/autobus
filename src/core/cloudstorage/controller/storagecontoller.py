from fastapi import APIRouter, Depends, HTTPException, UploadFile, status, Query, File
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from core.auth.service.sessiondriver import SessionDriver, TokenData
from another_fastapi_jwt_auth import AuthJWT
from core.cloudstorage.dto.filedto import FileDTO
from core.exceptions import *
from core.notification.dto.request.notificationcreate import NotificationCreateRequest
from core.notification.dto.request.notificationupdate import NotificationUpdateRequest
from utilities.dbconfig import SessionLocal
from sqlalchemy.orm import Session
import logging
from core.notification.model.Notification import Notification, NotificationStatus, NotificationType
from core.user.model.User import User

# DTO Models
from core.notification.dto.response.notification_response import NotificationResponse
from core.notification.dto.response.paged_notifications import PagedNotificationResponse
from core.notification.dto.response.message_response import MessageResponse

from core.notification.service.notification_service import NotificationService
from another_fastapi_jwt_auth.exceptions import MissingTokenError
from core.cloudstorage.service.storageservice import StorageService
from core.cloudstorage.service.storageservice import StorageFolder
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Reuse your existing token validation and DB dependencies
from core.user.controller.usercontroller import validate_token, get_db

from fastapi.responses import FileResponse
import os


storage_routes = APIRouter()

storage_service = StorageService()

def _safe_user_prefix(subject: str) -> str:
    # S3 keys can include many characters, but we keep it conservative and stable.
    safe = (subject or "unknown").strip()
    safe = safe.replace("\\", "_").replace("/", "_")
    return f"{safe}/"

@storage_routes.post("/upload", response_model=FileDTO)
async def upload_file(
    file: UploadFile,
    folder: Optional[StorageFolder] = Query(None),
    authjwt: AuthJWT = Depends(validate_token),
):
    safe_name = os.path.basename(file.filename)
    url = storage_service.upload_file(
        file.file,
        safe_name,
        content_type=file.content_type,
        folder=folder,
    )
    return FileDTO(file_name=safe_name, file_url=url, folder=folder.value if folder else None)


@storage_routes.post("/me/upload-multiple", response_model=List[FileDTO])
async def upload_multiple_files_for_me(
    files: List[UploadFile] = File(...),
    folder: StorageFolder = Query(...),
    authjwt: AuthJWT = Depends(validate_token),
):
    subject = authjwt.get_jwt_subject()
    user_prefix = _safe_user_prefix(subject)

    uploaded: List[FileDTO] = []
    for f in files:
        safe_name = os.path.basename(f.filename)
        key_name = f"{user_prefix}{safe_name}"
        url = storage_service.upload_file(
            f.file,
            key_name,
            content_type=f.content_type,
            folder=folder,
        )
        object_key = f"{storage_service.resolve_subfolder(folder=folder)}{key_name}"
        uploaded.append(
            FileDTO(
                file_name=safe_name,
                file_url=url,
                folder=folder.value,
                object_key=object_key,
            )
        )

    return uploaded


@storage_routes.get("/me/files", response_model=List[FileDTO])
async def list_my_files_in_folder(
    folder: StorageFolder = Query(...),
    authjwt: AuthJWT = Depends(validate_token),
):
    subject = authjwt.get_jwt_subject()
    user_prefix = _safe_user_prefix(subject)

    objects = storage_service.list_files(folder=folder, prefix=user_prefix)
    return [
        FileDTO(
            file_name=os.path.basename(o["key"]),
            file_url=o["url"],
            folder=folder.value,
            object_key=o["key"],
        )
        for o in objects
    ]


@storage_routes.get("/me/download/{file_name}")
async def download_my_file(
    file_name: str,
    folder: StorageFolder = Query(...),
    authjwt: AuthJWT = Depends(validate_token),
):
    subject = authjwt.get_jwt_subject()
    user_prefix = _safe_user_prefix(subject)

    safe_name = os.path.basename(file_name)
    key_name = f"{user_prefix}{safe_name}"

    os.makedirs("./downloads", exist_ok=True)
    destination_path = f"./downloads/{safe_name}"
    try:
        storage_service.download_file(key_name, destination_path, folder=folder)
    except Exception:
        raise HTTPException(status_code=404, detail=f"File not found: {safe_name}")

    return FileResponse(destination_path, filename=safe_name)

@storage_routes.get("/download/{file_name}")
async def download_file(
    file_name: str,
    folder: Optional[StorageFolder] = Query(None),
    authjwt: AuthJWT = Depends(validate_token),
):
    # Sanitize file name
    safe_name = os.path.basename(file_name)

    # Ensure downloads directory exists
    os.makedirs("./downloads", exist_ok=True)

    destination_path = f"./downloads/{safe_name}"
    try:
        storage_service.download_file(safe_name, destination_path, folder=folder)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {safe_name}")
    

    # Return file to client
    return FileResponse(destination_path, filename=safe_name)

