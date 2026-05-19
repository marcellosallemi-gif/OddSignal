from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EventResponse(BaseModel):
    id: int
    competition: str
    home_team: str
    away_team: str
    match: str
    start_time: datetime
    status: str


class OddsResponse(BaseModel):
    id: int
    event: str
    competition: str
    provider: str
    provider_event_id: Optional[str] = None
    bookmaker: str
    market: str
    selection: str
    line: Optional[float] = None
    odds_decimal: float
    provider_updated_at: Optional[datetime] = None
    captured_at: datetime


class AlertResponse(BaseModel):
    id: int
    event: str
    competition: str
    provider: str
    bookmaker: str
    market: str
    selection: str
    previous_odds: float
    current_odds: float
    variation_percent: float
    direction: str
    alert_type: str
    created_at: datetime


class MonitoredCompetitionCreate(BaseModel):
    competition_name: str
    country: Optional[str] = None
    provider: str = "odds_api_io"
    provider_league_slug: Optional[str] = None
    is_active: bool = True


class MonitoredCompetitionResponse(BaseModel):
    id: int
    competition_name: str
    country: Optional[str] = None
    provider: str
    provider_league_slug: Optional[str] = None
    is_active: bool
    created_at: datetime


class MonitoredMarketCreate(BaseModel):
    market_name: str
    is_active: bool = True


class MonitoredMarketResponse(BaseModel):
    id: int
    market_name: str
    is_active: bool
    created_at: datetime


class NotificationRecipientCreate(BaseModel):
    channel: str
    recipient_value: str
    label: Optional[str] = None
    is_active: bool = True


class NotificationRecipientResponse(BaseModel):
    id: int
    channel: str
    recipient_value: str
    label: Optional[str] = None
    is_active: bool
    created_at: datetime


class AlertSettingUpdate(BaseModel):
    min_percent: float
    max_percent: float
    critical_percent: float
    deduplication_minutes: int


class AlertSettingResponse(BaseModel):
    id: int
    min_percent: float
    max_percent: float
    critical_percent: float
    deduplication_minutes: int
    created_at: datetime

class SchedulerSettingUpdate(BaseModel):
    enabled: bool
    poll_interval_seconds: int
    event_limit: int


class SchedulerSettingResponse(BaseModel):
    id: int
    enabled: bool
    poll_interval_seconds: int
    event_limit: int
    created_at: datetime

