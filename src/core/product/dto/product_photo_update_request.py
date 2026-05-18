from pydantic import BaseModel, HttpUrl


class ProductPhotoUpdateRequest(BaseModel):
    photo_url: HttpUrl
