# 2-4. Streamlit 카카오맵 구조화 여행 추천 — Backend Plan

> 기준 문서: `C:\mini_agent\mini_agent_02_structured_output\MASTER_PLAN.md`  
> 실제 구현 대상: `C:\mini_agent\mini_agent_02_structured_output`  
> 문서 목적: Backend A/B 병렬 개발과 Frontend 병합 시 충돌을 최소화하는 구현 기준 확정  
> 현재 상태: 검토용 계획서이며 프로젝트 코드는 변경하지 않음

---

## 1. 목표와 범위

백엔드는 자연어 여행 질문과 Provider를 받아 여행 기간, 랜드마크, 음식 추천을 구조화된 JSON으로 반환한다.

```http
POST /api/structured/map-travel
Content-Type: application/json
```

백엔드가 담당하는 범위:

- 요청 `provider`, `message` 검증
- `당일치기`, `N박 M일` 여행 기간 해석
- Mock 및 실제 Provider 구조화 출력 생성
- Pydantic을 이용한 최종 응답 재검증
- 기간, 배열 크기, 좌표, 가격, 추가 필드 검증
- 검증된 데이터만 Frontend에 반환
- `422`, `502` 오류 구분
- OpenAPI 및 자동 테스트 제공

백엔드에서 하지 않는 작업:

- Streamlit 화면과 카카오맵 HTML 생성
- 카카오 JavaScript 키 관리
- 카카오 로컬 API를 이용한 좌표 검증
- 예약, 결제, 길찾기, 데이터 영구 저장
- 기존 2-1~2-3 API 변경 또는 삭제

---

## 2. 구현 기준 결정

### 2.1 실제 저장소 구조 반영

현재 저장소에는 `backend/app/schemas.py` 파일이 이미 존재한다. 따라서 `backend/app/schemas/map_travel.py` 디렉터리를 추가할 수 없다. 같은 위치에 `schemas.py` 파일과 `schemas/` 디렉터리를 함께 둘 수 없기 때문이다.

Master Plan의 API 및 데이터 계약은 유지하면서 신규 기능을 아래 패키지로 격리한다.

```text
backend/app/map_travel/
```

이 구조는 기존 `schemas.py`, `providers.py`, `agent_router.py`를 대규모로 분해하지 않으면서 신규 기능을 독립적으로 관리하기 위한 결정이다.

### 2.2 고정 결정

- 전용 API: `POST /api/structured/map-travel`
- 전용 Schema 이름: `map_travel`
- Provider: `mock`, `gemini`, `openai`, `ollama`
- Provider 생략 시 `settings.llm_provider` 사용
- `message`: trim 이후 1~4,000자
- 기간 미지정 시 `nights=0`, `days=1`
- 기간 기본값 적용 시 `cautions`에 안내 추가
- `days == nights + 1` 필수
- `landmarks`: 1~10개
- `foods`: 0~10개
- 음식 가격: `estimated_price_krw` 단일 정수
- 좌표는 교육용 Provider 생성값 사용
- 모든 신규 모델에 `extra="forbid"` 적용
- 기존 API와 응답 계약 유지

---

## 3. Backend–Frontend 고정 API 계약

### 3.1 요청

```json
{
  "provider": "mock",
  "message": "부산에 2박 3일 여행을 가고자 해. 관광지와 음식을 추천해 주세요."
}
```

`provider`는 생략하거나 `null`일 수 있다.

### 3.2 성공 응답

```json
{
  "provider": "mock",
  "model": "deterministic-map-travel-mock",
  "content": {
    "destination": "부산",
    "nights": 2,
    "days": 3,
    "summary": "해운대와 광안리를 중심으로 둘러보는 2박 3일 여행입니다.",
    "landmarks": [
      {
        "name": "해운대해수욕장",
        "description": "해변 산책과 바다 풍경을 즐길 수 있는 장소입니다.",
        "latitude": 35.1587,
        "longitude": 129.1604,
        "category": "beach"
      }
    ],
    "foods": [
      {
        "name": "돼지국밥",
        "estimated_price_krw": 10000,
        "description": "부산을 대표하는 따뜻한 국밥입니다.",
        "latitude": 35.1631,
        "longitude": 129.1635
      }
    ],
    "cautions": [
      "가격과 영업시간은 방문 전에 확인하세요."
    ]
  },
  "latency_ms": 0
}
```

### 3.3 오류

| HTTP | 조건 | Frontend 처리 |
|---|---|---|
| `422` | 빈 질문, 길이 초과, Provider 값 오류, 구조화 결과 Schema 위반 | 응답 `detail` 표시 |
| `502` | OpenAI/Gemini/Ollama 연결 또는 호출 실패 | 응답 `detail` 표시 |

응답에는 Provider 키, 토큰, 내부 전체 예외, System Prompt를 포함하지 않는다.

### 3.4 변경 금지 계약

Frontend 구현이 시작된 뒤 다음 항목은 단독으로 변경하지 않는다.

- API 경로와 HTTP 메서드
- 요청의 `provider`, `message`
- 응답의 `provider`, `model`, `content`, `latency_ms`
- `landmarks`, `foods`의 복수형 이름
- `latitude`, `longitude`의 타입과 의미
- `estimated_price_krw`의 원화 정수 표현
- `nights`, `days`의 관계

변경이 필요하면 Backend A, Backend B, Frontend 담당자가 먼저 계약 변경에 합의한다.

---

## 4. 예정 파일 구조

```text
mini_agent_02_structured_output/
└─ backend/
   ├─ app/
   │  ├─ main.py                                  # Backend B만 수정
   │  ├─ providers.py                             # Backend A만 수정
   │  ├─ schemas.py                               # Backend A만 최소 수정
   │  ├─ map_travel/                              # 신규 기능 패키지
   │  │  ├─ __init__.py                           # Backend A 생성, 이후 수정 금지
   │  │  ├─ schemas.py                            # Backend A
   │  │  ├─ prompt.py                             # Backend A
   │  │  ├─ mock_data.py                          # Backend A
   │  │  ├─ provider_service.py                   # Backend A
   │  │  └─ service.py                            # Backend B
   │  └─ routers/
   │     ├─ agent_router.py                       # 유지
   │     └─ map_travel_router.py                  # Backend B
   └─ tests/
      ├─ test_map_travel_schema.py                # Backend A
      ├─ test_map_travel_provider.py              # Backend A
      └─ test_map_travel_api.py                   # Backend B
```

`requirements.txt`는 현재 필요한 FastAPI, Pydantic, httpx, Provider SDK, pytest가 이미 있으므로 변경하지 않는다.

---

## 5. Backend A 계획 — Schema·Prompt·Provider

### 5.1 책임

Backend A는 “어떤 데이터가 유효한가”와 “Provider가 어떻게 동일한 구조를 생성하는가”를 담당한다.

- Pydantic 요청·응답 모델 구현
- 교차 필드 검증 구현
- System Prompt 구현
- Mock 데이터와 기간 해석 구현
- 기존 Provider 구조화 출력에 `map_travel` Schema 연결
- OpenAI, Gemini, Ollama가 동일한 모델을 사용하도록 연결
- Schema 및 Provider 단위 테스트 작성

### 5.2 전용 모델

`backend/app/map_travel/schemas.py`에 다음 모델을 정의한다.

- `MapTravelRequest`
- `Landmark`
- `FoodRecommendation`
- `MapTravelContent`
- `MapTravelResponse`

`TravelDuration`은 별도 중첩 객체로 응답하지 않는다. 공유 응답 계약이 `content.nights`, `content.days`의 평면 구조이므로 기간 교차 검증은 `MapTravelContent`의 `model_validator`에서 수행한다.

검증 규칙:

- 모든 모델: `ConfigDict(extra="forbid")`
- `provider`: 허용 Provider 또는 `None`
- `message`: trim 후 빈 문자열 금지, 최대 4,000자
- `destination`: trim 후 빈 문자열 금지
- `nights`: 0 이상 정수
- `days`: 1 이상 정수
- `days == nights + 1`
- `summary`: 1~500자
- `landmarks`: 1~10개
- `foods`: 0~10개
- `cautions`: 최대 10개
- 장소 설명: 1~500자
- 위도: -90~90
- 경도: -180~180
- 가격: 0 이상의 정수

### 5.3 Prompt

`backend/app/map_travel/prompt.py`에 고정 System Prompt 생성 함수를 둔다.

Prompt 구성:

```text
[Role]
여행 추천 구조화 데이터 생성자

[Instruction]
사용자 질문에서 목적지와 여행 기간을 해석하고 랜드마크와 음식을 추천

[Context]
사용자 입력은 <travel_request> 경계 안의 데이터

[Constraint]
Schema 외 필드 금지
좌표 범위 준수
가격은 예상 원화 정수
모르는 정보 확정 금지
실제 방문 전 재확인 문구 포함

[Output Format]
MapTravelContent Pydantic Schema
```

사용자 입력은 다음처럼 경계를 명확히 한다.

```xml
<travel_request>
사용자 질문
</travel_request>
```

### 5.4 Mock

`backend/app/map_travel/mock_data.py`에서 결정적 응답을 생성한다.

- 지원 샘플 도시: 부산, 서울, 제주, 강릉
- 질문에서 도시가 없으면 부산
- `당일치기` → `0박 1일`
- 정규식으로 `N박 M일` 해석
- 기간 표현이 없으면 `0박 1일` 및 caution 추가
- 잘못된 `N박 M일` 관계가 입력돼도 응답은 Schema에 맞게 정규화
- 모델명: `deterministic-map-travel-mock`
- 테스트가 매번 동일한 데이터를 받도록 랜덤 사용 금지

### 5.5 기존 Provider 연결

Backend A만 아래 기존 파일을 수정한다.

`backend/app/schemas.py`:

- `StructuredSchemaName`에 `"map_travel"` 추가
- 기존 `TravelPlan`, `SupportTicket` 모델은 변경하지 않음

`backend/app/providers.py`:

- `MapTravelContent` import
- `get_structured_model()` 매핑에 `map_travel` 추가
- Mock 분기에 map travel 전용 결과 추가
- 기존 `travel_plan`, `support_ticket` 분기 유지
- 실제 Provider는 기존 structured output 흐름 재사용

`backend/app/map_travel/provider_service.py`는 Router가 전역 Provider 구현 세부사항에 직접 의존하지 않도록 다음 단일 진입점을 제공한다.

```python
generate_map_travel(provider: str, message: str) -> ProviderResult
```

이 함수는 Prompt 구성, `generate_structured(..., "map_travel")` 호출, `MapTravelContent` 최종 재검증을 담당한다.

또한 B가 오류 유형을 문자열로 추측하지 않도록 전용 예외를 제공한다.

- `MapTravelOutputValidationError`: Provider 응답이 Schema를 위반한 경우
- `MapTravelProviderError`: Provider 인증, 연결, 시간 초과 또는 호출 실패

### 5.6 Backend A 테스트

`test_map_travel_schema.py`:

- 정상 당일치기
- 정상 2박 3일
- `days != nights + 1` 거부
- landmark 0개 및 11개 거부
- food 11개 거부
- 잘못된 위도·경도 거부
- 음수 가격 거부
- 추가 필드 거부
- 공백 message 거부
- 4,000자 초과 message 거부

`test_map_travel_provider.py`:

- Mock 부산 데이터
- 당일치기 해석
- 2박 3일 해석
- 기간 미지정 기본값과 caution
- Provider 결과 최종 Schema 검증
- 기존 `travel_plan`, `support_ticket` Mock 회귀 확인

### 5.7 Backend A 완료 조건

- `map_travel` Schema가 모든 Provider 구조화 흐름에서 선택 가능
- Mock이 API 키 없이 결정적 콘텐츠 생성
- 기간과 좌표, 가격, 배열 검증 통과
- 기존 두 Structured Schema의 테스트가 계속 통과
- Backend B가 사용할 공개 함수와 모델 import 경로가 확정

---

## 6. Backend B 계획 — Service·Router·API

### 6.1 책임

Backend B는 “HTTP 요청이 어떻게 Provider 계층으로 전달되고 응답되는가”를 담당한다.

- Application Service 구현
- 전용 FastAPI Router 구현
- Router 등록
- 기본 Provider 선택
- 예외를 `422`, `502`로 변환
- OpenAPI 노출 확인
- API 및 회귀 테스트 작성

### 6.2 Application Service

`backend/app/map_travel/service.py`에 다음 함수를 둔다.

```python
create_map_travel(payload: MapTravelRequest) -> MapTravelResponse
```

처리 순서:

1. `payload.provider`가 없으면 `settings.llm_provider` 선택
2. Backend A의 `generate_map_travel()` 호출
3. Provider 결과에서 `provider`, `model`, `content`, `latency_ms` 추출
4. `MapTravelResponse.model_validate()`로 최종 검증
5. 성공 응답 반환

Service는 FastAPI `HTTPException`을 직접 생성하지 않는다. HTTP 상태 변환은 Router에서만 수행한다.

### 6.3 Router

`backend/app/routers/map_travel_router.py`:

```python
map_travel_router = APIRouter()

@map_travel_router.post(
    "/api/structured/map-travel",
    response_model=MapTravelResponse,
)
```

오류 변환:

- Request Pydantic 오류 → FastAPI 기본 `422`
- Provider가 반환한 구조의 ValidationError → `422`
- Provider 연결, 인증, 시간 초과 및 호출 실패 → `502`
- 내부 전체 예외 대신 안전한 한국어 `detail` 반환

기존 `agent_router.py`에는 엔드포인트를 추가하지 않는다. 별도 Router를 사용해 기존 기능과의 충돌을 피한다.

### 6.4 애플리케이션 등록

Backend B만 `backend/app/main.py`를 수정한다.

```python
from app.routers.map_travel_router import map_travel_router

app.include_router(map_travel_router)
```

기존 `agent_router`, `media_router` 등록 순서와 내용은 유지한다.

OpenAPI 태그가 필요하면 Router에 문자열 태그를 직접 지정하고, 현재 변경 중인 `openapi.py`를 불필요하게 함께 수정하지 않는다. 태그 상수 통합은 최종 병합 담당자가 별도 커밋으로 처리할 수 있다.

### 6.5 Backend B 테스트

`backend/tests/test_map_travel_api.py`:

- `POST /api/structured/map-travel` Mock `200`
- 응답이 `MapTravelResponse`와 일치
- provider 생략 시 기본 Provider 사용
- 빈 문자열·공백 문자열 `422`
- 4,000자 초과 `422`
- 잘못된 Provider `422`
- 구조화 결과 검증 실패 `422`
- 외부 Provider 실패 `502`
- 오류에 API 키나 내부 예외 전체가 노출되지 않음
- OpenAPI에 경로와 응답 Schema 노출
- `/health`, `/api/structured/generate`, `/api/structured/compare` 회귀 확인

외부 Provider를 실제로 호출하지 않고 monkeypatch/fake를 사용한다. 실제 Provider 품질 확인은 별도의 수동 통합 테스트로 분리한다.

### 6.6 Backend B 완료 조건

- 전용 API가 Mock으로 `200` 반환
- Request와 Response가 OpenAPI에 정확히 표시
- `422`, `502`가 계획대로 구분
- 기존 Router와 API가 손상되지 않음
- Frontend가 API 계약만으로 구현 가능

---

## 7. 파일 소유권 — 충돌 방지 핵심 규칙

| 파일 | Backend A | Backend B | Frontend | 규칙 |
|---|---:|---:|---:|---|
| `backend/app/schemas.py` | 수정 | 금지 | 금지 | Schema 이름 등록만 최소 수정 |
| `backend/app/providers.py` | 수정 | 금지 | 금지 | A 전용 |
| `backend/app/map_travel/__init__.py` | 생성 | 금지 | 금지 | 비워두고 재수정하지 않음 |
| `backend/app/map_travel/schemas.py` | 생성·수정 | 읽기 | 금지 | A 전용 |
| `backend/app/map_travel/prompt.py` | 생성·수정 | 읽기 | 금지 | A 전용 |
| `backend/app/map_travel/mock_data.py` | 생성·수정 | 읽기 | 금지 | A 전용 |
| `backend/app/map_travel/provider_service.py` | 생성·수정 | 읽기 | 금지 | A 전용 |
| `backend/app/map_travel/service.py` | 읽기 | 생성·수정 | 금지 | B 전용 |
| `backend/app/routers/map_travel_router.py` | 금지 | 생성·수정 | 금지 | B 전용 |
| `backend/app/main.py` | 금지 | 최소 수정 | 금지 | B 전용 |
| `backend/tests/test_map_travel_schema.py` | 생성·수정 | 금지 | 금지 | A 전용 |
| `backend/tests/test_map_travel_provider.py` | 생성·수정 | 금지 | 금지 | A 전용 |
| `backend/tests/test_map_travel_api.py` | 금지 | 생성·수정 | 금지 | B 전용 |
| `frontend/**` | 금지 | 금지 | 수정 | Frontend 전용 |
| `.env.example`, `README.md` | 금지 | 금지 | 통합 담당 | 마지막 문서화 커밋에서만 변경 |

추가 규칙:

- 기존 `backend/app/routers/agent_router.py`를 수정하지 않는다.
- 기존 `backend/tests/test_api.py`를 수정하지 않는다.
- A와 B는 상대방 소유 파일의 포맷팅, import 정리, 주석 수정도 하지 않는다.
- 공통 파일 수정이 필요하면 해당 파일 소유자에게 요청한다.
- 기능과 무관한 자동 포맷팅을 전체 디렉터리에 실행하지 않는다.

---

## 8. A/B 연결 인터페이스

Backend B는 A의 내부 구현이 아니라 아래 import만 사용한다.

```python
from app.map_travel.provider_service import generate_map_travel
from app.map_travel.schemas import MapTravelRequest, MapTravelResponse
```

A가 B에게 보장해야 하는 것:

- 위 import 경로 고정
- `generate_map_travel(provider, message)` 시그니처 고정
- 성공 시 `ProviderResult` 반환
- 콘텐츠는 `MapTravelContent` 검증을 통과
- 구조 위반은 `MapTravelOutputValidationError`로 전달
- Provider 실패는 `MapTravelProviderError`로 전달

B가 A에게 보장해야 하는 것:

- Provider 호출 전에 요청 모델 검증 완료
- Provider 생략 시 기본 Provider 결정
- A의 반환 콘텐츠를 임의로 수정하지 않음
- HTTP 변환을 Router에서 처리

---

## 9. Git 병렬 작업 및 병합 순서

### 9.1 시작 전 필수 확인

현재 작업 트리에는 이미 `main.py`, `providers.py`, `agent_router.py`, `test_api.py` 등을 포함한 변경이 존재한다. 이 변경의 소유자와 목적을 확인하지 않고 새 브랜치를 만들거나 덮어쓰면 안 된다.

시작 절차:

1. 현재 변경을 담당자가 커밋하거나 안전하게 보관한다.
2. 팀이 동일한 기준 커밋 SHA를 확정한다.
3. A와 B가 그 기준 커밋에서 각각 브랜치를 만든다.
4. 계획서의 파일 소유권을 이슈 또는 PR 설명에 붙인다.

권장 브랜치:

```text
feature/map-travel-backend-a
feature/map-travel-backend-b
feature/map-travel-backend-integration
feature/map-travel-frontend
```

### 9.2 병렬 개발

- A는 Schema·Prompt·Provider와 자신의 테스트만 커밋한다.
- B는 Service·Router·main 등록과 자신의 API 테스트만 커밋한다.
- B는 A가 제공할 import 경로를 기준으로 작업한다.
- A의 공개 인터페이스가 바뀌면 코드보다 계약 문서를 먼저 갱신한다.

### 9.3 병합 순서

1. Backend A PR 검토 및 테스트
2. A를 `feature/map-travel-backend-integration`에 먼저 병합
3. Backend B 브랜치를 integration 최신 상태에 맞춰 rebase 또는 merge
4. B에서 import와 전체 API 테스트 확인
5. Backend B 병합
6. Backend 전체 테스트 실행
7. API 계약 동결
8. Frontend 브랜치를 최신 integration 기준으로 갱신
9. Frontend 병합
10. `.env.example`, `README.md`를 통합 담당자가 마지막 별도 커밋으로 수정

### 9.4 충돌 처리 원칙

- `providers.py` 충돌은 Backend A가 해결한다.
- `main.py` 충돌은 Backend B가 해결한다.
- `frontend/**` 충돌은 Frontend 담당자가 해결한다.
- `.env.example`, `README.md` 충돌은 통합 담당자가 해결한다.
- 충돌 해결 시 한쪽 파일을 통째로 선택하지 말고 양쪽 변경 의도를 확인한다.
- `git reset --hard`, 강제 push, 다른 사람 커밋 삭제는 사용하지 않는다.

---

## 10. 구현 순서

### Backend A

1. `map_travel` 패키지와 Schema 작성
2. 교차 필드 Validator 작성
3. Schema 단위 테스트 작성
4. Prompt와 사용자 데이터 경계 작성
5. Mock 데이터 및 기간 해석 작성
6. 기존 Provider 매핑 확장
7. Provider Service 작성
8. Provider 테스트와 기존 Structured Output 회귀 테스트

### Backend B

1. A/B import 계약을 기준으로 Service 작성
2. 전용 Router 작성
3. `main.py`에 Router 최소 등록
4. API 정상·검증·실패 테스트 작성
5. OpenAPI 확인
6. 기존 API 회귀 테스트

### 통합

1. A 병합
2. B 최신화 및 병합
3. Mock 전체 흐름 확인
4. 실제 Provider별 수동 검증
5. Frontend에 API 계약 전달

---

## 11. 전체 테스트 명령과 기준

백엔드 작업 위치:

```powershell
cd C:\mini_agent\mini_agent_02_structured_output\backend
```

A 전용 테스트:

```powershell
pytest tests/test_map_travel_schema.py tests/test_map_travel_provider.py -q
```

B 전용 테스트:

```powershell
pytest tests/test_map_travel_api.py -q
```

병합 전 전체 테스트:

```powershell
pytest -q
```

완료 기준:

- 신규 테스트 전체 통과
- 기존 테스트 전체 통과
- Mock은 외부 API 키 없이 동작
- OpenAPI에 전용 경로와 Schema 표시
- 실제 Provider 실패가 다른 API를 중단시키지 않음
- 기존 2-1~2-3 기능 회귀 없음

---

## 12. Frontend 전달 체크리스트

Backend 완료 후 Frontend 담당자에게 다음만 전달한다.

- 실행 가능한 백엔드 기준 커밋 SHA
- API 경로: `POST /api/structured/map-travel`
- 요청 및 성공 응답 예시
- `422`, `502` 오류 예시
- Mock Provider 실행 방법
- OpenAPI 주소: `http://127.0.0.1:8000/docs`
- 지도 좌표 규칙: `latitude`는 위도, `longitude`는 경도
- 가격 단위: `estimated_price_krw`, 원화 정수
- 기간 표시 규칙: `0박 1일`은 당일치기

Frontend는 백엔드 Python 모델이나 Provider 모듈을 import하지 않고 HTTP API 계약만 사용한다.

---

## 13. 최종 인수 조건

- `POST /api/structured/map-travel`이 계약된 JSON을 반환한다.
- `provider` 생략과 네 Provider 선택을 지원한다.
- 당일치기와 `N박 M일`을 동일 Schema로 표현한다.
- 기간 미지정 시 `0박 1일`과 기본값 안내를 반환한다.
- Landmark는 1~10개, Food는 0~10개로 검증한다.
- 좌표와 가격 범위를 검증한다.
- 추가 필드를 거부한다.
- Mock이 외부 키 없이 동작한다.
- Provider 실패는 `502`, 검증 실패는 `422`로 반환한다.
- 기존 API와 테스트가 유지된다.
- A/B가 동일 파일을 수정하지 않는다.
- Frontend와의 병합은 `frontend/**`와 `backend/**` 분리를 유지해 충돌 없이 진행된다.

---

## 14. 구현 승인 전 상태

이 문서는 검토용 Backend Plan이다. 현재 단계에서는 `C:\mini_agent`의 Python 코드, 설정, 테스트, 의존성 및 Git 브랜치를 변경하지 않는다. 계획 승인 후 Backend A와 Backend B가 각자 소유 파일 범위 안에서 구현을 시작한다.
