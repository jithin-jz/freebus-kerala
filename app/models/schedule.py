from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    departure_time = Column(Time, nullable=False)
    days_of_operation = Column(String(20), nullable=False, default="daily")
    frequency_note = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    route = relationship("Route", back_populates="schedules")


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
    status = Column(String(20), nullable=False, default="running")
    routes_added = Column(Integer, nullable=False, default=0)
    routes_updated = Column(Integer, nullable=False, default=0)
    routes_failed = Column(Integer, nullable=False, default=0)
    schedules_added = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)
    source_url = Column(Text)

