from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session
from another_fastapi_jwt_auth import AuthJWT
from utilities.dbconfig import get_db
from core.auth.dependencies import validate_token, require_admin, get_current_user
from core.user.model.User import User
from core.user.service.user_service import UserService
from core.subscription.service.subscription_service import SubscriptionService
from core.subscription.dto.request.subscribe_request import SubscribeRequest
from core.subscription.dto.request.upgrade_request import UpgradeRequest
from core.subscription.dto.request.cancel_request import CancelRequest, MeSubscriptionCancelRequest
from core.subscription.dto.request.me_upgrade_request import MeUpgradeRequest
from core.subscription.dto.request.create_plan_request import CreatePlanRequest
from core.subscription.dto.request.update_plan_request import UpdatePlanRequest
from core.subscription.dto.response.subscription_response import (
    SubscriptionResponse, 
    SubscriptionStatusResponse, 
    PlansListResponse,
    PlanResponse,
    PlanCreateResponse
)

subscription_routes = APIRouter()


@subscription_routes.get("/me", response_model=SubscriptionStatusResponse)
def get_my_subscription_status(
    authjwt: AuthJWT = Depends(validate_token),
    db: Session = Depends(get_db),
):
    """Current user's subscription (JWT). Prefer this over `/status/{phone}` in clients."""
    user_service = UserService(db)
    user = user_service.get_current_user(authjwt.get_jwt_subject())
    subscription_service = SubscriptionService(db)
    data = subscription_service.get_user_subscription_status(user.id)
    return SubscriptionStatusResponse(**data)


@subscription_routes.post("/me/cancel", response_model=SubscriptionResponse)
def cancel_my_subscription(
    authjwt: AuthJWT = Depends(validate_token),
    db: Session = Depends(get_db),
    payload: Optional[MeSubscriptionCancelRequest] = Body(default=None),
):
    """Cancel the authenticated user's active subscription (no phone in request body)."""
    user_service = UserService(db)
    user = user_service.get_current_user(authjwt.get_jwt_subject())
    reason = payload.reason if payload else None
    subscription_service = SubscriptionService(db)
    result = subscription_service.cancel_subscription(user.id, reason)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"],
        )

    return SubscriptionResponse(**result)


@subscription_routes.post("/me/upgrade", response_model=SubscriptionResponse)
def upgrade_my_subscription(
    request: MeUpgradeRequest,
    authjwt: AuthJWT = Depends(validate_token),
    db: Session = Depends(get_db),
):
    """Upgrade the authenticated user's subscription (JWT)."""
    user_service = UserService(db)
    user = user_service.get_current_user(authjwt.get_jwt_subject())
    subscription_service = SubscriptionService(db)
    result = subscription_service.upgrade_subscription(
        user.id,
        request.new_plan_id,
        request.payment_reference,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"],
        )

    return SubscriptionResponse(**result)


@subscription_routes.get("/plans", response_model=PlansListResponse)
def get_subscription_plans(db: Session = Depends(get_db)):
    """Get all available subscription plans"""
    subscription_service = SubscriptionService(db)
    plans = subscription_service.get_all_plans()
    
    plan_responses = [
        PlanResponse(
            id=plan.id,
            name=plan.name,
            price=plan.price,
            features=plan.get_features_list(),
            agents=plan.get_agents_list(),
            description=plan.description,
            is_active=plan.is_active
        )
        for plan in plans
    ]
    
    return PlansListResponse(
        success=True,
        plans=plan_responses,
        total_count=len(plan_responses)
    )


@subscription_routes.post("/subscribe", response_model=SubscriptionResponse)
def subscribe_to_plan(
    request: SubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Subscribe authenticated user (phone in body must match account)."""
    if current_user.phone and request.phone and request.phone != current_user.phone:
        raise HTTPException(status_code=403, detail="Phone does not match authenticated user")
    subscription_service = SubscriptionService(db)
    result = subscription_service.subscribe_user_by_phone(
        phone=request.phone or current_user.phone,
        plan_id=request.plan_id,
        payment_reference=request.payment_reference
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return SubscriptionResponse(**result)


@subscription_routes.post("/upgrade", response_model=SubscriptionResponse)
def upgrade_subscription(
    request: UpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upgrade authenticated user's subscription (phone must match account)."""
    if current_user.phone and request.phone and request.phone != current_user.phone:
        raise HTTPException(status_code=403, detail="Phone does not match authenticated user")
    subscription_service = SubscriptionService(db)
    result = subscription_service.upgrade_subscription_by_phone(
        phone=request.phone or current_user.phone,
        new_plan_id=request.new_plan_id,
        payment_reference=request.payment_reference
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return SubscriptionResponse(**result)


@subscription_routes.post("/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    request: CancelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel authenticated user's subscription (phone must match account)."""
    if current_user.phone and request.phone and request.phone != current_user.phone:
        raise HTTPException(status_code=403, detail="Phone does not match authenticated user")
    subscription_service = SubscriptionService(db)
    result = subscription_service.cancel_subscription_by_phone(
        phone=request.phone or current_user.phone,
        reason=request.reason
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    
    return SubscriptionResponse(**result)


@subscription_routes.get("/status/{phone}", response_model=SubscriptionStatusResponse)
def get_subscription_status(
    phone: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get subscription status for the authenticated user's phone only."""
    if current_user.phone and phone != current_user.phone:
        raise HTTPException(status_code=403, detail="Phone does not match authenticated user")
    subscription_service = SubscriptionService(db)
    result = subscription_service.get_user_subscription_status_by_phone(phone)
    return SubscriptionStatusResponse(**result)


@subscription_routes.get("/check-feature/{feature}/{phone}")
def check_user_feature(
    feature: str,
    phone: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check feature access for the authenticated user's phone only."""
    if current_user.phone and phone != current_user.phone:
        raise HTTPException(status_code=403, detail="Phone does not match authenticated user")
    subscription_service = SubscriptionService(db)
    return subscription_service.check_user_has_feature_by_phone(phone, feature)


# ADMIN ENDPOINTS
@subscription_routes.post("/admin/plans", response_model=PlanCreateResponse)
def create_subscription_plan(
    request: CreatePlanRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new subscription plan (Admin only)"""
    subscription_service = SubscriptionService(db)
    result = subscription_service.create_subscription_plan(
        name=request.name,
        price=request.price,
        billing_period=request.billing_period,
        billing_period_count=request.billing_period_count,
        features=request.features,
        agents=request.agents,
        description=request.description,
        is_active=request.is_active
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    plan = result["plan"]
    return PlanCreateResponse(
        success=True,
        message=result["message"],
        plan=PlanResponse(
            id=plan.id,
            name=plan.name,
            price=plan.price,
            features=plan.get_features_list(),
            agents=plan.get_agents_list(),
            description=plan.description,
            is_active=plan.is_active
        )
    )



@subscription_routes.put("/admin/plans/{plan_id}", response_model=SubscriptionResponse)
def update_subscription_plan(
    plan_id: int,
    request: UpdatePlanRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a subscription plan (Admin only)"""
    subscription_service = SubscriptionService(db)
    
    # Filter out None values
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    
    result = subscription_service.update_subscription_plan(plan_id, **updates)
    
    if not result["success"]:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in result["message"].lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=result["message"])
    
    return SubscriptionResponse(**result)


@subscription_routes.delete("/admin/plans/{plan_id}", response_model=SubscriptionResponse)
def delete_subscription_plan(
    plan_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a subscription plan (Admin only)"""
    subscription_service = SubscriptionService(db)
    result = subscription_service.delete_subscription_plan(plan_id)
    
    if not result["success"]:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in result["message"].lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=result["message"])
    
    return SubscriptionResponse(**result)