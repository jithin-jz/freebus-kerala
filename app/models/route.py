from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True)
    origin_stop_id = Column(Integer, ForeignKey("stops.id"), nullable=False)
    destination_stop_id = Column(Integer, ForeignKey("stops.id"), nullable=False)
    route_name = Column(String(250), nullable=False)
    route_name_ml = Column(String(250))
    via = Column(String(200))
    bus_type = Column(String(60), nullable=False)
    is_priyadarshini = Column(Boolean, nullable=False, default=False)
    depot_id = Column(Integer, ForeignKey("depots.id"))
    source_url = Column(Text)
    data_hash = Column(String(64))
    last_scraped_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    origin_stop = relationship(
        "Stop",
        foreign_keys=[origin_stop_id],
        back_populates="origin_routes",
    )
    destination_stop = relationship(
        "Stop",
        foreign_keys=[destination_stop_id],
        back_populates="destination_routes",
    )
    depot = relationship("Depot", back_populates="routes")
    schedules = relationship("Schedule", back_populates="route", cascade="all, delete-orphan")

