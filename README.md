# ⚡ WattUp BE (Electric Vehicle Charging Station Management System)

WattUp은 전기차 충전소 검색 및 예약 관리를 위한 고도화된 백엔드 시스템입니다. 단순한 CRUD를 넘어 **Debezium(CDC)**과 **Kafka**를 활용한 데이터 파이프라인 아키텍처를 갖추고 있으며, **PostgreSQL(PostGIS)**을 통한 위치 기반 데이터 처리를 지원합니다.

---

## 🏗 System Architecture

본 프로젝트는 마이크로서비스 및 이벤트 기반 아키텍처를 지향하며 다음과 같은 구조로 설계되었습니다.

1.  **Gateway (Nginx)**: 단일 진입점(Port 3000)을 통해 프론트엔드와 백엔드 API 라우팅을 담당합니다.
2.  **FastAPI Backend**: 비동기 처리를 지원하는 메인 API 서버입니다.
3.  **Database Stack**:
    -   **PostgreSQL (PostGIS)**: 충전소 위치 정보 및 예약 트랜잭션 데이터 관리.
    -   **MongoDB**: 대용량 로그 또는 비정형 데이터 저장 (확장성 고려).
4.  **Data Pipeline**:
    -   **Debezium**: PostgreSQL의 변경 사항을 실시간으로 감지(CDC).
    -   **Kafka Cluster (KRaft)**: 3-Node 클러스터 구성을 통해 이벤트 메시지 스트리밍 및 내결함성 확보.
    -   **Kafka UI**: 실시간 토픽 및 메시지 모니터링.

---

## 🛠 Tech Stack

-   **Framework**: FastAPI (Python 3.10+)
-   **ORM/DB**: SQLAlchemy, PostgreSQL (PostGIS), MongoDB (PyMongo)
-   **Messaging**: Apache Kafka (KRaft mode), Debezium (Connect)
-   **Validation**: Pydantic v2
-   **Infrastructure**: Docker, Docker Compose, Nginx
-   **Unique ID**: ULID (Universally Unique Lexicographically Sortable Identifier)

---

## 🚀 Key Features

### 1. 충전소 검색 (Station Map)
-   서울시 행정구역(‘~구’) 기반의 충전소 위치 정보 조회.
-   PostGIS 기반의 위경도 데이터 처리.

### 2. 예약 관리 (Reservation System)
-   **시간 기반 예약**: 정수형 시간(0~24) 입력을 통한 직관적인 예약 프로세스.
-   **충돌 감지 로직**: 동일 충전소 내 시간 중복 예약 원천 차단.
-   **상태 관리**: READY, COMPLETED 등 예약 생명주기 관리.

### 3. 실시간 데이터 동기화 (CDC)
-   DB 레벨의 변경 사항을 Kafka로 스트리밍하여 실시간 데이터 일관성 유지.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | 서버 상태 체크 |
| `GET` | `/api/wattup/map/{regionName}` | 특정 구 단위 충전소 목록 조회 (예: 강남구) |
| `POST` | `/api/wattup/reservations` | 충전소 예약 생성 (중복 체크 포함) |
| `GET` | `/api/wattup/stations/{stat_id}/reservations` | 특정 충전소의 전체 예약 현황 조회 |

---

## ⚙️ Installation & Setup

### Prerequisites
-   Docker & Docker Compose
-   `.env` 파일 설정 (PostgreSQL, MongoDB 계정 정보 등)

### Execution
```bash
# 전체 서비스 빌드 및 실행
docker-compose up -d --build

# 서비스 상태 확인
docker-compose ps
```

### Access Ports
-   **Frontend & API Gateway**: [http://localhost:3000](http://localhost:3000)
-   **Backend API Docs (Swagger)**: [http://localhost:8001/docs](http://localhost:8001/docs)
-   **Kafka UI**: [http://localhost:8081](http://localhost:8081)
-   **Debezium Connect**: [http://localhost:8083](http://localhost:8083)

---

## 📂 Project Structure
```text
.
├── backend/          # FastAPI 서버 코드
├── debezium/         # CDC 커넥터 설정
├── importer/         # 초기 데이터 적재 스크립트
├── nginx.conf        # Gateway 설정
├── docker-compose.yml # 컨테이너 오케스트레이션
└── schema.sql        # 데이터베이스 스키마
```
