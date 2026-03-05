from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, time

# ULID: 라이브러리 버전/패키지명이 혼동되는 경우가 많아서 안전하게 처리
# - python-ulid: import ulid; ulid.new().str  (버전에 따라 new가 없을 수 있음)
# - ulid-py: from ulid import ULID; str(ULID())
#
# 아래 코드는 둘 다 대응하는 "안전 생성" 함수로 처리한다.
def generate_ulid_26() -> str:
    # 1) python-ulid 스타일
    try:
        import ulid  # type: ignore
        if hasattr(ulid, "new"):
            s = ulid.new().str
            if isinstance(s, str) and len(s) == 26:
                return s
    except Exception:
        pass

    # 2) ulid-py 스타일
    try:
        from ulid import ULID  # type: ignore
        s = str(ULID())
        # ulid-py는 보통 26자 Crockford Base32
        if isinstance(s, str) and len(s) == 26:
            return s
    except Exception:
        pass

    # 최후의 수단: 예외
    raise RuntimeError("ULID(26자) 생성 실패: ulid 패키지 버전/의존성을 확인해야 함")


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
    예약 생성
    - start_dt/end_dt: '정수 hour' 입력 (0~24)
    - end_dt=24는 23:59:59로 저장(하루 끝 처리)
    - 충돌 예약이 있으면 400 + 충돌 정보 반환
    """

    # =========================
    # 0) 입력 검증
    # =========================
    if not isinstance(req.start_dt, int) or not isinstance(req.end_dt, int):
        raise HTTPException(status_code=400, detail="start_dt/end_dt는 정수(hour)여야 함")

    if not (0 <= req.start_dt <= 23):
        raise HTTPException(status_code=400, detail="start_dt는 0~23 범위여야 함")

    if not (1 <= req.end_dt <= 24):
        raise HTTPException(status_code=400, detail="end_dt는 1~24 범위여야 함")

    if req.start_dt >= req.end_dt:
        raise HTTPException(status_code=400, detail="start_dt는 end_dt보다 작아야 함")

    if not req.user_id or not isinstance(req.user_id, str) or len(req.user_id.strip()) == 0:
        raise HTTPException(status_code=400, detail="user_id가 비어있음")

    if len(req.user_id) > 50:
        raise HTTPException(status_code=400, detail="user_id가 너무 김(최대 50)")

    if not req.stat_id or not isinstance(req.stat_id, str) or len(req.stat_id.strip()) == 0:
        raise HTTPException(status_code=400, detail="stat_id가 비어있음")

    # =========================
    # 1) stat_id 존재성 검증
    # =========================
    station_exists_query = text("""
        SELECT 1
        FROM ev_station
        WHERE stat_id = :stat_id
        LIMIT 1
    """)
    station_exists = db.execute(station_exists_query, {"stat_id": req.stat_id}).first()
    if not station_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지 않는 충전소(stat_id)임"
        )

    # =========================
    # 2) 시간 변환: 오늘 날짜 + hour
    # =========================
    today = datetime.now().date()
    start_dt_obj = datetime.combine(today, time(hour=req.start_dt))

    # 24시 예외 처리
    if req.end_dt == 24:
        end_dt_obj = datetime.combine(today, time(hour=23, minute=59, second=59))
    else:
        end_dt_obj = datetime.combine(today, time(hour=req.end_dt))

    # =========================
    # 3) 중복(겹침) 체크: 충돌 예약 1건 가져오기
    # =========================
    conflict_query = text("""
        SELECT reserv_id, user_id, start_dt, end_dt, status
        FROM ev_reservation
        WHERE stat_id = :stat_id
          AND start_dt < :end_dt
          AND end_dt > :start_dt
        ORDER BY start_dt ASC
        LIMIT 1
    """)
    conflict = db.execute(conflict_query, {
        "stat_id": req.stat_id,
        "start_dt": start_dt_obj,
        "end_dt": end_dt_obj
    }).mappings().first()

    if conflict:
        
        # 개발 단계에서는 충돌 예약 정보를 같이 내려주는 게 디버깅에 압도적으로 좋다.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "msg": "이미 해당 시간에 예약이 존재합니다.",
                "request": {
                    "stat_id": req.stat_id,
                    "start_dt": str(start_dt_obj),
                    "end_dt": str(end_dt_obj),
                    "user_id": req.user_id
                },
                "conflict": {
                    "reserv_id": str(conflict["reserv_id"]),
                    "user_id": conflict["user_id"],
                    "start_dt": str(conflict["start_dt"]),
                    "end_dt": str(conflict["end_dt"]),
                    "status": conflict["status"]
                }
            }
        )

    # =========================
    # 4) INSERT
    # =========================
    new_reserv_id = generate_ulid_26()

    insert_query = text("""
        INSERT INTO ev_reservation (reserv_id, user_id, status, stat_id, start_dt, end_dt)
        VALUES (:reserv_id, :user_id, 'USED', :stat_id, :start_dt, :end_dt)
    """)

    try:
        db.execute(insert_query, {
            "reserv_id": new_reserv_id,
            "user_id": req.user_id,
            "stat_id": req.stat_id,
            "start_dt": start_dt_obj,
            "end_dt": end_dt_obj
        })
        db.commit()
    except Exception as e:
        db.rollback()
        # DB 레벨 에러(제약조건 등)는 500 대신 400으로 내려도 되지만,
        # 지금은 디버깅 위해 메시지 노출(운영가면 숨김 처리)해도 된다.
        raise HTTPException(
            status_code=500,
            detail=f"예약 저장 실패: {type(e).__name__}: {str(e)}"
        )

    # =========================
    # 5) 응답
    # =========================
    return {
        "user_id": req.user_id,
        "reserv_id": new_reserv_id,
        "status": "USED" #이 부분 고쳐야됨.
    }


@router.get("/stations/{stat_id}/reservations", response_model=ReservationListResponse)
def list_reservations(stat_id: str, db: Session = Depends(get_pg)):
    """
    특정 충전소(stat_id)의 예약 목록 조회
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
        reservations.append({
            "reserv_id": str(r.reserv_id),
            "user_id": r.user_id,
            "start_dt": r.start_dt,
            "end_dt": r.end_dt,
            "status": r.status,
        })

    return {"stat_id": stat_id, "reservations": reservations}
