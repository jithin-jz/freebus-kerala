from pydantic import BaseModel, ConfigDict


class StopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_ml: str | None = None
    name_slug: str
    district: str
    lat: float | None = None
    lng: float | None = None
    is_major: bool = False

