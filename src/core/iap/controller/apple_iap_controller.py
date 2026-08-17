from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from another_fastapi_jwt_auth import AuthJWT
from core.auth.dependencies import validate_token
from core.iap.apple_jws import AppleJwsError
from core.iap.dto.request.verify_request import AppleIapVerifyRequest
from core.iap.dto.response.verify_response import AppleIapVerifyResponse
from core.iap.service.apple_iap_service import AppleIapService
from core.user.service.user_service import UserService
from utilities.dbconfig import get_db

apple_iap_routes = APIRouter()


@apple_iap_routes.post("/apple/verify", response_model=AppleIapVerifyResponse)
def verify_apple_iap(
    request: AppleIapVerifyRequest,
    authjwt: AuthJWT = Depends(validate_token),
    db: Session = Depends(get_db),
):
    """Verify a StoreKit 2 signed transaction and activate the user's subscription."""
    user = UserService(db).get_current_user(authjwt.get_jwt_subject())
    service = AppleIapService(db)
    try:
        result = service.apply_signed_transaction(
            user_id=user.id,
            signed_transaction=request.signed_transaction,
            expected_plan_id=request.plan_id,
            expected_billing_id=request.billing_id,
        )
    except AppleJwsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message") or "Apple In-App Purchase could not be applied",
        )

    return AppleIapVerifyResponse(
        success=True,
        message=result.get("message") or "Subscription activated",
        subscription_id=result.get("subscription_id"),
        plan_id=result.get("plan_id"),
        plan_name=result.get("plan_name"),
        expires_at=result.get("expires_at"),
        product_id=result.get("product_id"),
        original_transaction_id=result.get("original_transaction_id"),
        environment=result.get("environment"),
    )


@apple_iap_routes.post("/apple/notifications")
def apple_server_notifications(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """App Store Server Notifications V2 endpoint (no user JWT)."""
    signed = ""
    if isinstance(payload, dict):
        signed = str(payload.get("signedPayload") or "")
    if not signed:
        raise HTTPException(status_code=400, detail="Missing signedPayload")

    service = AppleIapService(db)
    try:
        return service.handle_server_notification(signed)
    except AppleJwsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
