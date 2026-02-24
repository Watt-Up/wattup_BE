from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from db_postgres import get_pg
from schemas import StationResponse, ReservationListResponse

router = APIRouter(tags=["stations"])


@router.get("/map/{regionName}", response_model=StationResponse)
def get_stations(regionName: str, db: Session = Depends(get_pg)):

    query = text("""
        SELECT stat_id, stat_nm, addr, lat, lng
        FROM ev_station
        WHERE addr LIKE :region
    """)

    result = db.execute(query, {"region": f"%{regionName}%"}).fetchall()

    stations = [
        {
            "stat_id": row.stat_id,
            "stat_nm": row.stat_nm,
            "addr": row.addr,
            "lat": float(row.lat) if row.lat else None,
            "lng": float(row.lng) if row.lng else None,
        }
        for row in result
    ]

    return {"regionName": regionName, "stations": stations}


@router.get("/stations/{stat_id}/reservations", response_model=ReservationListResponse)
def get_reservations(stat_id: str, db: Session = Depends(get_pg)):

    query = text("""
        SELECT reserv_id, user_id, start_dt, end_dt, status
        FROM ev_reservation
        WHERE stat_id = :stat_id
    """)

    result = db.execute(query, {"stat_id": stat_id}).fetchall()

    reservations = [dict(row._mapping) for row in result]

    return {"stat_id": stat_id, "reservations": reservations}