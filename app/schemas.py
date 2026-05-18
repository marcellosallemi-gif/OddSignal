from datetime import datetime

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
    bookmaker: str
    market: str
    selection: str
    odds_decimal: float
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
