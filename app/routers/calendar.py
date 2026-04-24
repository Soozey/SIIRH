from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime, time, timedelta
import calendar as pycalendar
from typing import List, Literal, Optional
from pydantic import BaseModel

from .. import models
from ..config.config import get_db
from ..security import READ_PAYROLL_ROLES, WRITE_RH_ROLES, can_access_employer, can_access_worker, require_roles

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"]
)

class CalendarDayOut(BaseModel):
    date: date
    is_worked: bool
    status: Literal["worked", "off", "closed", "holiday"]
    is_override: bool


class CalendarAgendaItemOut(BaseModel):
    id: str
    date: date
    end_date: Optional[date] = None
    category: Literal["leave", "planning", "absence", "event"]
    title: str
    subtitle: Optional[str] = None
    status: str
    worker_id: Optional[int] = None
    worker_name: Optional[str] = None
    leave_type_code: Optional[str] = None

class ToggleRequest(BaseModel):
    employer_id: int
    date: date
    is_worked: Optional[bool] = None
    status: Optional[Literal["worked", "off", "closed", "holiday"]] = None


def _default_status_for_date(value: date) -> str:
    return "worked" if value.weekday() < 5 else "off"


def _normalize_status(request_status: Optional[str], request_is_worked: Optional[bool], target_date: date) -> str:
    if request_status in {"worked", "off", "closed", "holiday"}:
        return request_status
    if request_is_worked is not None:
        return "worked" if request_is_worked else "off"
    return _default_status_for_date(target_date)


def _is_worked_from_status(status: str) -> bool:
    return status == "worked"


def _overlaps_month(start_value: date, end_value: date, month_start: date, month_end: date) -> bool:
    return start_value <= month_end and end_value >= month_start

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
    
    db_map = {}
    for db_day in db_days:
        stored_status = getattr(db_day, "status", None)
        if stored_status in {"worked", "off", "closed", "holiday"}:
            db_map[db_day.date] = stored_status
        else:
            db_map[db_day.date] = "worked" if db_day.is_worked else "off"
    
    # 2. Generate full month
    result = []
    
    for day in range(1, last_day + 1):
        curr = date(year, month, day)
        
        # Determine status
        if curr in db_map:
            status = db_map[curr]
            is_worked = _is_worked_from_status(status)
            is_override = True
        else:
            # Default: Mon-Fri worked (0-4), Sat-Sun off (5-6)
            status = _default_status_for_date(curr)
            is_worked = _is_worked_from_status(status)
            is_override = False
            
        result.append(CalendarDayOut(date=curr, is_worked=is_worked, status=status, is_override=is_override))
        
    return result


@router.get("/{employer_id}/{year}/{month}/agenda", response_model=List[CalendarAgendaItemOut])
def get_month_agenda(
    employer_id: int,
    year: int,
    month: int,
    worker_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    if not can_access_employer(db, user, employer_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    _, last_day = pycalendar.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)
    next_month_start = month_end + timedelta(days=1)

    workers = (
        db.query(models.Worker)
        .filter(models.Worker.employer_id == employer_id)
        .order_by(models.Worker.nom.asc(), models.Worker.prenom.asc())
        .all()
    )
    visible_workers = [item for item in workers if can_access_worker(db, user, item)]
    if worker_id is not None:
        visible_workers = [item for item in visible_workers if item.id == worker_id]
    visible_worker_ids = {item.id for item in visible_workers}
    worker_names = {
        item.id: " ".join(part for part in [item.nom or "", item.prenom or ""] if part).strip() or item.matricule or f"Salarie #{item.id}"
        for item in visible_workers
    }

    agenda: list[CalendarAgendaItemOut] = []

    if visible_worker_ids:
        requests = (
            db.query(models.LeaveRequest)
            .filter(
                models.LeaveRequest.employer_id == employer_id,
                models.LeaveRequest.worker_id.in_(visible_worker_ids),
                models.LeaveRequest.start_date <= month_end,
                models.LeaveRequest.end_date >= month_start,
                models.LeaveRequest.status.in_(
                    (
                        "submitted",
                        "pending_validation_1",
                        "pending_validation_2",
                        "pending_parallel",
                        "approved",
                        "integrated",
                        "requalified",
                    )
                ),
            )
            .order_by(models.LeaveRequest.start_date.asc(), models.LeaveRequest.id.asc())
            .all()
        )
        for item in requests:
            agenda.append(
                CalendarAgendaItemOut(
                    id=f"leave-{item.id}",
                    date=item.start_date,
                    end_date=item.end_date,
                    category="leave",
                    title=item.subject,
                    subtitle=item.final_leave_type_code,
                    status=item.status,
                    worker_id=item.worker_id,
                    worker_name=worker_names.get(item.worker_id),
                    leave_type_code=item.final_leave_type_code,
                )
            )

        proposals = (
            db.query(models.LeavePlanningProposal)
            .join(models.LeavePlanningCycle, models.LeavePlanningCycle.id == models.LeavePlanningProposal.cycle_id)
            .filter(
                models.LeavePlanningCycle.employer_id == employer_id,
                models.LeavePlanningProposal.worker_id.in_(visible_worker_ids),
                models.LeavePlanningProposal.start_date <= month_end,
                models.LeavePlanningProposal.end_date >= month_start,
            )
            .order_by(models.LeavePlanningProposal.start_date.asc(), models.LeavePlanningProposal.id.asc())
            .all()
        )
        for item in proposals:
            agenda.append(
                CalendarAgendaItemOut(
                    id=f"planning-{item.id}",
                    date=item.start_date,
                    end_date=item.end_date,
                    category="planning",
                    title=f"Proposition {item.leave_type_code}",
                    subtitle=f"Score {round(item.score or 0.0, 1)}",
                    status=item.status,
                    worker_id=item.worker_id,
                    worker_name=worker_names.get(item.worker_id),
                    leave_type_code=item.leave_type_code,
                )
            )

        period = f"{year:04d}-{month:02d}"
        absences = (
            db.query(models.Absence)
            .filter(
                models.Absence.worker_id.in_(visible_worker_ids),
                models.Absence.mois == period,
            )
            .order_by(models.Absence.worker_id.asc(), models.Absence.id.asc())
            .all()
        )
        for item in absences:
            details: list[str] = []
            for code in ("ABSM_J", "ABSM_H", "ABSNR_J", "ABSNR_H", "ABSMP", "ABS1_J", "ABS1_H", "ABS2_J", "ABS2_H"):
                value = float(getattr(item, code, 0.0) or 0.0)
                if value:
                    details.append(f"{code}: {value:g}")
            if not details:
                continue
            agenda.append(
                CalendarAgendaItemOut(
                    id=f"absence-{item.id}",
                    date=month_start,
                    end_date=month_end,
                    category="absence",
                    title="Synthese absences paie",
                    subtitle=" | ".join(details),
                    status="recorded",
                    worker_id=item.worker_id,
                    worker_name=worker_names.get(item.worker_id),
                )
            )

        histories = (
            db.query(models.LeaveRequestHistory)
            .join(models.LeaveRequest, models.LeaveRequest.id == models.LeaveRequestHistory.leave_request_id)
            .filter(
                models.LeaveRequest.employer_id == employer_id,
                models.LeaveRequest.worker_id.in_(visible_worker_ids),
                models.LeaveRequestHistory.created_at >= datetime.combine(month_start, time.min),
                models.LeaveRequestHistory.created_at < datetime.combine(next_month_start, time.min),
            )
            .order_by(models.LeaveRequestHistory.created_at.desc(), models.LeaveRequestHistory.id.desc())
            .all()
        )
        for item in histories[:120]:
            history_day = item.created_at.date()
            if not _overlaps_month(history_day, history_day, month_start, month_end):
                continue
            worker_ref = item.leave_request.worker_id if item.leave_request else None
            agenda.append(
                CalendarAgendaItemOut(
                    id=f"event-{item.id}",
                    date=history_day,
                    end_date=history_day,
                    category="event",
                    title=item.action,
                    subtitle=item.comment,
                    status=item.to_status or item.from_status or "logged",
                    worker_id=worker_ref,
                    worker_name=worker_names.get(worker_ref) if worker_ref is not None else None,
                    leave_type_code=item.leave_request.final_leave_type_code if item.leave_request else None,
                )
            )

    return agenda

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
    
    new_status = _normalize_status(req.status, req.is_worked, req.date)
    new_is_worked = _is_worked_from_status(new_status)

    if day_entry:
        day_entry.is_worked = new_is_worked
        day_entry.status = new_status
    else:
        day_entry = models.CalendarDay(
            employer_id=req.employer_id,
            date=req.date,
            is_worked=new_is_worked,
            status=new_status,
        )
        db.add(day_entry)
        
    db.commit()
    return {"message": "Updated"}
