# backend/app/routers/type_regimes.py
from typing import Any, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..config.config import get_db
from .. import models, schemas
from ..security import READ_PAYROLL_ROLES, require_roles
from ..services.audit_service import record_audit
from ..services.tabular_io import (
    build_column_mapping,
    dataframe_to_csv_bytes,
    dataframe_to_xlsx_bytes,
    read_tabular_bytes,
)

router = APIRouter(prefix="/type_regimes", tags=["type_regimes"])
REGIME_WRITE_ROLES = {"admin", "rh"}
TYPE_REGIME_TEMPLATE_COLUMNS = ["Code", "Libelle", "VHM"]
TYPE_REGIME_REQUIRED_COLUMNS = ["Code", "Libelle", "VHM"]


# ---------- Helpers ----------
def _default_regime_payloads() -> list[dict]:
    return [
        {"code": "agricole", "label": "Regime Agricole", "vhm": 200.0},
        {"code": "non_agricole", "label": "Regime Non Agricole", "vhm": 173.33},
    ]


def _ensure_default_regimes(db: Session) -> None:
    if db.query(models.TypeRegime.id).first():
        return
    for payload in _default_regime_payloads():
        db.add(models.TypeRegime(**payload))
    db.commit()


def _get_or_404(db: Session, regime_id: int) -> models.TypeRegime:
    obj = db.query(models.TypeRegime).get(regime_id)
    if not obj:
        raise HTTPException(status_code=404, detail="TypeRegime not found")
    return obj


def _add_issue(
    issues: list[dict[str, Any]],
    *,
    row_number: int,
    code: str,
    message: str,
    column: Optional[str] = None,
    value: Optional[Any] = None,
) -> None:
    issues.append(
        {
            "row_number": row_number,
            "column": column,
            "code": code,
            "message": message,
            "value": None if value is None else str(value),
        }
    )


def _build_report(
    *,
    mode: str,
    total_rows: int,
    processed_rows: int,
    created: int,
    updated: int,
    skipped: int,
    failed: int,
    unknown_columns: list[str],
    missing_columns: list[str],
    issues: list[dict[str, Any]],
) -> schemas.TabularImportReport:
    return schemas.TabularImportReport(
        mode=mode,
        total_rows=total_rows,
        processed_rows=processed_rows,
        created=created,
        updated=updated,
        skipped=skipped,
        failed=failed,
        unknown_columns=unknown_columns,
        missing_columns=missing_columns,
        issues=[schemas.TabularImportIssue(**issue) for issue in issues],
        summary=(
            f"{created} cree(s), {updated} mis a jour, {skipped} ignore(s), {failed} en erreur."
        ),
    )


# ---------- List with filters ----------
@router.get("", response_model=List[schemas.TypeRegimeOut])
def list_type_regimes(
    q: Optional[str] = Query(None, description="Recherche sur code/label (contient)"),
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    if not q:
        _ensure_default_regimes(db)
    query = db.query(models.TypeRegime)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (models.TypeRegime.code.ilike(like)) | (models.TypeRegime.label.ilike(like))
        )
    return query.offset(skip).limit(limit).all()


# ---------- Retrieve ----------
@router.get("/{regime_id}", response_model=schemas.TypeRegimeOut)
def retrieve_type_regime(
    regime_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    return _get_or_404(db, regime_id)


# ---------- Create ----------
@router.post("", response_model=schemas.TypeRegimeOut, status_code=status.HTTP_201_CREATED)
def create_type_regime(
    data: schemas.TypeRegimeIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REGIME_WRITE_ROLES)),
):
    # Unicité du code
    if db.query(models.TypeRegime).filter_by(code=data.code).first():
        raise HTTPException(status_code=400, detail="Code already exists")
    obj = models.TypeRegime(**data.dict())
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Double filet de sécurité si contrainte d'unicité côté DB
        raise HTTPException(status_code=400, detail="Code already exists")
    db.refresh(obj)
    return obj


# ---------- Full update (PUT) ----------
@router.put("/{regime_id}", response_model=schemas.TypeRegimeOut)
def update_type_regime(
    regime_id: int,
    data: schemas.TypeRegimeIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REGIME_WRITE_ROLES)),
):
    obj = _get_or_404(db, regime_id)

    # Empêcher la collision de codes
    if db.query(models.TypeRegime).filter(
        models.TypeRegime.code == data.code,
        models.TypeRegime.id != regime_id
    ).first():
        raise HTTPException(status_code=400, detail="Code already exists")

    for k, v in data.dict().items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Unique constraint failed")
    db.refresh(obj)
    return obj


# ---------- Partial update (PATCH) ----------
@router.patch("/{regime_id}", response_model=schemas.TypeRegimeOut)
def patch_type_regime(
    regime_id: int,
    data: schemas.TypeRegimeIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REGIME_WRITE_ROLES)),
):
    obj = _get_or_404(db, regime_id)
    payload = data.dict(exclude_unset=True)

    # Collision éventuelle sur code
    new_code = payload.get("code")
    if new_code and db.query(models.TypeRegime).filter(
        models.TypeRegime.code == new_code,
        models.TypeRegime.id != regime_id
    ).first():
        raise HTTPException(status_code=400, detail="Code already exists")

    for k, v in payload.items():
        setattr(obj, k, v)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Unique constraint failed")
    db.refresh(obj)
    return obj


# ---------- Delete ----------
@router.delete("/{regime_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_type_regime(
    regime_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REGIME_WRITE_ROLES)),
):
    obj = _get_or_404(db, regime_id)

    # Empêcher la suppression si des employeurs y sont liés (optionnel)
    linked = db.query(models.Employer).filter(models.Employer.type_regime_id == regime_id).first()
    if linked:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: regime is referenced by at least one employer",
        )

    db.delete(obj)
    db.commit()
    return None


# ---------- Seed defaults (pratique) ----------
@router.post("/seed-defaults", response_model=List[schemas.TypeRegimeOut])
def seed_defaults(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REGIME_WRITE_ROLES)),
):
    """
    Crée/Met à jour les deux régimes standards.
    Adapte les VHM selon ta règle métier.
    """
    defaults = [
        {"code": "agricole", "label": "Régime Agricole", "vhm": 200.0},
        {"code": "non_agricole", "label": "Régime Non Agricole", "vhm": 173.33},
    ]
    out = []
    for d in defaults:
        obj = db.query(models.TypeRegime).filter_by(code=d["code"]).first()
        if obj:
            obj.label = d["label"]
            obj.vhm = d["vhm"]
        else:
            obj = models.TypeRegime(**d)
            db.add(obj)
        db.commit()
        db.refresh(obj)
        out.append(obj)
    return out


@router.get("/import/template")
def download_type_regimes_template(
    prefilled: bool = Query(False),
    export_format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    if prefilled:
        rows = [
            {
                "Code": item.code,
                "Libelle": item.label,
                "VHM": float(item.vhm),
            }
            for item in db.query(models.TypeRegime).order_by(models.TypeRegime.code.asc()).all()
        ]
    else:
        rows = [{"Code": "agricole", "Libelle": "Regime Agricole", "VHM": 200}]

    df = pd.DataFrame(rows, columns=TYPE_REGIME_TEMPLATE_COLUMNS)
    if export_format == "csv":
        content = dataframe_to_csv_bytes(df)
        filename = "type_regimes_template_prefilled.csv" if prefilled else "type_regimes_template.csv"
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    content = dataframe_to_xlsx_bytes(df, sheet_name="TypeRegimes")
    filename = "type_regimes_template_prefilled.xlsx" if prefilled else "type_regimes_template.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=schemas.TabularImportReport)
async def import_type_regimes(
    file: UploadFile = File(...),
    update_existing: bool = Form(True),
    dry_run: bool = Form(False),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REGIME_WRITE_ROLES)),
):
    content = await file.read()
    df = read_tabular_bytes(content, file.filename)
    mapping, unknown_columns, missing_columns = build_column_mapping(
        df.columns.tolist(),
        TYPE_REGIME_TEMPLATE_COLUMNS,
        TYPE_REGIME_REQUIRED_COLUMNS,
    )
    issues: list[dict[str, Any]] = []
    if unknown_columns:
        _add_issue(
            issues,
            row_number=1,
            code="unknown_columns",
            message=f"Colonnes inconnues: {', '.join(unknown_columns)}",
        )
    if missing_columns:
        _add_issue(
            issues,
            row_number=1,
            code="missing_columns",
            message=f"Colonnes obligatoires manquantes: {', '.join(missing_columns)}",
        )
    if unknown_columns or missing_columns:
        return _build_report(
            mode="mixed" if update_existing else "create",
            total_rows=0,
            processed_rows=0,
            created=0,
            updated=0,
            skipped=0,
            failed=0,
            unknown_columns=unknown_columns,
            missing_columns=missing_columns,
            issues=issues,
        )

    created = 0
    updated = 0
    skipped = 0
    failed = 0

    for idx, row in df.iterrows():
        row_number = idx + 2
        raw_code = row.get(mapping["Code"])
        raw_label = row.get(mapping["Libelle"])
        raw_vhm = row.get(mapping["VHM"])

        if pd.isna(raw_code) or str(raw_code).strip() == "":
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                column="Code",
                code="missing_code",
                message="Code regime requis.",
                value=raw_code,
            )
            continue
        if pd.isna(raw_label) or str(raw_label).strip() == "":
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                column="Libelle",
                code="missing_label",
                message="Libelle regime requis.",
                value=raw_label,
            )
            continue

        code = str(raw_code).strip()
        label = str(raw_label).strip()
        try:
            vhm = float(raw_vhm)
        except (TypeError, ValueError):
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                column="VHM",
                code="invalid_vhm",
                message="VHM doit etre numerique.",
                value=raw_vhm,
            )
            continue
        if vhm <= 0:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                column="VHM",
                code="invalid_vhm",
                message="VHM doit etre strictement positif.",
                value=raw_vhm,
            )
            continue

        existing = db.query(models.TypeRegime).filter(models.TypeRegime.code == code).first()
        if existing:
            if not update_existing:
                skipped += 1
                continue
            updated += 1
            if not dry_run:
                existing.label = label
                existing.vhm = vhm
        else:
            created += 1
            if not dry_run:
                db.add(models.TypeRegime(code=code, label=label, vhm=vhm))

    processed_rows = created + updated
    if not dry_run:
        db.flush()
        record_audit(
            db,
            actor=user,
            action="type_regime.import",
            entity_type="type_regime",
            entity_id="bulk",
            route="/type_regimes/import",
            after={
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "failed": failed,
                "dry_run": dry_run,
                "update_existing": update_existing,
            },
        )
        db.commit()

    return _build_report(
        mode="mixed" if update_existing else "create",
        total_rows=int(len(df.index)),
        processed_rows=processed_rows,
        created=created,
        updated=updated,
        skipped=skipped,
        failed=failed,
        unknown_columns=unknown_columns,
        missing_columns=missing_columns,
        issues=issues,
    )
