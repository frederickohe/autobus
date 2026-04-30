from pydantic import BaseModel, HttpUrl


class ProfileImageUpdateRequest(BaseModel):
    profile_picture_url: HttpUrl

