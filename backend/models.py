import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(10), nullable=False)
    plot_number = Column(String(50), unique=True, nullable=False)
    crop_type = Column(String(100), nullable=False)
    geometry = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    index_requests = relationship("IndexRequest", back_populates="farmer")

    def set_geometry(self, geo: dict | None):
        self.geometry = json.dumps(geo) if geo else None

    def get_geometry(self) -> dict | None:
        return json.loads(self.geometry) if self.geometry else None


class IndexRequest(Base):
    __tablename__ = "index_requests"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=True)
    index_name = Column(String(20), nullable=False)
    date_from = Column(String(20), nullable=False)
    date_to = Column(String(20), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="index_requests")
