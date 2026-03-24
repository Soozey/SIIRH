from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
import calendar as pycalendar
from typing import List
from pydantic import BaseModel

from .. import models
from ..config.config import get_db
from ..security import READ_PAYROLL_ROLES, WRITE_RH_ROLES, can_access_employer, require_roles

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"]
)

class CalendarDayOut(BaseModel):
    date: date
    is_worked: bool
    is_override: bool

class ToggleRequest(BaseModel):
    employer_id: int
    date: date
    is_worked: bool

@router.get("/{employer_id}/{year}/{month}", response_model=List[CalendarDayOut])
def get_month_calendar(
    employer_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    if not can_access_employer(db, user, employer_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    # 1. Fetch overrides from DB
    _, last_day = pycalendar.monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    db_days = db.query(models.CalendarDay).filter(
        models.CalendarDay.employer_id == employer_id,
        models.CalendarDay.date >= start,
        models.CalendarDay.date <= end
    ).all()
    
    db_map = {d.date: d.is_worked for d in db_days}
    
    # 2. Generate full month
    result = []
    
    for day in range(1, last_day + 1):
        curr = date(year, month, day)
        
        # Determine status
        if curr in db_map:
            is_worked = db_map[curr]
            is_override = True
        else:
            # Default: Mon-Fri worked (0-4), Sat-Sun off (5-6)
            is_worked = (curr.weekday() < 5)
            is_override = False
            
        result.append(CalendarDayOut(date=curr, is_worked=is_worked, is_override=is_override))
        
    return result

@router.post("/toggle")
def toggle_day(
    req: ToggleRequest,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    if not can_access_employer(db, user, req.employer_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    # Check if exists
    day_entry = db.query(models.CalendarDay).filter(
        models.CalendarDay.employer_id == req.employer_id,
        models.CalendarDay.date == req.date
    ).first()
    
    if day_entry:
        day_entry.is_worked = req.is_worked
    else:
        day_entry = models.CalendarDay(
            employer_id=req.employer_id,
            date=req.date,
            is_worked=req.is_worked
        )
        db.add(day_entry)
        
    db.commit()
    return {"message": "Updated"}
