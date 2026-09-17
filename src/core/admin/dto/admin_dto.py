from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from core.auth.dto.request.password_policy import PASSWORD_MIN_LENGTH

AdminRoleLiteral = Literal["super_admin", "admin", "support"]
AdminRoleLabel = Literal["Super Admin", "Admin", "Support"]


class AdminSignInRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=100)


class AdminMeResponse(BaseModel):
    id: str
    fullName: str
    email: str
    role: AdminRoleLabel
    status: str = "active"


class AdminAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AdminMeResponse


class OnboardingAnswer(BaseModel):
    question: str
    answer: str


class MerchantResponse(BaseModel):
    id: str
    company: str
    fullName: str
    email: str
    phone: str
    currency: str
    status: str
    enabled: bool
    onboardingCompleted: bool
    created: str
    location: Optional[str] = None
    ghanaCard: Optional[str] = None
    onboardingAnswers: Optional[List[OnboardingAnswer]] = None


class CustomerResponse(BaseModel):
    id: str
    fullName: str
    email: str
    phone: str
    merchantId: str
    merchantName: str
    totalOrders: int
    totalSpent: float
    currency: str
    status: str
    joined: str


class CustomerUpdateRequest(BaseModel):
    fullName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class PlanAdminResponse(BaseModel):
    id: str
    name: str
    price: float
    billingPeriod: Literal["monthly", "annually"]
    billingPeriodCount: int
    features: List[str]
    agents: List[str]
    description: str
    active: bool
    appleProductIds: List[str]


class PlanUpsertRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., ge=0)
    billingPeriod: Literal["monthly", "annually"] = "monthly"
    billingPeriodCount: int = Field(1, gt=0)
    features: List[str] = Field(default_factory=list)
    agents: List[str] = Field(default_factory=list)
    description: str = ""
    active: bool = True
    appleProductIds: List[str] = Field(default_factory=list)


class SenderIdAdminResponse(BaseModel):
    id: str
    senderId: str
    company: str
    notes: str
    status: str
    created: str
    reviewed: Optional[str] = None
    rejectionReason: Optional[str] = None


class SenderIdRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


class TransactionAdminResponse(BaseModel):
    id: str
    reference: str
    merchantName: str
    planName: str
    amount: float
    currency: str
    paymentMethod: str
    status: str
    date: str
    dateISO: str


class AdResponse(BaseModel):
    id: str
    title: str
    type: Literal["image", "video"]
    mediaUrl: str
    linkUrl: Optional[str] = None
    active: bool
    startDate: str
    endDate: str
    createdOn: str


class AdUpsertRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    type: Literal["image", "video"] = "image"
    mediaUrl: str = Field(..., min_length=1)
    linkUrl: Optional[str] = None
    active: bool = True
    startDate: date
    endDate: date


class AdminUserResponse(BaseModel):
    id: str
    fullName: str
    email: str
    role: AdminRoleLabel
    status: str
    invitedOn: str
    lastActive: Optional[str] = None
    isCurrentUser: bool = False
    envLocked: bool = False


class AdminInviteRequest(BaseModel):
    fullName: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    role: AdminRoleLabel = "Admin"


class AdminRoleUpdateRequest(BaseModel):
    role: AdminRoleLabel


class DashboardKpi(BaseModel):
    label: str
    value: str
    icon: str
    change: str
    bg: str


class DashboardCurrency(BaseModel):
    code: str
    percent: int


class DashboardSenderQueueItem(BaseModel):
    id: str
    company: str
    created: str


class DashboardResponse(BaseModel):
    kpis: List[DashboardKpi]
    weekLabels: List[str]
    weekSignups: List[int]
    enabledCount: int
    disabledCount: int
    onboardingCompletion: int
    currencyBreakdown: List[DashboardCurrency]
    senderIdQueue: List[DashboardSenderQueueItem]


class PasswordResetRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=12)
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)
