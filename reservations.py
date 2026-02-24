from fastapi import APIRouter, Depends
from ulid import ULID
from db_mongo import get_mongo
from schemas import ReservationCreateRequest, ReservationCreateResponse

router = APIRouter(tags=["reservations"])


@router.post("/reservations", response_model=ReservationCreateResponse)
def create_reservation(req: ReservationCreateRequest):

    db = get_mongo()
    reserv_id = str(ULID())

    document = {
        "reserv_id": reserv_id,
        "user_id": req.user_id,
        "stat_id": req.stat_id,
        "start_dt": req.start_dt,
        "end_dt": req.end_dt,
        "status": "READY"
    }

    db.ev_reservation.insert_one(document)

    return {"reserv_id": reserv_id, "status": "READY"}