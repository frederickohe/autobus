from fastapi import APIRouter, Depends, HTTPException, Header
from another_fastapi_jwt_auth import AuthJWT
from another_fastapi_jwt_auth.exceptions import MissingTokenError
import jwt
from sqlalchemy.orm import Session
from core.auth.service.sessiondriver import SessionDriver, TokenData
from core.exceptions import *
from core.auth.dto.request.user_create import UserCreateRequest
from core.auth.dto.request.userlogin import UserLoginRequest
from core.auth.dto.request.resetpassword import ResetPasswordRequest
from core.auth.dto.request.resetpassnoauth import ResetPassNoAuth
from core.auth.dto.request.otp_verify import OTPVerifyRequest
from core.auth.dto.request.refresh_token import RefreshTokenRequest
from core.auth.dto.request.verify_account import VerifyAccountRequest
from core.auth.service.authservice import AuthService
from core.auth.service.linked_business_service import LinkedBusinessService
from core.auth.dto.request.linked_business import (
    CreateBusinessRequest,
    DetachBusinessRequest,
    SwitchBusinessRequest,
)
from core.auth.dto.response.linked_business import (
    LinkedBusinessItem,
    LinkedBusinessListResponse,
)
from core.auth.dto.request.delete_account import DeleteAccountRequest
from core.auth.dto.response.account_deletion import (
    AccountDeletionPreview,
    AccountDeletionResult,
)
from core.auth.service.account_deletion_service import AccountDeletionService
from core.auth.dependencies import resolve_user_from_jwt
from core.exceptions.AuthException import InvalidCredentialsError
from core.exceptions.UserException import UserAlreadyExistsError
from utilities.dbconfig import SessionLocal
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def validate_token(authjwt: AuthJWT = Depends()):
    try:
        authjwt.jwt_required()
        return authjwt
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired. Please log in again."
        )
    except MissingTokenError:
        raise HTTPException(
            status_code=401,
            detail="No token found. Please create an account and log in.",
        )
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


auth_routes = APIRouter()


@auth_routes.post("/signup")
def signup(request: UserCreateRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)

    return auth_service.create_user(request)


@auth_routes.post("/signin")
def signin(user: UserLoginRequest, db: Session = Depends(get_db), authjwt: AuthJWT = Depends()):
    auth_service = AuthService(db)

    return auth_service.signin(user)


@auth_routes.post("/signout")
def signout(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token found. Please log in.")
    token = authorization.removeprefix("Bearer ").strip()
    auth_service = AuthService(db)
    return auth_service.signout(token)


@auth_routes.post("/refresh")
def refresh_tokens(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.refresh_tokens(request.refresh_token)


@auth_routes.post("/verify-account")
async def verify_account(
    request: VerifyAccountRequest,
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    return auth_service.verify_account(request)


@auth_routes.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token)
):
    auth_service = AuthService(db)
    return auth_service.reset_password(request)


@auth_routes.post("/no-auth/reset-password")
async def reset_password_no_auth(
    request: ResetPassNoAuth,
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    return auth_service.reset_password_no_auth(request)


@auth_routes.post("/verify-otp")
def verify_otp(request: OTPVerifyRequest, db: Session = Depends(get_db)):
    """Verify OTP and enable user account"""
    auth_service = AuthService(db)
    result = auth_service.verify_and_enable_user(request.phone, request.otp)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message") or "Invalid or expired OTP",
        )
    return result


@auth_routes.get("/businesses", response_model=LinkedBusinessListResponse)
def list_businesses(
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    current_user = resolve_user_from_jwt(authjwt, db)
    return LinkedBusinessService(db).list_businesses(current_user, authjwt)


@auth_routes.post("/businesses", response_model=LinkedBusinessItem)
def create_business(
    request: CreateBusinessRequest,
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    current_user = resolve_user_from_jwt(authjwt, db)
    return LinkedBusinessService(db).create_business(current_user, authjwt, request)


@auth_routes.post("/switch-business")
def switch_business(
    request: SwitchBusinessRequest,
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    current_user = resolve_user_from_jwt(authjwt, db)
    return LinkedBusinessService(db).switch_business(current_user, authjwt, request)


@auth_routes.post("/businesses/{business_id}/send-detach-otp")
def send_detach_otp(
    business_id: str,
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    current_user = resolve_user_from_jwt(authjwt, db)
    return LinkedBusinessService(db).send_detach_otp(current_user, authjwt, business_id)


@auth_routes.post("/businesses/{business_id}/detach")
def detach_business(
    business_id: str,
    request: DetachBusinessRequest,
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    current_user = resolve_user_from_jwt(authjwt, db)
    return LinkedBusinessService(db).detach_business(
        current_user, authjwt, business_id, request
    )


@auth_routes.get("/account-deletion-preview", response_model=AccountDeletionPreview)
def account_deletion_preview(
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    current_user = resolve_user_from_jwt(authjwt, db)
    return AccountDeletionService(db).preview(current_user, authjwt)


@auth_routes.delete("/me", response_model=AccountDeletionResult)
@auth_routes.post("/delete-account", response_model=AccountDeletionResult)
async def delete_my_account(
    request: DeleteAccountRequest,
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    current_user = resolve_user_from_jwt(authjwt, db)
    return await AccountDeletionService(db).delete_account(
        current_user, authjwt, request.password
    )
