from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
import json
from datetime import datetime

from app.database import get_db
from app import models, schemas
from app.services.marketing_service import fetch_meta_templates, send_meta_template

router = APIRouter(
    prefix="/api/v1/marketing",
    tags=["marketing"],
)

@router.post("/templates/sync")
async def sync_templates(db: Session = Depends(get_db)):
    """Sincroniza las plantillas desde Meta a la base de datos local."""
    waba_id = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    
    if not waba_id or not access_token:
        raise HTTPException(status_code=500, detail="Faltan credenciales de Meta en las variables de entorno.")
    
    try:
        meta_templates = await fetch_meta_templates(waba_id, access_token)
        
        synced_count = 0
        for tpl in meta_templates:
            # upsert based on meta_id (which is template 'id' from Meta)
            meta_id = tpl.get("id")
            existing = db.query(models.MarketingTemplate).filter(models.MarketingTemplate.meta_id == meta_id).first()
            
            components_str = json.dumps(tpl.get("components", []))
            
            if existing:
                existing.name = tpl.get("name")
                existing.language = tpl.get("language")
                existing.components = components_str
                existing.status = tpl.get("status")
            else:
                new_tpl = models.MarketingTemplate(
                    meta_id=meta_id,
                    name=tpl.get("name"),
                    language=tpl.get("language"),
                    components=components_str,
                    status=tpl.get("status")
                )
                db.add(new_tpl)
            synced_count += 1
            
        db.commit()
        return {"status": "success", "synced": synced_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error sincronizando con Meta: {str(e)}")

@router.get("/templates", response_model=List[schemas.MarketingTemplate])
def get_templates(db: Session = Depends(get_db)):
    return db.query(models.MarketingTemplate).all()

@router.post("/campaigns", response_model=schemas.Campaign)
def create_campaign(campaign_in: schemas.CampaignCreate, db: Session = Depends(get_db)):
    new_campaign = models.Campaign(
        name=campaign_in.name,
        template_id=campaign_in.template_id,
        variables_mapping=campaign_in.variables_mapping,
        status="draft"
    )
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)
    return new_campaign

@router.post("/campaigns/{campaign_id}/recipients")
def add_recipients(campaign_id: int, payload: schemas.CampaignRecipientAddList, db: Session = Depends(get_db)):
    campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
        
    for w_id in payload.whatsapp_ids:
        # Check if already exists
        ext = db.query(models.CampaignRecipient).filter_by(campaign_id=campaign_id, whatsapp_id=w_id).first()
        if not ext:
            new_rec = models.CampaignRecipient(
                campaign_id=campaign_id,
                whatsapp_id=w_id,
                status="pending"
            )
            db.add(new_rec)
            
    db.commit()
    return {"status": "success", "message": f"{len(payload.whatsapp_ids)} destinatarios añadidos."}

async def execute_campaign_task(campaign_id: int, db: Session):
    """Función en segundo plano para procesar los envíos masivos."""
    campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
    if not campaign or campaign.status == "completed":
        return

    campaign.status = "running"
    db.commit()
    
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    
    if not phone_number_id or not access_token:
        # Can't proceed
        campaign.status = "failed_credentials"
        db.commit()
        return

    # Mapeo guardado como json string a dictionary
    try:
        mapping = json.loads(campaign.variables_mapping) if campaign.variables_mapping else {}
    except:
        mapping = {}

    template = campaign.template
    
    recipients = db.query(models.CampaignRecipient).filter_by(campaign_id=campaign_id, status="pending").all()
    
    for rec in recipients:
        customer = rec.customer
        if not customer:
            rec.status = "failed"
            rec.error_message = "Cliente no encontrado"
            db.commit()
            continue
            
        # Armar las variables
        # Meta usa parameters list. Supondremos que construimos los components basándonos en la plantilla
        # En una impl. completa real, se parsea exacto. Usaremos algo genérico para reemplazo en 'body'.
        # En el 'mapping', el frontend envía keys que se ajustan al componente.
        # Por simplicidad aquí construiremos los parameters del body.
        
        # Ejemplo: mapping es {"1": "name", "2": "address"}
        # Recuperamos atributos de 'customer': getattr(customer, "name")
        parameters = []
        for key, prop in mapping.items():
            val = getattr(customer, prop, "")
            parameters.append({
                "type": "text",
                "text": str(val) if val else " "
            })
            
        # Construir components simplificado para el envio (usando solo body parameters)
        req_components = []
        if parameters:
            req_components = [{
                "type": "body",
                "parameters": parameters
            }]
            
        try:
            await send_meta_template(
                phone_number_id=phone_number_id,
                access_token=access_token,
                to_number=rec.whatsapp_id,
                template_name=template.name,
                language_code=template.language,
                components=req_components
            )
            rec.status = "sent"
            rec.sent_at = datetime.utcnow()
        except Exception as e:
            rec.status = "failed"
            rec.error_message = str(e)
            
        db.commit() # Commit iterativo para ver progreso en tiempo real
        
    # Fin de campaña
    campaign.status = "completed"
    db.commit()

@router.post("/campaigns/{campaign_id}/execute")
async def execute_campaign(campaign_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
        
    if campaign.template.status != "APPROVED":
        raise HTTPException(status_code=400, detail="La plantilla seleccionada no está aprobada por Meta.")

    # Inicia tarea en segundo plano para no bloquear a FastAPI
    background_tasks.add_task(execute_campaign_task, campaign_id, db)
    
    return {"status": "success", "message": "Ejecución iniciada en segundo plano."}
