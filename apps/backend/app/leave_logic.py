# backend/app/leave_logic.py
"""
Business logic for leave (congé) and permission calculations
"""
from datetime import date, datetime
from typing import List, Dict, Optional
import calendar
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_

from .models import Permission, Leave, RequestWorkflow, Worker


def _approved_or_legacy_filter(request_type: str, model_id_column):
    return or_(
        RequestWorkflow.id.is_(None),
        and_(
            RequestWorkflow.request_type == request_type,
            RequestWorkflow.request_id == model_id_column,
            RequestWorkflow.overall_status == "approved",
        ),
    )


def calculate_leave_accrual(worker: Worker, period: str) -> float:
    """
    Calculate prorated leave accrual for a specific period.
    
    Base rate: 2.5 days per month (30 days/year)
    Prorata for partial months based on hire/termination dates
    
    Args:
        worker: Worker instance
        period: Period in "YYYY-MM" format
        
    Returns:
        Float: Number of days accrued for this period
    """
    year, month = map(int, period.split("-"))
    days_in_month = calendar.monthrange(year, month)[1]
    
    # Default: full month accrual
    days_worked = days_in_month
    
    # Check if hired this month (partial month)
    if worker.date_embauche:
        hire_date = worker.date_embauche
        if hire_date.year == year and hire_date.month == month:
            # Hired mid-month: count from hire date to end of month
            days_worked = days_in_month - hire_date.day + 1
    
    # Check if terminated this month (partial month)
    # Using hasattr for forward compatibility when date_sortie is added to Worker model
    if hasattr(worker, 'date_sortie') and worker.date_sortie:
        term_date = worker.date_sortie
        if term_date.year == year and term_date.month == month:
            # Terminated mid-month: count from start of month to termination date
            # If also hired this month, count only days between hire and termination
            if worker.date_embauche and worker.date_embauche.year == year and worker.date_embauche.month == month:
                # Both hire and termination in same month
                days_worked = term_date.day - worker.date_embauche.day + 1
            else:
                # Only termination this month
                days_worked = term_date.day
    
    # Calculate prorated accrual
    accrual = 2.5 * (days_worked / days_in_month)
    return round(accrual, 2)


def calculate_leave_balance(db: Session, worker_id: int, up_to_period: str) -> Dict[str, float]:
    """
    Calculate total leave balance up to a specific period.
    
    Balance = Sum of accrued - Sum of taken
    
    Args:
        db: Database session
        worker_id: Worker ID
        up_to_period: Period in "YYYY-MM" format
        
    Returns:
        Dict with 'accrued', 'taken', and 'balance' keys
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker or not worker.date_embauche:
        return {"accrued": 0.0, "taken": 0.0, "balance": 0.0}
    
    # Generate all periods from hire date to up_to_period
    hire_date = worker.date_embauche
    
    if not up_to_period or "-" not in up_to_period:
        return {"accrued": 0.0, "taken": 0.0, "balance": 0.0}
        
    try:
        parts = up_to_period.split("-")
        if len(parts) != 2:
            return {"accrued": 0.0, "taken": 0.0, "balance": 0.0}
        up_to_year = int(parts[0])
        up_to_month = int(parts[1])
    except (ValueError, TypeError):
        return {"accrued": 0.0, "taken": 0.0, "balance": 0.0}
    
    total_accrued = worker.solde_conge_initial or 0.0
    current_date = date(hire_date.year, hire_date.month, 1)
    end_date = date(up_to_year, up_to_month, 1)
    
    while current_date <= end_date:
        period_str = current_date.strftime("%Y-%m")
        accrual = calculate_leave_accrual(worker, period_str)
        total_accrued += accrual
        
        # Move to next month
        if current_date.month == 12:
            current_date = date(current_date.year + 1, 1, 1)
        else:
            current_date = date(current_date.year, current_date.month + 1, 1)
    
    # Sum all leave taken up to this period
    total_taken = db.query(func.sum(Leave.days_taken)).outerjoin(
        RequestWorkflow,
        and_(
            RequestWorkflow.request_type == "leave",
            RequestWorkflow.request_id == Leave.id,
        ),
    ).filter(
        Leave.worker_id == worker_id,
        Leave.period <= up_to_period,
        _approved_or_legacy_filter("leave", Leave.id),
    ).scalar() or 0.0
    
    balance = total_accrued - total_taken
    
    return {
        "accrued": round(total_accrued, 2),
        "taken": round(total_taken, 2),
        "balance": round(balance, 2)
    }


def calculate_permission_balance(db: Session, worker_id: int, year: int) -> Dict[str, float]:
    """
    Calculate permission balance for a specific year.
    
    Annual allowance: 10 days
    Balance = 10 - Sum of taken in year
    
    Args:
        db: Database session
        worker_id: Worker ID
        year: Year (e.g., 2025)
        
    Returns:
        Dict with 'allowance', 'taken', and 'balance' keys
    """
    # Annual allowance
    allowance = 10.0
    
    # Sum all permissions taken in this year
    total_taken = db.query(func.sum(Permission.days_taken)).outerjoin(
        RequestWorkflow,
        and_(
            RequestWorkflow.request_type == "permission",
            RequestWorkflow.request_id == Permission.id,
        ),
    ).filter(
        Permission.worker_id == worker_id,
        Permission.period.like(f"{year}-%"),
        _approved_or_legacy_filter("permission", Permission.id),
    ).scalar() or 0.0
    
    balance = allowance - total_taken
    
    return {
        "allowance": allowance,
        "taken": round(total_taken, 2),
        "balance": round(balance, 2)
    }


def get_leave_summary_for_period(db: Session, worker_id: int, period: str) -> Dict:
    """
    Get leave summary for display on payslip.
    
    Returns:
        Dict with monthly taken, balance, and date range
    """
    # Get leaves for this specific period
    leaves_this_month = db.query(Leave).outerjoin(
        RequestWorkflow,
        and_(
            RequestWorkflow.request_type == "leave",
            RequestWorkflow.request_id == Leave.id,
        ),
    ).filter(
        Leave.worker_id == worker_id,
        Leave.period == period,
        _approved_or_legacy_filter("leave", Leave.id),
    ).all()
    
    if not leaves_this_month:
        balance_info = calculate_leave_balance(db, worker_id, period)
        return {
            "taken_this_month": 0.0,
            "balance": balance_info["balance"],
            "start_date": None,
            "end_date": None
        }
    
    # Sum days taken this month
    taken_this_month = sum(l.days_taken for l in leaves_this_month)
    
    # Format periods string
    periods = []
    sorted_leaves = sorted(leaves_this_month, key=lambda l: l.start_date)
    for leave in sorted_leaves:
        start = leave.start_date.strftime("%d/%m")
        end = leave.end_date.strftime("%d/%m")
        periods.append(f"{start}-{end}")
    
    periods_str = ", ".join(periods)
    
    # Calculate balance
    balance_info = calculate_leave_balance(db, worker_id, period)
    
    return {
        "taken_this_month": round(taken_this_month, 2),
        "balance": balance_info["balance"],
        "start_date": periods_str,
        "end_date": None
    }


def get_permission_summary_for_period(db: Session, worker_id: int, period: str) -> Dict:
    """
    Get permission summary for display on payslip.
    
    Returns:
        Dict with monthly taken and annual balance
    """
    year = int(period.split("-")[0])
    
    # Get permissions for this specific period
    perms_this_month = db.query(Permission).outerjoin(
        RequestWorkflow,
        and_(
            RequestWorkflow.request_type == "permission",
            RequestWorkflow.request_id == Permission.id,
        ),
    ).filter(
        Permission.worker_id == worker_id,
        Permission.period == period,
        _approved_or_legacy_filter("permission", Permission.id),
    ).all()
    
    taken_this_month = sum(p.days_taken for p in perms_this_month) if perms_this_month else 0.0
    
    # Calculate annual balance
    balance_info = calculate_permission_balance(db, worker_id, year)
    
    # Format periods string
    periods = []
    if perms_this_month:
        sorted_perms = sorted(perms_this_month, key=lambda p: p.start_date)
        for perm in sorted_perms:
            start = perm.start_date.strftime("%d/%m")
            end = perm.end_date.strftime("%d/%m")
            periods.append(f"{start}-{end}")
            
    periods_str = ", ".join(periods) if periods else None

    return {
        "taken_this_month": round(taken_this_month, 2),
        "balance": balance_info["balance"],
        "start_date": periods_str,
        "end_date": None
    }
