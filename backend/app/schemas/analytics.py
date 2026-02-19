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
