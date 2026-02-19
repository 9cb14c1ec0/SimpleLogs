from pydantic import BaseModel


class VolumeBucket(BaseModel):
    bucket: str
    level: str | None = None
    source: str | None = None
    count: int


class VolumeResponse(BaseModel):
    buckets: list[VolumeBucket]
    totals: dict[str, int]


class TopItem(BaseModel):
    value: str
    count: int


class TopResponse(BaseModel):
    items: list[TopItem]


class HeatmapCell(BaseModel):
    source: str
    level: str
    count: int


class HeatmapResponse(BaseModel):
    sources: list[str]
    levels: list[str]
    data: list[HeatmapCell]


class TopUsersVolumeBucket(BaseModel):
    bucket: str
    user_id: str
    count: int


class TopUsersVolumeResponse(BaseModel):
    users: list[str]
    buckets: list[TopUsersVolumeBucket]
