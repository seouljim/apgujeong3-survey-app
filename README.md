# 압구정3구역 조합원 희망평형·위치 조사 웹앱 v0.5 안정판

## 핵심 변경
- 기존 `submissions` 테이블을 사용하지 않습니다.
- 새 테이블 `survey_submissions_v05`, `survey_edit_logs_v05`만 사용합니다.
- Supabase/PostgREST 캐시 꼬임을 피하기 위해 테이블명을 새로 만들었습니다.

## 반영 순서
1. Supabase SQL Editor에서 `supabase_schema.sql` 전체 실행
2. GitHub에 `app.py`, `requirements.txt`, `supabase_schema.sql`, `README.md` 덮어쓰기 업로드
3. Streamlit Cloud에서 Reboot app
4. 테스트 제출
5. Supabase Table Editor에서 `survey_submissions_v05`에 데이터가 들어오는지 확인
