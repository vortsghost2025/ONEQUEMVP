from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Optional
from pydantic import BaseModel

from app.models import Settings
from app.main import get_session

router = APIRouter()


# Pydantic model for PATCH body
class SettingsPatch(BaseModel):
    max_ram_percent: Optional[float] = None
    max_cpu_percent: Optional[float] = None
    max_disk_percent: Optional[float] = None
    auto_pause: Optional[bool] = None
    default_model: Optional[str] = None
    default_timeout_seconds: Optional[int] = None
    queue_paused: Optional[bool] = None


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
    return get_settings_row(session)


# PATCH singleton settings
@router.patch("", response_model=Settings)
def update_settings(patch: SettingsPatch, session: Session = Depends(get_session)):
    s = get_settings_row(session)
    update_data = patch.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(s, key, value)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s
