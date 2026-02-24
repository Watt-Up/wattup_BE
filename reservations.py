from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, time
import ulid  # pip install python-ulid
from db_postgres import get_pg  # 파일명에 맞춰 수정
import schemas

router = APIRouter()

@router.post("/reservations", response_model=schemas.ReservationCreateResponse)
async def create_reservation(req: schemas.ReservationCreateRequest, db: Session = Depends(get_pg)):
    # 1. [시간 변환] 정수(14, 16)를 오늘 날짜의 TIMESTAMP로 변환
    today = datetime.now().date()
    
    # schemas.py의 datetime 필드를 int로 가정하고 로직 처리
    # 만약 schemas.py를 수정 전이라면 req.start_dt.hour 등으로 접근해야 함
    start_dt_obj = datetime.combine(today, time(hour=int(req.start_dt.hour if hasattr(req.start_dt, 'hour') else req.start_dt)))
    end_dt_obj = datetime.combine(today, time(hour=int(req.end_dt.hour if hasattr(req.end_dt, 'hour') else req.end_dt)))

    # 2. [중복 체크] 직접 SQL 실행 (ERD의 ev_resevation 테이블 기준)
    check_query = text("""
        SELECT 1 FROM ev_resevation 
        WHERE stat_id = :stat_id 
        AND start_dt < :end_dt 
        AND end_dt > :start_dt
    """)
    
    conflict = db.execute(check_query, {
        "stat_id": req.stat_id,
        "start_dt": start_dt_obj,
        "end_dt": end_dt_obj
    }).first()

    if conflict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="이미 해당 시간에 예약이 존재합니다."
        )

    # 3. [데이터 저장] 직접 INSERT (ULID 생성 및 status 고정)
    new_reserv_id = ulid.new().str
    insert_query = text("""
        INSERT INTO ev_resevation (reserv_id, user_id, status, stat_id, start_dt, end_dt)
        VALUES (:reserv_id, :user_id, 'READY', :stat_id, :start_dt, :end_dt)
    """)
    
    db.execute(insert_query, {
        "reserv_id": new_reserv_id,
        "user_id": req.user_id,
        "stat_id": req.stat_id,
        "start_dt": start_dt_obj,
        "end_dt": end_dt_obj
    })
    db.commit()

    # 4. [응답] 최종 결과 반환
    return {
        "reserv_id": new_reserv_id,
        "status": "READY"
    }
