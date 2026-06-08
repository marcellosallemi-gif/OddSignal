from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EventResponse(BaseModel):
    id: int
    sport: str
    competition: str
    home_team: str
    away_team: str
    match: str
    start_time: datetime
    status: str


class OddsResponse(BaseModel):
    id: int
    sport: str
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
    sport: str
    country: str
    category: str
    event: str
    competition: str
    event_start_time: Optional[str] = None
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


class CompetitionProviderMappingUpdate(BaseModel):
    competition_name: str
    provider_league_slug: str
    country: Optional[str] = None
    sport: str = "football"


class MonitoredCompetitionCreate(BaseModel):
    competition_name: str
    country: Optional[str] = None
    sport: str = "football"
    provider: str = "odds_api_io"
    provider_league_slug: Optional[str] = None
    is_active: bool = True


class MonitoredCompetitionResponse(BaseModel):
    id: int
    competition_name: str
    country: Optional[str] = None
    sport: str
    provider: str
    provider_league_slug: Optional[str] = None
    is_active: bool
    created_at: datetime


class MonitoredMarketCreate(BaseModel):
    sport: str = "football"
    market_name: str
    is_active: bool = True


class MonitoredMarketResponse(BaseModel):
    id: int
    sport: str = "football"
    market_name: str
    is_active: bool
    created_at: datetime


class NotificationRecipientCreate(BaseModel):
    channel: str
    recipient_value: str
    label: Optional[str] = None
    is_active: bool = True
    status: Optional[str] = None


class NotificationRecipientResponse(BaseModel):
    id: int
    channel: str
    recipient_value: str
    label: Optional[str] = None
    is_active: bool
    status: str
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



class ProviderPlanSettingUpdate(BaseModel):
    plan_name: str
    hourly_request_limit: Optional[int] = None
    max_bookmakers: int


class ProviderPlanUsageEstimate(BaseModel):
    active_mapped_competitions_count: int
    active_mapped_football_count: int = 0
    active_mapped_tennis_count: int = 0
    poll_interval_seconds: int
    event_limit: int
    cycles_per_hour: float
    estimated_requests_per_cycle: int
    estimated_requests_per_hour: float
    hourly_request_limit: Optional[int] = None
    exceeds_hourly_limit: bool
    recommendation: str


class ProviderPlanSettingResponse(BaseModel):
    id: int
    plan_name: str
    hourly_request_limit: Optional[int] = None
    max_bookmakers: int
    created_at: datetime
    usage_estimate: Optional[ProviderPlanUsageEstimate] = None



class ProviderBookmakerSettingUpdate(BaseModel):
    bookmakers_csv: str


class ProviderBookmakerSettingResponse(BaseModel):
    id: int
    bookmakers_csv: str
    bookmakers: list[str]
    bookmaker_count: int
    max_bookmakers: int
    exceeds_bookmaker_limit: bool
    created_at: datetime
