from fastapi import HTTPException


class BillingNotFoundException(HTTPException):
    def __init__(self, message: str = "Billing record not found"):
        super().__init__(status_code=404, detail=message)


class BillingValidationException(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=400, detail=message)
