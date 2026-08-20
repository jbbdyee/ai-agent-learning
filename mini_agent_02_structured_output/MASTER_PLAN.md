# 2-4. Streamlit 카카오맵 구조화 여행 추천 — Master Plan

## 1. 문서 목적

이 문서는 `mini_agent_02_structured_output`에 추가할 **2-4. 카카오맵 여행 추천** 기능의 구현 기준을 정의한다.

구현은 다음 순서를 따른다.

```text
Master Plan
├─ Backend Plan
└─ Frontend Plan
```

Master Plan은 백엔드와 프론트엔드가 공유할 기능 범위와 API 계약을 정의한다. Backend Plan과 Frontend Plan은 이 계약을 기준으로 각각 독립적으로 구현할 작업을 정의한다.

이 문서를 추가하는 단계에서는 기존 Python 코드, 설정 파일, 테스트 및 의존성을 수정하지 않는다.

---

## 2. 기능 목표

사용자가 여행지, 여행 기간, 원하는 활동을 자연어 질문으로 입력하면 백엔드가 여행 기간, 랜드마크와 음식 추천을 구조화된 JSON으로 생성한다. 여행 기간은 `당일치기`, `1박 2일`, `2박 3일`처럼 고정되지 않은 형태를 지원한다. Streamlit 프론트엔드는 결과를 받아 다음 형태로 출력한다.

- 카카오맵 위에 랜드마크와 음식 위치 마커 표시
- 마커 선택 시 장소명과 설명 표시
- 랜드마크 상세 목록 표시
- 음식명과 예상 가격 표시
- 해석된 여행 기간 표시
- 주의사항과 구조화된 원본 JSON 표시

예시 질문:

```text
부산에 2박 3일 여행을 가고자 해. 관광지와 음식을 추천해 주세요.
```

당일치기 입력도 지원한다.

```text
부산 당일치기로 방문할 관광지와 음식을 추천해 주세요.
```

---

## 3. 범위

### 포함 범위

- 사이드바 `02. Prompt와 구조화 출력` 아래에 `2-4. 카카오맵 여행 추천` 페이지 추가
- Streamlit 입력 및 결과 화면
- FastAPI 기반 구조화 출력 API
- Pydantic 기반 요청·응답 검증
- `mock`, `gemini`, `openai`, `ollama` Provider 구조 유지
- 카카오맵 JavaScript SDK를 Streamlit HTML 컴포넌트에 삽입
- Mock Provider만으로 전체 흐름을 확인할 수 있는 데이터 제공
- 백엔드 및 프론트엔드 오류 처리
- API 자동 테스트

### 제외 범위

- 카카오 로컬 검색 API를 이용한 장소 검색 및 좌표 검증
- 음식점 예약, 결제, 길찾기 및 실시간 교통 정보
- 실제 음식 가격과 영업시간의 정확성 보장
- 사용자 로그인과 추천 결과 영구 저장
- 기존 2-1~2-3 기능 변경

### 데이터 정확성 원칙

이번 기능의 좌표와 음식 가격은 LLM 또는 Mock Provider가 생성하는 교육용 추천 데이터다. 실제 방문 전에 장소 위치, 가격, 영업시간을 확인해야 한다는 안내를 화면에 표시한다.

---

## 4. 전체 처리 흐름

```text
사용자 질문 입력
    ↓
Streamlit이 Backend API 호출
    ↓
FastAPI가 Provider에 구조화 출력 요청
    ↓
Pydantic이 응답 Schema 검증
    ↓
검증된 JSON을 Streamlit에 반환
    ↓
Streamlit이 카카오맵과 추천 목록 렌더링
```

역할 분리 원칙:

- 백엔드는 질문 처리, Provider 호출, 구조화 출력 생성 및 검증을 담당한다.
- 프론트엔드는 사용자 입력, API 호출, 카카오맵 및 결과 표현을 담당한다.
- 프론트엔드는 LLM을 직접 호출하지 않는다.
- 백엔드는 카카오맵 화면을 생성하지 않는다.
- 양쪽은 아래 API 계약만 공유한다.

---

## 5. Backend–Frontend 공유 계약

### 5.1 API

권장 전용 API:

```http
POST /api/structured/map-travel
Content-Type: application/json
```

기존 범용 구조화 API를 확장할 수도 있지만, 학습 페이지의 목적과 테스트 범위를 분명하게 하기 위해 전용 경로를 우선 사용한다.

### 5.2 요청 계약

```json
{
  "provider": "mock",
  "message": "부산에 2박 3일 여행을 가고자 해. 관광지와 음식을 추천해 주세요."
}
```

검증 규칙:

- `provider`: `mock`, `gemini`, `openai`, `ollama` 중 하나
- `message`: 공백이 아닌 문자열, 최대 4,000자
- 여행 기간은 별도의 입력 필드가 아니라 `message` 안의 자연어 표현으로 전달
- `당일치기`, `1박 2일`, `2박 3일` 등의 기간 표현 지원
- Provider가 생략되면 백엔드 기본 Provider 사용

### 5.3 성공 응답 계약

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

### 5.4 필드 검증 규칙

#### 최상위 content

- `destination`: 필수 문자열
- `nights`: 0 이상의 정수. 당일치기는 `0`
- `days`: 1 이상의 정수. 당일치기는 `1`
- 일반적인 숙박 여행에서는 `days = nights + 1` 관계를 만족
- `summary`: 필수 문자열, 최대 500자
- `landmarks`: 객체 배열, 1~10개
- `foods`: 객체 배열, 0~10개
- `cautions`: 문자열 배열, 최대 10개
- 정의하지 않은 추가 필드 금지

#### landmark 객체

- `name`: 필수 문자열
- `description`: 필수 문자열, 최대 500자
- `latitude`: 숫자, `-90` 이상 `90` 이하
- `longitude`: 숫자, `-180` 이상 `180` 이하
- `category`: 필수 문자열
- 정의하지 않은 추가 필드 금지

#### food 객체

- `name`: 필수 문자열
- `estimated_price_krw`: 0 이상의 정수
- `description`: 필수 문자열, 최대 500자
- `latitude`: 숫자, `-90` 이상 `90` 이하
- `longitude`: 숫자, `-180` 이상 `180` 이하
- 정의하지 않은 추가 필드 금지

### 5.5 오류 계약

- `422`: 요청값 또는 구조화 결과 검증 실패
- `502`: 외부 Provider 호출 실패
- 프론트엔드는 응답의 `detail`을 사용자용 오류 메시지로 표시
- Provider 키, 토큰 또는 내부 예외 전체를 응답이나 로그 화면에 노출하지 않음

---

## 6. Backend Plan

### 6.1 백엔드 책임

- 요청 메시지와 Provider 검증
- 자연어 질문에서 여행지와 여행 기간을 구조화된 필드로 생성
- 구조화 출력용 Pydantic Schema 제공
- Provider별 구조화 출력 생성
- 생성 결과의 여행 기간·좌표·가격·배열 개수 검증
- 검증이 끝난 데이터만 프론트엔드에 반환
- 일관된 HTTP 상태 코드와 오류 메시지 제공

### 6.2 신규 파일 우선 원칙

실제 구현 단계에서는 가능한 기능을 신규 모듈로 분리한다.

예상 신규 파일:

```text
backend/app/schemas/map_travel.py
backend/app/services/map_travel_service.py
backend/app/routers/map_travel_router.py
backend/tests/test_map_travel_api.py
```

다만 FastAPI Router 등록, 공통 Provider 연결처럼 애플리케이션 진입점과 연결해야 하는 부분은 기존 파일의 최소 수정이 필요하다. 이 작업은 구현 승인 이후에만 수행한다.

### 6.3 Schema 설계

다음 모델을 정의한다.

- `MapTravelRequest`
- `TravelDuration`
- `Landmark`
- `FoodRecommendation`
- `MapTravelContent`
- `MapTravelResponse`

모든 응답 모델은 가능하면 `extra="forbid"`를 적용한다.

`TravelDuration` 또는 `MapTravelContent`에는 다음 교차 필드 검증을 둔다.

- `nights >= 0`
- `days >= 1`
- `days == nights + 1`
- `당일치기`는 `nights=0`, `days=1`로 정규화

### 6.4 Provider 처리

- Mock: 부산·서울·제주·강릉 등 고정된 샘플 좌표와 음식 데이터를 반환하고, 질문의 `당일치기` 또는 `N박 M일` 표현을 기간 필드로 변환
- OpenAI: Pydantic Schema를 사용한 structured output
- Gemini: JSON Schema 기반 structured output 후 Pydantic 재검증
- Ollama: JSON Schema를 `format`으로 전달한 후 Pydantic 재검증
- 어떤 Provider를 사용해도 최종 API 계약은 동일하게 유지

### 6.5 시스템 프롬프트 원칙

- 요청한 지역과 관련된 랜드마크와 음식을 반환
- 요청에 포함된 `당일치기` 또는 `N박 M일` 표현을 `nights`, `days`로 반환
- 여행 기간에 맞는 수와 범위의 추천을 제공
- 모르는 정보를 확정적으로 표현하지 않음
- 모든 랜드마크와 음식에 유효한 위도와 경도 제공
- 가격은 예상값임을 전제로 원화 정수로 반환
- JSON Schema에 없는 필드 생성 금지
- 실제 방문 전 위치·가격·영업시간 확인을 `cautions`에 포함

### 6.6 백엔드 테스트

- Mock API 정상 응답
- `당일치기` 입력이 `nights=0`, `days=1`로 반환되는지 확인
- `2박 3일` 입력이 `nights=2`, `days=3`으로 반환되는지 확인
- `days != nights + 1`인 구조화 결과 거부
- `landmarks`와 `foods`가 객체 배열로 반환되는지 확인
- 위도 및 경도 범위 검증
- 음식 위치의 위도 및 경도 범위 검증
- 음수 가격 거부
- 추가 필드 거부
- 빈 질문 및 4,000자 초과 질문 거부
- 잘못된 Provider 거부
- Provider 실패 시 `502` 반환
- OpenAPI에 전용 경로와 응답 모델 노출
- 기존 API 회귀 테스트 통과

### 6.7 백엔드 완료 조건

- Mock Provider로 외부 API 키 없이 성공 응답 생성
- 당일치기와 숙박 여행의 기간이 동일한 Schema로 표현됨
- 모든 성공 응답이 Pydantic 계약을 통과
- Provider별 데이터 구조가 동일
- 기존 2-1~2-3 API 동작 유지

---

## 7. Frontend Plan

### 7.1 프론트엔드 책임

- 질문과 Provider 입력 UI 제공
- 백엔드가 해석한 `nights`, `days`를 사용자에게 여행 기간으로 표시
- 백엔드 API 호출
- 로딩, 성공, 빈 결과 및 오류 상태 표시
- 검증된 랜드마크와 음식 위치를 카카오맵 마커로 표시
- 음식과 예상 가격을 Streamlit UI로 표시
- 지도 실패 시에도 텍스트 결과 유지

### 7.2 Streamlit 신규 파일

예상 신규 파일:

```text
frontend/app_pages/12_map_travel.py
frontend/core/kakao_map.py
```

- `12_map_travel.py`: 페이지 UI와 API 응답 표시
- `kakao_map.py`: 카카오맵 HTML 생성과 안전한 데이터 직렬화

API Client 함수는 구현 단계에서 기존 `frontend/clients/agent_client.py`에 최소 추가하거나, 기능 전용 신규 Client 파일로 분리할 수 있다.

사이드바 등록을 위해 기존 `frontend/app.py`의 최소 수정이 필요하지만, 이 작업 역시 구현 승인 이후에만 수행한다.

### 7.3 Streamlit 화면 구성

```text
페이지 제목과 설명
Provider 선택
질문 입력
추천 결과 생성 버튼
처리 상태
해석된 여행 기간
카카오맵
랜드마크 목록
음식 및 예상 가격 목록
주의사항
구조화 JSON 원문
```

권장 Streamlit 컴포넌트:

- `st.selectbox`: Provider 선택
- `st.text_area`: 질문 입력
- `st.button`: 요청 실행
- `st.spinner`: 요청 처리 상태
- `st.metric` 또는 `st.caption`: `당일치기` 또는 `N박 M일` 여행 기간 표시
- `st.components.v1.html`: 카카오맵 렌더링
- `st.container`: 랜드마크 카드
- `st.dataframe` 또는 `st.table`: 음식과 예상 가격
- `st.warning`, `st.error`: 안내 및 오류
- `st.json`: 원본 구조화 결과

### 7.4 카카오맵 렌더링 방식

Streamlit은 React 또는 별도 SPA를 추가하지 않고 `st.components.v1.html()`로 카카오맵 HTML과 JavaScript를 삽입한다.

HTML 컴포넌트는 다음 작업만 담당한다.

- 카카오맵 JavaScript SDK 로딩
- 지도 컨테이너 생성
- 첫 번째 유효 랜드마크를 초기 중심으로 설정
- 모든 랜드마크와 음식 위치에 마커 생성
- 랜드마크와 음식 마커를 색상 또는 아이콘으로 구분
- 마커 클릭 시 장소명 또는 음식명과 설명을 InfoWindow로 표시
- 여러 마커가 있으면 `LatLngBounds`로 전체 마커가 보이도록 조정
- SDK 또는 지도 초기화 실패 시 컴포넌트 내부 오류 문구 표시

백엔드가 반환한 문자열을 JavaScript 문자열에 직접 이어 붙이지 않는다. `json.dumps()`로 직렬화하고 HTML 특수문자와 스크립트 종료 문자열이 실행 코드로 해석되지 않도록 처리한다.

### 7.5 카카오맵 키 설정

- 환경 변수명: `KAKAO_MAP_JAVASCRIPT_KEY`
- 카카오 개발자 콘솔에서 **JavaScript 키** 사용
- Streamlit 접속 주소를 카카오 개발자 콘솔의 Web 플랫폼 도메인에 등록
- 로컬 개발 주소 예: `http://localhost:8501`
- 배포 주소가 생기면 해당 Origin도 별도로 등록
- JavaScript 키는 브라우저에서 사용되는 식별 키이므로 도메인 제한이 필수
- REST API 키, Admin 키, LLM Provider 비밀키는 프론트 HTML에 포함하지 않음

### 7.6 지도와 목록의 실패 분리

- 카카오맵 키 없음: `st.warning` 표시 후 장소·음식 목록은 정상 출력
- SDK 로딩 실패: 지도 영역에 오류 표시 후 나머지 결과 유지
- 유효 좌표 없음: 지도 대신 안내 문구 표시
- 일부 좌표만 잘못됨: 잘못된 랜드마크 또는 음식의 마커만 제외하고 목록은 유지
- 백엔드 호출 실패: 지도와 결과를 렌더링하지 않고 API 오류 표시
- 음식 목록 없음: `추천 음식이 없습니다`라는 빈 상태 표시

### 7.7 프론트엔드 완료 조건

- `streamlit run frontend/app.py`로 페이지 접근 가능
- 사이드바의 2-3 아래에 2-4 메뉴 표시
- Mock 응답의 모든 유효한 랜드마크와 음식 위치가 카카오맵 마커로 표시
- 마커 클릭 시 장소명 또는 음식명과 설명 표시
- 음식명과 예상 가격을 읽기 쉬운 형태로 출력
- `nights=0`, `days=1`은 `당일치기`, 그 외에는 `N박 M일`로 표시
- 카카오맵 실패 시에도 텍스트 결과와 JSON 확인 가능
- 기존 Streamlit 페이지 동작 유지

---

## 8. 구현 순서

1. 공유 API 계약과 Pydantic 모델 확정
2. Backend Plan에 따라 Mock Provider와 API 구현
3. 백엔드 단위 및 API 테스트 작성
4. Frontend Plan에 따라 API Client와 Streamlit 페이지 구현
5. 카카오맵 HTML 컴포넌트 구현
6. 사이드바에 2-4 페이지 연결
7. Mock 기반 전체 흐름 검증
8. 실제 Provider별 구조화 출력 검증
9. 카카오맵 키 등록 및 브라우저 렌더링 검증
10. 기존 2-1~2-3 회귀 테스트

---

## 9. 전체 인수 조건

- 사용자가 지역 여행 질문을 입력할 수 있다.
- 사용자는 질문에 `당일치기` 또는 `N박 M일` 형태로 여행 기간을 입력할 수 있다.
- 백엔드는 당일치기를 `nights=0`, `days=1`로, 숙박 여행을 해당 정수 값으로 반환한다.
- 백엔드는 `landmarks: [{...}]`, `foods: [{...}]` 형태의 유효한 JSON을 반환한다.
- 랜드마크에는 이름, 설명, 위도, 경도, 카테고리가 존재한다.
- 음식에는 이름, 예상 가격, 설명, 위도 및 경도가 존재한다.
- Streamlit에서 카카오맵과 추천 결과가 함께 표시된다.
- 카카오맵 마커와 장소 목록의 데이터가 일치한다.
- 지도 또는 SDK 오류가 텍스트 결과 표시를 막지 않는다.
- Mock 모드에서는 외부 LLM API 키 없이 기능을 시연할 수 있다.
- 기존 기능과 테스트가 손상되지 않는다.

---

## 10. 구현 전 확인 사항

- 카카오 개발자 콘솔에서 애플리케이션과 JavaScript 키 준비
- 로컬 Streamlit 도메인 등록
- 전용 API 경로 `/api/structured/map-travel` 사용 확정
- 랜드마크 최소 개수를 1개로 유지할지, 빈 배열도 허용할지 확정
- 음식 가격을 단일 예상 가격으로 표현할지 가격 범위로 표현할지 확정
- 기간이 질문에 명시되지 않았을 때 기본 기간을 적용할지 사용자에게 재질문할지 확정
- LLM이 생성한 좌표를 MVP에서 그대로 사용할지, 이후 카카오 로컬 API 검증 단계로 확장할지 결정

현재 Master Plan은 다음 기본값을 사용한다.

- 전용 API 경로 사용
- 랜드마크 최소 1개
- 음식 가격은 `estimated_price_krw` 단일 정수
- 당일치기는 `nights=0`, `days=1`로 표현
- 숙박 여행은 `days=nights+1` 관계로 검증
- 기간이 명시되지 않으면 MVP에서는 `nights=0`, `days=1`을 기본값으로 사용하고 결과 안내에 기본값 적용 사실을 표시
- MVP에서는 LLM 또는 Mock이 생성한 좌표 사용
- 카카오 로컬 검색 API 연동은 후속 기능으로 분리
