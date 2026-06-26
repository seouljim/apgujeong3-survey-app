# 압구정3구역 조합원 설문조사 웹앱 v0.6

## 핵심 변경
- 첨부된 종이 설문지 PDF를 페이지 이미지로 렌더링해 앱에 그대로 표시합니다.
- 사용자는 종이 설문지를 한 장씩 넘기는 느낌으로 1~12페이지를 이동합니다.
- 이전 장 / 다음 장을 오가도 입력값이 유지됩니다.
- 마지막 페이지에 `조합원님의 다양한 의견` 입력란과 50MB 이하 파일 첨부 기능을 추가했습니다.
- 첨부파일은 Supabase Storage의 `survey-attachments-v06` 버킷에 저장되고, DB에는 파일 경로와 메타데이터가 저장됩니다.

## 적용 순서
1. Supabase SQL Editor에서 `supabase_schema.sql` 전체 실행
2. GitHub에 `app.py`, `requirements.txt`, `supabase_schema.sql`, `README.md`, `assets/` 폴더 전체 업로드
3. Streamlit Cloud에서 Reboot app
4. 테스트 제출
5. Supabase Table Editor에서 `survey_submissions_v06` 확인
6. Storage에서 `survey-attachments-v06` 버킷 확인
