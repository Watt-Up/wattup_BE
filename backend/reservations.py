from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, time

def generate_ulid_26() -> str:
    try:
        import ulid
        if hasattr(ulid, "new"):
            s = ulid.new().str
            if isinstance(s, str) and len(s) == 26:
                return s
    except Exception:
        pass

    try:
        from ulid import ULID
        s = str(ULID())
        if isinstance(s, str) and len(s) == 26:
            return s
    except Exception:
        pass

    raise RuntimeError("ULID 생성 실패")


from db_postgres import get_pg
from schemas import (
    ReservationCreateRequest,
    ReservationCreateResponse,
    ReservationListResponse,
)

router = APIRouter(tags=["reservations"])


# =========================
# 예약 생성
# =========================
@router.post("/reservations", response_model=ReservationCreateResponse)
async def create_reservation(req: ReservationCreateRequest, db: Session = Depends(get_pg)):

    if req.start_dt >= req.end_dt:
        raise HTTPException(status_code=400, detail="start_dt는 end_dt보다 작아야 함")

    today = datetime.now().date()
    start_dt_obj = datetime.combine(today, time(hour=req.start_dt))

    if req.end_dt == 24:
        end_dt_obj = datetime.combine(today, time(hour=23, minute=59, second=59))
    else:
        end_dt_obj = datetime.combine(today, time(hour=req.end_dt))

    # 예약 겹침 체크
    conflict_query = text("""
        SELECT 1
        FROM ev_reservation
        WHERE stat_id = :stat_id
          AND start_dt < :end_dt
          AND end_dt > :start_dt
        LIMIT 1
    """)

    conflict = db.execute(conflict_query, {
        "stat_id": req.stat_id,
        "start_dt": start_dt_obj,
        "end_dt": end_dt_obj
    }).first()

    if conflict:
        raise HTTPException(
            status_code=400,
            detail="이미 해당 시간에 예약이 존재합니다."
        )

    new_reserv_id = generate_ulid_26()

    insert_query = text("""
        INSERT INTO ev_reservation
        (reserv_id, user_id, status, stat_id, start_dt, end_dt)
        VALUES
        (:reserv_id, :user_id, 'READY', :stat_id, :start_dt, :end_dt)
    """)

    db.execute(insert_query, {
        "reserv_id": new_reserv_id,
        "user_id": req.user_id,
        "stat_id": req.stat_id,
        "start_dt": start_dt_obj,
        "end_dt": end_dt_obj
    })

    db.commit()

    return {
        "reserv_id": new_reserv_id,
        "status": "READY"
    }


# =========================
# 예약 목록 조회
# =========================
@router.get("/stations/{stat_id}/reservations", response_model=ReservationListResponse)
def list_reservations(stat_id: str, db: Session = Depends(get_pg)):

    query = text("""
        SELECT reserv_id, user_id, start_dt, end_dt, status
        FROM ev_reservation
        WHERE stat_id = :stat_id
        ORDER BY start_dt ASC
    """)

    rows = db.execute(query, {"stat_id": stat_id}).fetchall()

    reservations = []

    for r in rows:

        # 여기서 READY → USED 변환
        status_out = "USED" if r.status == "READY" else r.status

        reservations.append({
            "reserv_id": str(r.reserv_id),
            "user_id": r.user_id,
            "start_dt": r.start_dt,
            "end_dt": r.end_dt,
            "status": status_out
        })

    return {
        "stat_id": stat_id,
        "reservations": reservations
    }
