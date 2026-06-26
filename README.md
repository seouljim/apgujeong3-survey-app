# 압구정3구역 희망평형·위치 조사 웹앱 v0.3

조합원이 각자 휴대폰으로 URL에 접속해 정보를 입력하면 중앙 Supabase DB에 저장되고, 관리자는 웹에서 통계와 CSV를 확인하는 구조입니다.

## 구조
조합원 휴대폰 → 웹앱 URL 접속 → 정보 입력 → Supabase 중앙 DB 저장 → 관리자 통계 확인 → CSV 다운로드

## 준비
1. Supabase 프로젝트 생성
2. SQL Editor에서 `supabase_schema.sql` 실행
3. `.streamlit/secrets.toml` 또는 배포 서비스 Secrets에 아래 입력

```toml
SUPABASE_URL = "https://여기에_supabase_project_url.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "여기에_service_role_key"
SURVEY_ADMIN_PASSWORD = "관리자비밀번호"
```

## 로컬 테스트
```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

## 배포
Streamlit Cloud, Render, Railway 등에 배포하면 됩니다. 배포 후 URL이나 QR코드를 조합원에게 공유하면 됩니다.

## 휴대폰에서 앱처럼 쓰기
- 아이폰 Safari: 공유 → 홈 화면에 추가
- 안드로이드 Chrome: 메뉴 → 홈 화면에 추가

앱스토어 설치 없이도 아이콘으로 실행할 수 있습니다.
