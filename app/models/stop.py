from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import UserDefinedType

from app.database import Base


class Geometry(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **_kw: object) -> str:
        return "GEOMETRY(Point, 4326)"


class Depot(Base):
    __tablename__ = "depots"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    name_ml = Column(String(120))
    district = Column(String(60), nullable=False)
    address = Column(Text)
    phone = Column(String(20))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    stops = relationship("Stop", back_populates="depot")
    routes = relationship("Route", back_populates="depot")


class Stop(Base):
    __tablename__ = "stops"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    name_ml = Column(String(120))
    name_slug = Column(String(140), nullable=False, unique=True)
    district = Column(String(60), nullable=False)
    depot_id = Column(Integer, ForeignKey("depots.id"))
    location = Column(Geometry)
    osm_id = Column(BigInteger)
    is_major = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    depot = relationship("Depot", back_populates="stops")
    origin_routes = relationship(
        "Route",
        foreign_keys="Route.origin_stop_id",
        back_populates="origin_stop",
    )
    destination_routes = relationship(
        "Route",
        foreign_keys="Route.destination_stop_id",
        back_populates="destination_stop",
    )

