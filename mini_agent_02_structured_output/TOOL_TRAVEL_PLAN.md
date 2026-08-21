# 2-5. 지도 기반 여행 계획 Tool Use — 공동 개발 계획서

## 1. 목적

`mini_agent_02_structured_output`에 기존 2-4와 독립된 **2-5. 지도 기반 여행 계획 Tool Use**
기능을 새로 추가한다. 기존 **2-4. Kakao Map Travel**의 코드와 동작은 변경하지 않는다.
사용자는 화면에서 여행 지역, 여행 일정 시작일과 종료일, 여행 인원을 선택하고, 백엔드는
이 값을 검증한 뒤 허용된 여행 조회 Tool을 실행한다.
그 결과로 해당 지역·일정·인원에 맞는 관광지와 맛집을 추천하고, 각 위치를 카카오맵에 표시한다.

이 기능은 `C:\aidevs\05_llm-agent-orchestration\03_tool-use`의 학습 흐름을 따른다.

```text
사용자 UI 입력
  → FastAPI 요청 검증
  → LLM 또는 Mock의 Tool Call 제안
  → Allowlist 확인 + Pydantic arguments 검증
  → 여행 Tool 실행
  → Tool Result 기반 최종 답변 생성
  → 구조화된 API 응답 + Streamlit 화면 표시
```

중요 원칙: Tool Call은 실행 명령이 아니라 LLM의 **제안**이다. 실행 권한, 허용 Tool,
입력값 검증, 실행 횟수와 오류 응답은 모두 백엔드가 담당한다.

이번 단계에서는 계획서만 수정한다. 기존 코드와 환경 파일은 수정하지 않는다.

---

## 2. MVP 범위

### 포함

- 기존 2-4를 수정하지 않고, 왼쪽 사이드바에 `2-5. 여행 계획 Tool Use` 버튼 추가
- 여행 지역 선택: `서울`, `부산`, `제주`, `강릉`, `인천`, `대전`, `대구`, `광주`, `전주`, `경주`
- 여행 일정 시작일과 종료일 선택
- 여행 인원 선택 (`1~10`명)
- 선택값을 API 요청 Body로 전송
- Pydantic `Field`를 사용한 모든 요청·응답·Tool arguments 필드 검증
- 지역·일정·인원에 맞춘 관광지와 맛집 추천
- 관광지와 맛집 위치를 카카오맵 마커로 표시
- Tool Schema, Tool Call, Tool Result, 최종 답변, 실행 Trace 표시
- Mock Provider와 Mock 여행 Tool로 API 키 없이 시연 가능
- 허용 Tool 목록, 날짜 교차 검증, 추가 필드 차단, 오류 상태 표시

### 제외

- 실제 숙소 예약·결제·취소
- 사용자 로그인과 예약 정보 영구 저장
- 외부 숙소 API의 실시간 재고 또는 가격 보장
- 기존 `2-1`~`2-4` 기능 변경

---

## 3. 화면 및 사용자 흐름

새 페이지는 `frontend/app_pages/13_travel_tool_use.py`로 둔다. `frontend/app.py`에서
`2-4. Kakao Map Travel` 아래에 `2-5. 여행 계획 Tool Use` 버튼을 등록한다.

화면 입력 구성:

| 입력 | Streamlit 컴포넌트 | API 필드 | 검증 |
| --- | --- | --- | --- |
| 여행 지역 | `st.selectbox` | `city` | 허용 지역 10개 중 하나 |
| 여행 일정 시작일 | `st.date_input` | `check_in` | 오늘 이후 |
| 여행 일정 종료일 | `st.date_input` | `check_out` | 시작일보다 이후 |
| 여행 인원 | `st.number_input` | `guests` | 정수, 1~10 |
| Provider | `st.selectbox` | `provider` | mock/gemini/openai/ollama |
| 계획 생성 | `st.button` | - | 필수값이 유효할 때만 활성화 |

MVP의 조회 Tool은 다음 두 개로 고정한다.

1. `recommend_attractions`: 지역·일정·인원에 적합한 관광지와 좌표를 조회한다.
2. `recommend_restaurants`: 지역·일정·인원에 적합한 맛집과 좌표·예상 가격을 조회한다.

Mock LLM은 두 Tool을 순서대로 제안한다. 실제 Provider에서는 Tool Call이 하나도
필요 없다고 판단할 수 있으나, 백엔드는 오직 Allowlist에 있는 Tool만 실행한다.

---

## 4. 백엔드-프론트엔드 공유 API 계약

### 4.1 Endpoint와 Router 반환 타입

```http
POST /api/tools/travel-plan
Content-Type: application/json
```

Router는 반드시 반환 타입을 명시한다.

```python
@travel_tool_router.post(
    "/api/tools/travel-plan",
    response_model=TravelPlanResponse,
)
def create_travel_plan(payload: TravelPlanRequest) -> TravelPlanResponse:
    ...
```

Service와 Tool 함수도 모두 명시적 반환 타입을 사용한다.

```python
def create_travel_plan(payload: TravelPlanRequest) -> TravelPlanResponse: ...
def recommend_attractions(arguments: TravelRecommendationInput) -> AttractionRecommendationResult: ...
def recommend_restaurants(arguments: TravelRecommendationInput) -> RestaurantRecommendationResult: ...
```

### 4.2 요청 Body

```json
{
  "provider": "mock",
  "city": "부산",
  "check_in": "2026-08-12",
  "check_out": "2026-08-14",
  "guests": 2
}
```

### 4.3 성공 응답 Body

```json
{
  "provider": "mock",
  "model": "deterministic-travel-tool-mock",
  "request": {
    "city": "부산",
    "check_in": "2026-08-12",
    "check_out": "2026-08-14",
    "guests": 2
  },
  "tool_calls": [
    {
      "id": "call_attraction_001",
      "name": "recommend_attractions",
      "arguments": {
        "city": "부산",
        "check_in": "2026-08-12",
        "check_out": "2026-08-14",
        "guests": 2
      }
    }
  ],
  "tool_results": [
    {
      "tool_call_id": "call_attraction_001",
      "name": "recommend_attractions",
      "success": true,
      "data": {
        "attractions": [
          {
            "name": "해운대해수욕장",
            "description": "바다 산책을 즐길 수 있는 대표 관광지입니다.",
            "latitude": 35.1587,
            "longitude": 129.1604
          }
        ]
      }
    }
  ],
  "answer": "부산 2명 여행 일정에 맞는 관광지와 맛집 정보를 확인했습니다.",
  "latency_ms": 0
}
```

### 4.4 HTTP 오류 계약

| 상태 | 상황 | 프론트 처리 |
| --- | --- | --- |
| `422` | 날짜·인원·도시·추가 필드·Tool arguments 검증 실패 | `detail`을 입력 오류로 표시 |
| `502` | Provider 호출 실패 | Provider 오류 안내 |
| `503` | Tool 실행 실패 | 재시도 안내 및 Trace 표시 |

비밀키, Provider 원본 예외 전문, 내부 스택 트레이스는 응답에 포함하지 않는다.

---

## 5. 공통 Pydantic 모델 규칙

모든 모델은 `ConfigDict(extra="forbid")`를 사용한다. 모든 데이터 필드에는
빠짐없이 `Field(...)`를 선언한다. 이는 백엔드와 프론트엔드의 계약 충돌을 막는
필수 규칙이다.

```python
class TravelPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderName | None = Field(default=None)
    city: Literal["서울", "부산", "제주", "강릉", "인천", "대전", "대구", "광주", "전주", "경주"] = Field(description="여행 지역")
    check_in: date = Field(description="여행 일정 시작일")
    check_out: date = Field(description="여행 일정 종료일")
    guests: int = Field(ge=1, le=10, description="여행 인원")

    @model_validator(mode="after")
    def validate_dates(self) -> "TravelPlanRequest":
        if self.check_out <= self.check_in:
            raise ValueError("여행 일정 종료일은 시작일 이후여야 합니다.")
        return self
```

예상 모델:

- `TravelPlanRequest`
- `TravelRecommendationInput`
- `ToolCall`, `ToolExecutionResult`
- `Attraction`, `AttractionRecommendationResult`
- `Restaurant`, `RestaurantRecommendationResult`
- `TravelPlanResponse`

`ToolCall.name`은 `Literal["recommend_attractions", "recommend_restaurants"]`로
제한하고, Tool 함수 진입 시에도 각 arguments 모델로 다시 검증한다.

---

## 6. 역할 분담 (4명)

| 담당 | 역할 | 주요 작업 | 완료 기준 |
| --- | --- | --- | --- |
| 백엔드 A | API·Schema | 요청/응답/Tool 모델, Router, 반환 타입, OpenAPI | 모든 Field와 교차 검증이 OpenAPI에 노출 |
| 백엔드 B | Tool·Provider | Allowlist, 관광지·맛집 Mock Tool, Mock/실제 Provider Tool Loop, 오류 변환 | 검증되지 않은 Tool/인자는 실행되지 않음 |
| 프론트엔드 A | 입력 화면 | 새 2-5 페이지의 지역·여행 일정·인원 입력, Client, 로딩·오류 상태 | 유효한 입력만 API에 전송 |
| 프론트엔드 B | 결과·지도 통합 | 2-5 카카오맵 마커, 관광지·맛집 결과 카드, Tool Call/Result/Trace 표시, E2E 확인 | API 응답만으로 지도와 결과를 정확히 렌더링 |

공동 작업 규칙:

- `TOOL_TRAVEL_PLAN.md`의 요청·응답 필드명, 타입, 범위를 변경하기 전 네 명 모두 합의한다.
- 프론트엔드는 응답을 임의로 조합하거나 LLM·Tool을 직접 호출하지 않는다.
- 백엔드는 Streamlit 화면 형식을 알 필요 없이 API 계약만 반환한다.
- 신규 파일을 우선 사용하고, Router 등록 및 사이드바 연결만 기존 파일을 최소 수정한다.
- 각자 로컬 `.env`를 만들며, `.env`는 커밋하지 않는다.

---

## 7. 파일 구조 계획

```text
mini_agent_02_structured_output/
├─ TOOL_TRAVEL_PLAN.md
├─ backend/app/
│  ├─ routers/travel_tool_router.py
│  ├─ travel_tools/
│  │  ├─ schemas.py
│  │  ├─ definitions.py
│  │  ├─ service.py
│  │  ├─ provider_service.py
│  │  └─ mock_data.py
│  └─ main.py                         # Router 등록만 최소 수정
├─ backend/tests/
│  ├─ test_travel_tool_schema.py
│  ├─ test_travel_tool_service.py
│  └─ test_travel_tool_api.py
├─ frontend/
│  ├─ app_pages/13_travel_tool_use.py
│  ├─ clients/travel_tool_client.py
│  └─ core/travel_kakao_map.py          # 2-5 전용 관광지·맛집 마커 렌더링
└─ .env.example                       # 키 이름만, 실제 값 없음
```

환경 변수는 개인별 `.env`에 둔다.

```dotenv
BACKEND_API_URL=http://127.0.0.1:8000
OPENAI_API_KEY=
GEMINI_API_KEY=
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

---

## 8. 구현 순서 및 검증

1. 네 명이 이 문서의 API 계약과 Field 규칙을 확정한다.
2. 백엔드 A가 Schema와 빈 Router의 반환 타입/응답 모델을 먼저 만든다.
3. 프론트엔드 A가 확정된 요청 계약으로 입력 UI와 Client를 만든다.
4. 백엔드 B가 Mock Tool, Allowlist, Tool Loop 및 Tool Result를 구현한다.
5. 프론트엔드 B가 2-5 카카오맵 마커, 관광지·맛집 결과와 Trace 화면을 구현한다.
6. Mock Provider로 통합 테스트 후 실제 Provider를 선택적으로 확인한다.
7. 기존 `mini_agent_02_structured_output` 테스트를 회귀 실행한다.

필수 테스트:

- 정상 요청: 부산, `2026-08-12`~`2026-08-14`, 2명
- 여행 일정 종료일이 시작일과 같거나 이전인 요청 거부
- 0명과 11명 요청 거부
- 정의되지 않은 요청 필드 거부
- Allowlist 밖 Tool 이름 거부
- Tool arguments의 추가 필드 거부
- Mock 결과에 관광지·맛집 Tool Result와 유효한 좌표가 포함되는지 확인
- Router의 `response_model`과 함수 반환 타입 확인
- 프론트엔드에서 `422`, `502`, `503` 오류를 사용자 친화적으로 표시하는지 확인

---

## 9. 향후 AI Agent 연결을 위한 리팩터링 기준

이번 MVP는 지역·여행 일정·인원을 UI에서 모두 받는 **고정 Tool Use Workflow**로 구현한다.
그러나 이후 사용자가 자연어로 "다음 주 부산 2명 여행 계획해 줘"라고 요청하고,
Agent가 누락 정보를 재질문하거나 Tool 결과에 따라 다음 Tool을 고를 수 있도록 확장할 수 있다.

이를 위해 지금부터 다음 경계를 유지한다.

```text
Streamlit UI / 향후 Agent UI
          ↓ 같은 API Request 모델 사용
Travel Planning Service
          ↓
Tool Selection 정책 또는 Agent Orchestrator
          ↓
Allowlist + Tool Executor
          ↓
관광지 · 맛집 Tool
```

### 리팩터링 원칙

- `frontend/app_pages/13_travel_tool_use.py`는 입력과 결과 렌더링만 담당한다. Provider 호출,
  Tool 선택, Tool 실행 판단을 넣지 않는다.
- `map_travel_router.py`는 HTTP 요청·응답과 오류 변환만 담당한다. 업무 규칙과 Tool Loop는
  Service로 이동한다.
- `TravelPlanningService`는 고정 Workflow와 Agent Orchestrator가 공통으로 사용할 수 있는
  `create_plan(request: TravelPlanRequest) -> TravelPlanResponse` 진입점을 제공한다.
- `ToolExecutor`를 별도 모듈로 두고, 모든 Tool은 `ToolCall`과 Tool별 Pydantic arguments
  모델을 검증한 뒤 Allowlist로 실행한다. Agent도 이 Executor를 우회할 수 없다.
- `recommend_attractions`, `recommend_restaurants`는
  순수한 조회 함수로 유지한다. Streamlit, FastAPI Request 객체, LLM SDK에 직접 의존하지 않는다.
- Tool 실행 결과는 공통 `ToolExecutionResult` 모델로 정규화한다. 고정 Workflow와 Agent가
  같은 결과·오류 형식·Trace를 사용하게 한다.
- 현재의 선택형 입력은 `TravelPlanRequest`로 유지하고, 향후 자연어 입력용 Agent API는
  별도 `AgentTravelPlanRequest`를 추가한다. 기존 `/api/tools/travel-plan` 요청 계약을
  깨거나 `message` 같은 선택 필드를 무분별하게 섞지 않는다.
- Agent 연결 시에는 `POST /api/agent/travel-plan` 같은 새 Router를 추가한다. 이 Router도
  최종적으로는 동일한 `TravelPlanningService`와 `ToolExecutor`를 사용하고,
  `response_model`과 명시적 반환 타입을 선언한다.
- 무한 반복을 방지하기 위해 Agent Orchestrator에는 `max_steps`(예: 5), Tool별 timeout,
  허용 Tool 목록, 재시도 정책을 설정한다.
- 예약·결제·삭제처럼 상태를 바꾸는 Tool을 후속 추가할 경우, 조회 Tool과 분리하고 사용자 승인
  단계를 거치게 한다. 이번 MVP의 Tool은 모두 읽기 전용이다.

### Agent 확장 단계

1. 새 선택형 2-5의 Mock Tool Use Workflow와 지도 표시를 완성한다.
2. `ToolExecutor`와 `ToolExecutionResult`를 독립 모듈로 추출해 단위 테스트한다.
3. 자연어에서 `city`, 여행 일정, `guests`를 추출하는 Agent 입력 Schema를 추가한다.
4. 값이 빠진 경우 Tool 실행 전 재질문 상태를 반환한다.
5. Agent가 제안한 Tool Call도 기존 Allowlist·Field 검증·실행 제한을 통과시킨다.
6. 같은 지도 응답 모델로 관광지·맛집 마커를 렌더링해 프론트엔드 변경을 최소화한다.

## 10. 완료 조건

- 기존 2-4를 변경하지 않고, 왼쪽 메뉴에서 `2-5. 여행 계획 Tool Use` 페이지에 접근할 수 있다.
- 사용자는 10개 여행 지역, 여행 일정 시작일·종료일, 인원을 선택할 수 있다.
- API의 모든 Router가 명시적 반환 타입과 `response_model`을 가진다.
- 모든 Pydantic 필드가 `Field`로 선언되고 추가 필드는 차단된다.
- 백엔드가 검증과 Allowlist를 통과한 Tool만 실행한다.
- Mock 모드에서 API 키 없이 Tool Call → Tool Result → 관광지·맛집 추천 → 지도 마커 → 최종 답변의 전체 흐름을 시연한다.
- 프론트엔드와 백엔드가 이 문서의 API 계약만으로 독립 구현·통합할 수 있다.
