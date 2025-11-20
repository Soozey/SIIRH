from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..config.config import get_db
from .. import models, schemas

router = APIRouter(prefix="/employers", tags=["employers"])

@router.post("", response_model=schemas.EmployerOut)
def create_employer(data: schemas.EmployerIn, db: Session = Depends(get_db)):
    try:
        # Vérifier si le type_regime_id existe
        if data.type_regime_id:
            type_regime = db.query(models.TypeRegime).filter(models.TypeRegime.id == data.type_regime_id).first()
            if not type_regime:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"TypeRegime avec ID {data.type_regime_id} non trouvé"
                )
        
        obj = models.Employer(**data.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        print("Erreur SQLAlchemy:", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur base de données: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        print("Erreur générale:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne: {str(e)}"
        )

@router.get("", response_model=list[schemas.EmployerOut])
def list_employers(db: Session = Depends(get_db)):
    return db.query(models.Employer).all()
