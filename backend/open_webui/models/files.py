import logging
import time
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, JSON, and_

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class File(Base):
    __tablename__ = "file"
    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String)
    hash = Column(Text, nullable=True)

    filename = Column(Text)
    path = Column(Text, nullable=True)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class FileModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    hash: Optional[str] = None

    filename: str
    path: Optional[str] = None

    data: Optional[dict] = None
    meta: Optional[dict] = None

    access_control: Optional[dict] = None

    created_at: Optional[int]
    updated_at: Optional[int]


class FileMeta(BaseModel):
    name: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class FileModelResponse(BaseModel):
    id: str
    user_id: str
    hash: Optional[str] = None

    filename: str
    data: Optional[dict] = None
    meta: FileMeta

    created_at: int
    updated_at: int

    model_config = ConfigDict(extra="allow")


class FileMetadataResponse(BaseModel):
    id: str
    hash: Optional[str] = None
    meta: dict
    created_at: int
    updated_at: int


class FileForm(BaseModel):
    id: str
    hash: Optional[str] = None
    filename: str
    path: str
    data: dict = Field(default_factory=dict)
    meta: dict = Field(default_factory=dict)
    access_control: Optional[dict] = None


class FileUpdateForm(BaseModel):
    hash: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None


class FilesTable:
    def insert_new_file(self, user_id: str, form_data: FileForm) -> Optional[FileModel]:
        with get_db() as db:
            file = FileModel(
                **{
                    **form_data.model_dump(),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            try:
                result = File(**file.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return FileModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error inserting a new file: {e}")
                return None

    def get_file_by_id(self, id: str) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.get(File, id)
                return FileModel.model_validate(file) if file else None
            except Exception as e:
                log.exception(f"Error getting file by id: {e}")
                return None

    def get_file_by_id_and_user_id(self, id: str, user_id: str) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.query(File).filter_by(id=id, user_id=user_id).first()
                return FileModel.model_validate(file) if file else None
            except Exception as e:
                log.exception(f"Error getting file by id and user_id: {e}")
                return None

    def get_file_metadata_by_id(self, id: str) -> Optional[FileMetadataResponse]:
        with get_db() as db:
            try:
                file = db.get(File, id)
                if not file:
                    return None
                return FileMetadataResponse(
                    id=file.id,
                    hash=file.hash,
                    meta=file.meta,
                    created_at=file.created_at,
                    updated_at=file.updated_at,
                )
            except Exception as e:
                log.exception(f"Error getting file metadata by id: {e}")
                return None

    def get_files(self) -> list[FileModel]:
        with get_db() as db:
            return [FileModel.model_validate(file) for file in db.query(File).all()]

    def get_files_by_ids(self, ids: list[str]) -> list[FileModel]:
        with get_db() as db:
            return [
                FileModel.model_validate(file)
                for file in db.query(File).filter(File.id.in_(ids)).order_by(File.updated_at.desc()).all()
            ]

    def get_files_by_user_id(self, user_id: str) -> list[FileModel]:
        with get_db() as db:
            return [FileModel.model_validate(file) for file in db.query(File).filter_by(user_id=user_id).all()]

    def count_recent_upload_files_by_user_id(self, user_id: str, time_window_seconds: int = 5) -> int:
        current_time = int(time.time())
        time_threshold = current_time - time_window_seconds
        with get_db() as db:
            return (
                db.query(File)
                .filter(and_(File.user_id == user_id, File.created_at >= time_threshold))
                .count()
            )

    def update_file_by_id(self, id: str, form_data: FileUpdateForm) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.query(File).filter_by(id=id).first()
                if not file:
                    return None

                if form_data.hash is not None:
                    file.hash = form_data.hash

                if form_data.data is not None:
                    file.data = {**(file.data or {}), **form_data.data}

                if form_data.meta is not None:
                    file.meta = {**(file.meta or {}), **form_data.meta}

                file.updated_at = int(time.time())
                db.commit()
                db.refresh(file)
                return FileModel.model_validate(file)
            except Exception as e:
                log.exception(f"Error updating file by id: {e}")
                return None

    def update_file_hash_by_id(self, id: str, hash: str) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.query(File).filter_by(id=id).first()
                if not file:
                    return None
                file.hash = hash
                file.updated_at = int(time.time())
                db.commit()
                db.refresh(file)
                return FileModel.model_validate(file)
            except Exception as e:
                log.exception(f"Error updating file hash by id: {e}")
                return None

    def update_file_data_by_id(self, id: str, data: dict) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.query(File).filter_by(id=id).first()
                if not file:
                    return None
                file.data = {**(file.data or {}), **data}
                file.updated_at = int(time.time())
                db.commit()
                db.refresh(file)
                return FileModel.model_validate(file)
            except Exception as e:
                log.exception(f"Error updating file data by id: {e}")
                return None

    def update_file_metadata_by_id(self, id: str, meta: dict) -> Optional[FileModel]:
        with get_db() as db:
            try:
                file = db.query(File).filter_by(id=id).first()
                if not file:
                    return None
                file.meta = {**(file.meta or {}), **meta}
                file.updated_at = int(time.time())
                db.commit()
                db.refresh(file)
                return FileModel.model_validate(file)
            except Exception as e:
                log.exception(f"Error updating file metadata by id: {e}")
                return None

    def delete_file_by_id(self, id: str) -> bool:
        with get_db() as db:
            try:
                deleted = db.query(File).filter_by(id=id).delete()
                db.commit()
                return bool(deleted)
            except Exception as e:
                log.exception(f"Error deleting file by id: {e}")
                return False

    def delete_all_files(self) -> bool:
        with get_db() as db:
            try:
                db.query(File).delete()
                db.commit()
                return True
            except Exception as e:
                log.exception(f"Error deleting all files: {e}")
                return False


Files = FilesTable()
