from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, time
import ulid  # pip install python-ulid 필요
import models, schemas, db

router = APIRouter()

@router.post("/reservations", response_model=schemas.ReservationOut)
async def create_reservation(req: schemas.ReservationCreate, session: Session = Depends(db.get_db)):
    # 1. [시간 변환] 정수(14)를 오늘 날짜의 TIMESTAMP로 변환
    today = datetime.now().date()
    
    # start_dt 생성 (예: 2026-02-24 14:00:00)
    start_dt_obj = datetime.combine(today, time(hour=req.start_dt))
    
    # end_dt 생성 (24시 예외 처리 포함)
    if req.end_dt == 24:
        end_dt_obj = datetime.combine(today, time(hour=23, minute=59, second=59))
    else:
        end_dt_obj = datetime.combine(today, time(hour=req.end_dt))

    # 2. [중복 체크] DB 팀의 테이블(ev_resevation) 기준
    conflict = session.query(models.Reservation).filter(
        models.Reservation.stat_id == req.stat_id,
        models.Reservation.start_dt < end_dt_obj,
        models.Reservation.end_dt > start_dt_obj
    ).first()

    if conflict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="이미 해당 시간에 예약이 존재합니다."
        )

    # 3. [데이터 저장] 백엔드에서 생성할 값(ULID, status) 포함
    new_res = models.Reservation(
        reserv_id=ulid.new().str,      # 백엔드가 직접 생성한 ULID
        user_id=req.user_id,           # 프론트가 준 값
        status="READY",                # 백엔드가 고정한 초기 상태
        stat_id=req.stat_id,           # 프론트가 준 값
        start_dt=start_dt_obj,         # 조립된 TIMESTAMP
        end_dt=end_dt_obj              # 조립된 TIMESTAMP
    )
    
    session.add(new_res)
    session.commit()
    session.refresh(new_res)

    # 4. [CQRS 동기화] 선우의 조회를 위해 MongoDB 업데이트
    # (이미지에는 없지만 프로젝트 흐름상 필요)
    await db.mongo_db["reservation_view"].insert_one({
        "reserv_id": new_res.reserv_id,
        "stat_id": req.stat_id,
        "start_dt": start_dt_obj.isoformat(),
        "end_dt": end_dt_obj.isoformat(),
        "user_id": req.user_id
    })

    # 5. [응답] 최종 결과 반환
    return {
        "reserv_id": new_res.reserv_id,
        "status": new_res.status,
        "message": "예약이 완료되었습니다."
    }
