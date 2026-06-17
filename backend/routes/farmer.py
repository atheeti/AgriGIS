import json
import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator, ConfigDict
from sqlalchemy.orm import Session
from database import get_db
from models import Farmer

router = APIRouter()


class FarmerCreate(BaseModel):
    name: str
    phone: str
    plot_number: str
    crop_type: str
    geometry: Optional[dict] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^\d{10}$", v):
            raise ValueError("Phone number must be exactly 10 digits")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v

    @field_validator("plot_number")
    @classmethod
    def validate_plot(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Plot number cannot be empty")
        return v


class FarmerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    plot_number: str
    crop_type: str
    geometry: Optional[dict] = None
    created_at: datetime

    @classmethod
    def from_orm_farmer(cls, farmer: Farmer) -> "FarmerResponse":
        return cls(
            id=farmer.id,
            name=farmer.name,
            phone=farmer.phone,
            plot_number=farmer.plot_number,
            crop_type=farmer.crop_type,
            geometry=farmer.get_geometry(),
            created_at=farmer.created_at,
        )


class GeometryUpdate(BaseModel):
    geometry: dict


@router.post("/", response_model=FarmerResponse, status_code=status.HTTP_201_CREATED)
def register_farmer(farmer_data: FarmerCreate, db: Session = Depends(get_db)):
    existing = db.query(Farmer).filter(Farmer.plot_number == farmer_data.plot_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plot number '{farmer_data.plot_number}' is already registered",
        )

    farmer = Farmer(
        name=farmer_data.name,
        phone=farmer_data.phone,
        plot_number=farmer_data.plot_number,
        crop_type=farmer_data.crop_type,
    )
    farmer.set_geometry(farmer_data.geometry)
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return FarmerResponse.from_orm_farmer(farmer)


@router.get("/", response_model=list[FarmerResponse])
def list_farmers(db: Session = Depends(get_db)):
    farmers = db.query(Farmer).order_by(Farmer.created_at.desc()).all()
    return [FarmerResponse.from_orm_farmer(f) for f in farmers]


@router.get("/{farmer_id}", response_model=FarmerResponse)
def get_farmer(farmer_id: int, db: Session = Depends(get_db)):
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return FarmerResponse.from_orm_farmer(farmer)


@router.put("/{farmer_id}/geometry", response_model=FarmerResponse)
def update_geometry(farmer_id: int, body: GeometryUpdate, db: Session = Depends(get_db)):
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    farmer.set_geometry(body.geometry)
    db.commit()
    db.refresh(farmer)
    return FarmerResponse.from_orm_farmer(farmer)
