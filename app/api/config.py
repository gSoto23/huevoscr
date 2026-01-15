from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from pydantic import BaseModel
from .. import database, models, auth

router = APIRouter(
    prefix="/config",
    tags=["Configuration"]
)

class ConfigItem(BaseModel):
    key: str
    value: str

@router.get("/", response_model=List[ConfigItem])
def get_all_configs(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    # Any active user can read configs (needed for frontend logic like dropdowns/prices)
    configs = db.query(models.Config).all()
    return configs

@router.get("/{key}", response_model=ConfigItem)
def get_config(key: str, db: Session = Depends(database.get_db)):
    config = db.query(models.Config).filter(models.Config.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config

@router.post("/", response_model=ConfigItem)
def set_config(
    item: ConfigItem, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    # Only admin can set configs
    config = db.query(models.Config).filter(models.Config.key == item.key).first()
    if config:
        config.value = item.value
    else:
        config = models.Config(key=item.key, value=item.value)
        db.add(config)
    
    db.commit()
    db.refresh(config)
    return config

@router.delete("/{key}")
def delete_config(
    key: str, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    config = db.query(models.Config).filter(models.Config.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    db.delete(config)
    db.commit()
    return {"status": "deleted"}
