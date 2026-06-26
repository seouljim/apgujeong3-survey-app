# 압구정3구역 조합원 설문조사 웹앱 v0.7

## 핵심
- 종이 설문지 재현형 UI
- 입력 페이지는 웹으로 재구성하여 해당 위치에서 직접 클릭/입력
- 참고자료 페이지는 원본 이미지로 표시
- 이전/다음 이동 시 입력값 유지
- 마지막 의견 제출 + 50MB 이하 파일 첨부
- v0.7 전용 테이블: survey_submissions_v07
- v0.7 전용 첨부 버킷: survey-attachments-v07

## 적용
1. Supabase SQL Editor에서 supabase_schema.sql 실행
2. GitHub에 app.py, requirements.txt, supabase_schema.sql, README.md, assets 폴더 업로드
3. Streamlit Reboot
