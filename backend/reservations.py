from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, time

def generate_ulid_26() -> str:
    try:
        import ulid  # python-ulid
        if hasattr(ulid, "new"):
            s = ulid.new().str
            if isinstance(s, str) and len(s) == 26:
                return s
    except Exception:
        pass

    try:
        from ulid import ULID  # ulid-py
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


@router.post("/reservations", response_model=ReservationCreateResponse)
async def create_reservation(req: ReservationCreateRequest, db: Session = Depends(get_pg)):
    """
    예약 생성 규칙
    - start_dt: 필수 (0~23)
    - end_dt:
      (1) end_dt가 아예 없으면(또는 0/None으로 오면) => end_dt = start_dt + 2
      (2) end_dt = start_dt + 1 로 오면 => end_dt = end_dt + 1 (즉 start + 2)
      (3) 최종 end_dt는 최대 24까지 허용
    """

    # =========================
    # 0) start_dt 검증
    # =========================
    if not isinstance(req.start_dt, int):
        raise HTTPException(status_code=400, detail="start_dt는 정수(hour)여야 함")

    if not (0 <= req.start_dt <= 23):
        raise HTTPException(status_code=400, detail="start_dt는 0~23 범위여야 함")

    # =========================
    # 1) end_dt 입력 처리(자동 보정)
    #    - end_dt가 누락/비정상 값이면 자동으로 start+2
    #    - end_dt가 start+1이면 end를 +1
    # =========================
    end_in = getattr(req, "end_dt", None)

    # "시작만 선택"을 end_dt=None 또는 end_dt=0 같은 값으로 받는 경우까지 커버
    if end_in is None or end_in == 0:
        end_hour = req.start_dt + 2
    else:
        if not isinstance(end_in, int):
            raise HTTPException(status_code=400, detail="end_dt는 정수(hour)여야 함")
        end_hour = end_in

        # 끝이 시작+1이면 +1 보정(최소 2시간 강제)
        if end_hour == req.start_dt + 1:
            end_hour = end_hour + 1

    # end_hour 상한/하한 정리
    if end_hour > 24:
        end_hour = 24

    # start가 23인데 최소 2시간을 만들 수 없음(25시 필요) => 정책상 막는 게 깔끔
    # (원하면 end_hour를 24로 강제하는 방식으로 바꿀 수 있음)
    if req.start_dt >= 23:
        raise HTTPException(status_code=400, detail="23시는 최소 예약시간(2시간)을 만족할 수 없음")

    if end_hour <= req.start_dt:
        raise HTTPException(status_code=400, detail="end_dt는 start_dt보다 커야 함")

    if not (1 <= end_hour <= 24):
        raise HTTPException(status_code=400, detail="end_dt는 1~24 범위여야 함")

    # =========================
    # 2) stat_id 존재성 검증(선택)
    # =========================
    station_exists_query = text("""
        SELECT 1
        FROM ev_station
        WHERE stat_id = :stat_id
        LIMIT 1
    """)
    station_exists = db.execute(station_exists_query, {"stat_id": req.stat_id}).first()
    if not station_exists:
        raise HTTPException(status_code=404, detail="존재하지 않는 충전소(stat_id)임")

    # =========================
    # 3) 시간 변환: 오늘 날짜 + hour
    # =========================
    today = datetime.now().date()
    start_dt_obj = datetime.combine(today, time(hour=req.start_dt))

    if end_hour == 24:
        end_dt_obj = datetime.combine(today, time(hour=23, minute=59, second=59))
    else:
        end_dt_obj = datetime.combine(today, time(hour=end_hour))

    # =========================
    # 4) 예약 겹침 체크
    # =========================
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
        raise HTTPException(status_code=400, detail="이미 해당 시간에 예약이 존재합니다.")

    # =========================
    # 5) INSERT (DB에는 READY로 저장)
    # =========================
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

    return {"reserv_id": new_reserv_id, "status": "READY"}


@router.get("/stations/{stat_id}/reservations", response_model=ReservationListResponse)
def list_reservations(stat_id: str, db: Session = Depends(get_pg)):
    """
    예약 목록 조회
    """

    query = text("""
        SELECT reserv_id, user_id, start_dt, end_dt, status
        FROM ev_reservation
        WHERE stat_id = :stat_id
        ORDER BY start_dt ASC
    """)

    rows = db.execute(query, {"stat_id": stat_id}).fetchall()

    reservations = []
    for r in rows:
        # READY는 조회 응답에서만 USED로 표시
        status_out = "USED" if r.status == "READY" else r.status

        reservations.append({
            "reserv_id": str(r.reserv_id),
            "user_id": r.user_id,
            "start_dt": r.start_dt,
            "end_dt": r.end_dt,
            "status": status_out,
        })

    return {"stat_id": stat_id, "reservations": reservations}
