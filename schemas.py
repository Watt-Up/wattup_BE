from datetime import datetime
from pydantic import BaseModel

# ---------- Station ----------
class StationItem(BaseModel):
    stat_id: str
    stat_nm: str
    addr: str
    lat: float | None = None
    lng: float | None = None

class StationResponse(BaseModel):
    regionName: str
    stations: list[StationItem]

# ---------- Reservation ----------
class ReservationCreateRequest(BaseModel):
    user_id: str
    stat_id: str
    start_dt: int  # datetime에서 int로 변경 (14시 등)
    end_dt: int    # datetime에서 int로 변경 (16시 등)

class ReservationCreateResponse(BaseModel):
    reserv_id: str
    status: str

class ReservationListItem(BaseModel):
    reserv_id: str
    user_id: str
    start_dt: datetime
    end_dt: datetime
    status: str

class ReservationListResponse(BaseModel):
    stat_id: str
    reservations: list[ReservationListItem]
