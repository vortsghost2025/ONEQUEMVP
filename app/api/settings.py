from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Optional
from pydantic import BaseModel, Field, validator

from app.models import Settings
from app.utils import get_session, logger

router = APIRouter()


# Pydantic model for PATCH body
class SettingsPatch(BaseModel):
    max_ram_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    max_cpu_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    max_disk_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    auto_pause: Optional[bool] = None
    default_model: Optional[str] = Field(default=None, max_length=100, min_length=1)
    default_timeout_seconds: Optional[int] = Field(default=None, ge=10, le=3600)
    queue_paused: Optional[bool] = None

    @validator("default_model")
    def validate_model(cls, v):
        if v is not None and not v.strip():
            raise ValueError("default_model cannot be empty or whitespace only")
        return v.strip() if v else v


# Helper to retrieve the singleton Settings row (creates if missing)
def get_settings_row(session: Session) -> Settings:
    s = session.get(Settings, 1)
    if not s:
        s = Settings()
        session.add(s)
        session.commit()
        session.refresh(s)
    return s


# GET singleton settings
@router.get("", response_model=Settings)
def read_settings(session: Session = Depends(get_session)):
    logger.debug("Reading settings")
    return get_settings_row(session)


# PATCH singleton settings
@router.patch("", response_model=Settings)
def update_settings(patch: SettingsPatch, session: Session = Depends(get_session)):
    logger.info("Updating settings")
    s = get_settings_row(session)
    update_data = patch.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(s, key, value)
    session.add(s)
    session.commit()
    session.refresh(s)
    logger.info(f"Settings updated: {list(update_data.keys())}")
    return s
