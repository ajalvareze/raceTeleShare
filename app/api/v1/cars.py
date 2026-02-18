from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.car import Car
from app.models.user import User
from app.schemas.car import CarCreate, CarOut, CarUpdate

router = APIRouter(prefix="/cars", tags=["cars"])


@router.get("/", response_model=list[CarOut])
def list_my_cars(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Car).filter(Car.owner_id == current_user.id).all()


@router.post("/", response_model=CarOut, status_code=201)
def create_car(
    payload: CarCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    car = Car(**payload.model_dump(), owner_id=current_user.id)
    db.add(car)
    db.commit()
    db.refresh(car)
    return car


@router.patch("/{car_id}", response_model=CarOut)
def update_car(
    car_id: int,
    payload: CarUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    car = db.get(Car, car_id)
    if not car or car.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Car not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(car, field, value)
    db.commit()
    db.refresh(car)
    return car


@router.delete("/{car_id}", status_code=204)
def delete_car(
    car_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    car = db.get(Car, car_id)
    if not car or car.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Car not found")
    db.delete(car)
    db.commit()
