from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Competition(Base):
    __tablename__ = "competitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    country = Column(String, nullable=False)
    provider_league_slug = Column(String, nullable=True)

    events = relationship("Event", back_populates="competition")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)

    home_events = relationship(
        "Event",
        foreign_keys="Event.home_team_id",
        back_populates="home_team",
    )
    away_events = relationship(
        "Event",
        foreign_keys="Event.away_team_id",
        back_populates="away_team",
    )


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)

    competition = relationship("Competition", back_populates="events")
    home_team = relationship(
        "Team",
        foreign_keys=[home_team_id],
        back_populates="home_events",
    )
    away_team = relationship(
        "Team",
        foreign_keys=[away_team_id],
        back_populates="away_events",
    )
    odds_snapshots = relationship("OddsSnapshot", back_populates="event")
    alerts = relationship("Alert", back_populates="event")
    notification_logs = relationship("NotificationLog", back_populates="event")


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    provider = Column(String, nullable=False)
    provider_event_id = Column(String, nullable=True)
    bookmaker = Column(String, nullable=False)
    market = Column(String, nullable=False)
    selection = Column(String, nullable=False)
    line = Column(Float, nullable=True)
    odds_decimal = Column(Float, nullable=False)
    provider_updated_at = Column(DateTime, nullable=True)
    captured_at = Column(DateTime, nullable=False)
    raw_payload = Column(Text, nullable=True)

    event = relationship("Event", back_populates="odds_snapshots")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    provider = Column(String, nullable=False)
    bookmaker = Column(String, nullable=False)
    market = Column(String, nullable=False)
    selection = Column(String, nullable=False)
    previous_odds = Column(Float, nullable=False)
    current_odds = Column(Float, nullable=False)
    variation_percent = Column(Float, nullable=False)
    direction = Column(String, nullable=False)
    alert_type = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)

    event = relationship("Event", back_populates="alerts")
    notification_logs = relationship("NotificationLog", back_populates="alert")


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    channel = Column(String, nullable=False)
    status = Column(String, nullable=False)
    recipient = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=False)

    alert = relationship("Alert", back_populates="notification_logs")
    event = relationship("Event", back_populates="notification_logs")


class MonitoredCompetition(Base):
    __tablename__ = "monitored_competitions"

    id = Column(Integer, primary_key=True, index=True)
    competition_name = Column(String, nullable=False, unique=True)
    country = Column(String, nullable=True)
    provider = Column(String, nullable=False, default="odds_api_io")
    provider_league_slug = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False)


class MonitoredMarket(Base):
    __tablename__ = "monitored_markets"

    id = Column(Integer, primary_key=True, index=True)
    market_name = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False)


class NotificationRecipient(Base):
    __tablename__ = "notification_recipients"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String, nullable=False)
    recipient_value = Column(String, nullable=False)
    label = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False)


class AlertSetting(Base):
    __tablename__ = "alert_settings"

    id = Column(Integer, primary_key=True, index=True)
    min_percent = Column(Float, nullable=False, default=8.0)
    max_percent = Column(Float, nullable=False, default=15.0)
    critical_percent = Column(Float, nullable=False, default=15.0)
    deduplication_minutes = Column(Integer, nullable=False, default=30)
    created_at = Column(DateTime, nullable=False)

class SchedulerSetting(Base):
    __tablename__ = "scheduler_settings"

    id = Column(Integer, primary_key=True, index=True)
    enabled = Column(Boolean, nullable=False, default=False)
    poll_interval_seconds = Column(Integer, nullable=False, default=300)
    event_limit = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False)


class ProviderPlanSetting(Base):
    __tablename__ = "provider_plan_settings"

    id = Column(Integer, primary_key=True, index=True)
    plan_name = Column(String, nullable=False, default="Free")
    hourly_request_limit = Column(Integer, nullable=True, default=100)
    max_bookmakers = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime, nullable=False)


class ProviderBookmakerSetting(Base):
    __tablename__ = "provider_bookmaker_settings"

    id = Column(Integer, primary_key=True, index=True)
    bookmakers_csv = Column(String, nullable=False, default="Stake,Sbobet")
    created_at = Column(DateTime, nullable=False)



class ProviderApiRequestLog(Base):
    __tablename__ = "provider_api_request_logs"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, default="odds_api_io")
    endpoint = Column(String, nullable=False)
    status_code = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False)



class ProviderApiRateLimitState(Base):
    __tablename__ = "provider_api_rate_limit_state"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, default="odds_api_io")
    blocked_until = Column(DateTime, nullable=False)
    reason = Column(String, nullable=False, default="provider_rate_limit")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
