from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from another_fastapi_jwt_auth import AuthJWT
from core.auth.dependencies import validate_token
from core.iap.apple_jws import AppleJwsError
from core.iap.dto.request.google_verify_request import GooglePlayVerifyRequest
from core.iap.dto.request.verify_request import AppleIapVerifyRequest
from core.iap.dto.response.verify_response import AppleIapVerifyResponse
from core.iap.service.apple_iap_service import AppleIapService
from core.iap.service.google_play_iap_service import GooglePlayIapError, GooglePlayIapService
from core.user.service.user_service import UserService
from utilities.dbconfig import get_db

apple_iap_routes = APIRouter()


@apple_iap_routes.post("/apple/verify", response_model=AppleIapVerifyResponse)
def verify_apple_iap(
    request: AppleIapVerifyRequest,
    authjwt: AuthJWT = Depends(validate_token),
    db: Session = Depends(get_db),
):
    """Verify a StoreKit 2 signed transaction and grant consumable credits."""
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
        message=result.get("message") or "Credits added",
        credits_granted=result.get("credits_granted"),
        wallet_remaining=result.get("wallet_remaining"),
        pack_id=result.get("pack_id"),
        plan_name=result.get("plan_name"),
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


@apple_iap_routes.post("/google/verify", response_model=AppleIapVerifyResponse)
def verify_google_play_iap(
    request: GooglePlayVerifyRequest,
    authjwt: AuthJWT = Depends(validate_token),
    db: Session = Depends(get_db),
):
    """Verify a Google Play Billing purchase token and grant consumable credits."""
    user = UserService(db).get_current_user(authjwt.get_jwt_subject())
    service = GooglePlayIapService(db)
    try:
        result = service.apply_purchase(
            user_id=user.id,
            purchase_token=request.purchase_token,
            product_id=request.product_id,
            package_name=request.package_name,
            order_id=request.order_id,
        )
    except GooglePlayIapError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message") or "Google Play purchase could not be applied",
        )

    return AppleIapVerifyResponse(
        success=True,
        message=result.get("message") or "Credits added",
        credits_granted=result.get("credits_granted"),
        wallet_remaining=result.get("wallet_remaining"),
        pack_id=result.get("pack_id"),
        plan_name=result.get("plan_name"),
        product_id=result.get("product_id"),
        original_transaction_id=result.get("original_transaction_id"),
        environment=result.get("environment"),
    )


@apple_iap_routes.post("/google/notifications")
def google_play_notifications(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Google Play Real-time developer notifications (voided purchases)."""
    data = payload.get("voidedPurchaseNotification") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return {
            "success": True,
            "message": "Ignored Google Play notification without voided purchase",
        }

    token = str(data.get("purchaseToken") or "")
    GooglePlayIapService(db).handle_voided_purchase(token, "Google Play voided purchase")
    return {
        "success": True,
        "message": "Processed voided purchase",
        "purchase_token": token,
    }
