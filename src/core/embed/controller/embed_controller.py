"""Portal settings use the business login. Partner calls use the embed API key."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth.dependencies import get_current_user, get_db
from core.embed.service.embed_service import EmbedService
from core.user.model.User import User

portal_embed_routes = APIRouter()
embed_routes = APIRouter()


class EmbedSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    catalog_mode: Optional[str] = None
    enforce_stock: Optional[bool] = None
    handoff_enabled: Optional[bool] = None


class EmbedSubBusiness(BaseModel):
    external_id: str = Field(..., min_length=1, max_length=128)
    name: Optional[str] = None


class EmbedCustomer(BaseModel):
    external_id: str = Field(..., min_length=1, max_length=128)
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class EmbedMessageBody(BaseModel):
    id: str = Field(..., min_length=1, max_length=128)
    text: str = Field(..., min_length=1, max_length=4000)


class EmbedTurnRequest(BaseModel):
    conversation_id: Optional[str] = None
    sub_business: Optional[EmbedSubBusiness] = None
    customer: EmbedCustomer
    message: EmbedMessageBody


class EmbedCatalogItem(BaseModel):
    external_id: str
    sub_business: Optional[EmbedSubBusiness] = None
    kind: str = "product"
    name: str
    description: Optional[str] = None
    price: Optional[Dict[str, Any]] = None
    stock: Optional[Dict[str, Any]] = None
    category: Optional[str] = None
    active: bool = True
    image_url: Optional[str] = None
    link: Optional[str] = None


class EmbedCatalogSync(BaseModel):
    sub_business: Optional[EmbedSubBusiness] = None
    items: List[EmbedCatalogItem] = Field(..., min_length=1, max_length=200)


class EmbedOrderUpdate(BaseModel):
    payment_status: Optional[str] = None
    fulfillment_status: Optional[str] = None
    order_status: Optional[str] = None
    payment_reference: Optional[str] = None
    external_customer_id: Optional[str] = None
    sub_business: Optional[EmbedSubBusiness] = None


def _bearer(authorization: Optional[str], x_api_key: Optional[str]) -> str:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")


def _integration(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-Api-Key"),
):
    service = EmbedService(db)
    try:
        return service.authenticate(_bearer(authorization, x_api_key))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@portal_embed_routes.get("/settings")
def get_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = EmbedService(db)
    return service.public_settings(service.get_or_create(current_user.id))


@portal_embed_routes.put("/settings")
def put_settings(
    body: EmbedSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = EmbedService(db)
    try:
        row = service.update_settings(current_user.id, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return service.public_settings(row)


@portal_embed_routes.post("/settings/keys")
def rotate_key(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = EmbedService(db)
    row, raw = service.rotate_key(current_user.id)
    payload = service.public_settings(row)
    payload["api_key"] = raw
    return payload


@embed_routes.post("/messages")
def post_message(body: EmbedTurnRequest, integration=Depends(_integration), db: Session = Depends(get_db)):
    service = EmbedService(db)
    try:
        return service.handle_message(integration, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@embed_routes.put("/catalog")
def put_catalog(body: EmbedCatalogSync, integration=Depends(_integration), db: Session = Depends(get_db)):
    service = EmbedService(db)
    try:
        parent = body.sub_business.model_dump() if body.sub_business else None
        return service.upsert_catalog(integration, [item.model_dump() for item in body.items], parent)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@embed_routes.get("/catalog")
def get_catalog(
    integration=Depends(_integration),
    db: Session = Depends(get_db),
    sub_business: Optional[str] = Query(None),
):
    return {"items": EmbedService(db).list_catalog(integration, (sub_business or "").strip())}


@embed_routes.post("/orders/{order_number}")
def post_order_update(
    order_number: str,
    body: EmbedOrderUpdate,
    integration=Depends(_integration),
    db: Session = Depends(get_db),
):
    service = EmbedService(db)
    try:
        return service.update_order(integration, order_number, body.model_dump(exclude_unset=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
