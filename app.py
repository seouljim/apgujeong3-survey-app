
import os
import hmac
import hashlib
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from supabase import create_client, Client

APP_TITLE = "압구정3구역 조합원 설문조사"
SUBMISSIONS_TABLE = "survey_submissions_v06"
EDIT_LOGS_TABLE = "survey_edit_logs_v06"
STORAGE_BUCKET = "survey-attachments-v06"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

PAGE_COUNT = 12
ASSET_DIR = Path(__file__).parent / "assets"

CURRENT_SIZE_OPTIONS = [
    "30평형대", "31.72평", "32.10평", "34.56평", "35.42평", "36.74평",
    "40평형대", "43.29평", "43.24평", "47.75평",
    "50평형대", "50.40평", "51.96평", "52.92평", "54.03평",
    "60평형대", "64.52평", "64.55평", "64.99평",
    "80평형대", "80.30평", "87.75평", "92.01평",
    "빌라트", "72.79평", "75.98평", "86.89평", "92.26평", "기타"
]

HOPE_SIZE_OPTIONS = [
    "25평형", "36평형", "43평형", "48평형", "53평형",
    "58평형", "65평형", "75평형", "85평형", "90평형",
    "준펜트하우스 90평형", "준펜트하우스 95평형",
    "펜트하우스 90평형", "펜트하우스 95평형", "펜트하우스 105평형"
]

FAMILY_PLAN_OPTIONS = ["입주 계획 있음", "입주 계획 없음(임대 등)"]
PROPERTY_TYPE_OPTIONS = ["아파트", "상가"]
PLAN_OPTIONS = [
    "거실·주방 면적이 다소 줄어도 방의 개수가 많은 평면",
    "방의 개수보다 거실·주방 면적이 넓은 평면",
]
ROOM_OPTIONS = ["3개", "4개", "5개", "6개 이상"]
HOUSEHOLD_SPLIT_OPTIONS = ["희망함", "희망 안함"]
IMPORTANT_FACTORS = ["조망", "위치(역세권·학세권·숲세권 등)", "분담금", "향", "층수"]
PARKING_OPTIONS = ["2.5대", "2.5대 ~ 3대", "3대 초과", "기타"]

COMMUNITY_OPTIONS = [
    "다목적체육관", "실내수영장", "실내골프연습장", "스크린골프", "인도어 골프장", "피트니스센터",
    "사우나", "클라이밍", "실내테니스장", "볼링장", "프라이빗피트니스", "프라이빗 사우나",
    "펫 라운지", "펫 호텔", "시니어살롱(노인정)", "시니어케어센터", "실내놀이터", "스터디룸",
    "도서관", "아트 수장고", "게스트하우스", "올데이다이닝", "파티룸", "웰컴센터",
    "소공연장", "공유오피스", "주민카페",
    "스카이커뮤니티(게스트하우스)", "스카이커뮤니티(카페&라운지)", "스카이커뮤니티(피트니스)",
]

LANDSCAPE_OPTIONS = [
    "산책로", "사계절 정원", "프라이빗 정원", "대형 중앙공원", "예술·조각정원", "숲속 정원",
    "사계절실내온실", "압구정지 갤러리", "티하우스", "명상 공간", "캠핑장", "리조트형수경시설",
    "생태 연못", "바닥분수", "어린이 놀이터", "펫 놀이터", "야외 공연장", "한강전망대",
]

SEMI_RESIDENTIAL_OPTIONS = [
    "하이엔드 오피스텔",
    "시니어 특화형 공동주택",
    "교육시설(비인가 국제학교)",
    "하이엔드 브랜드 상업시설",
    "기타",
]


def clean_supabase_url(url: str) -> str:
    url = str(url or "").strip().strip('"').strip("'")
    for suffix in ["/rest/v1/", "/rest/v1"]:
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url.rstrip("/")


def get_secret(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


SUPABASE_URL = clean_supabase_url(get_secret("SUPABASE_URL"))
SUPABASE_KEY = get_secret("SUPABASE_SERVICE_ROLE_KEY") or get_secret("SUPABASE_ANON_KEY")
SUPABASE_KEY = str(SUPABASE_KEY or "").strip().strip('"').strip("'")
ADMIN_PASSWORD = get_secret("SURVEY_ADMIN_PASSWORD", "admin123")


@st.cache_resource
def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Supabase 연결 정보가 없습니다. Streamlit Secrets를 확인해 주세요.")
        st.stop()
    if "/rest/v1" in SUPABASE_URL:
        st.error("SUPABASE_URL에는 /rest/v1 을 넣지 말고 Project URL만 넣어야 합니다.")
        st.code('SUPABASE_URL = "https://프로젝트ID.supabase.co"')
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def init_state():
    if "page_idx" not in st.session_state:
        st.session_state.page_idx = 1
    if "survey_data" not in st.session_state:
        st.session_state.survey_data = {}
    if "submitted_ok" not in st.session_state:
        st.session_state.submitted_ok = False


def normalize_text(x):
    return str(x or "").strip().replace(" ", "")


def make_unit_key(name, dong, ho):
    raw = "|".join([normalize_text(name), normalize_text(dong), normalize_text(ho)])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def field_key(name):
    return f"fld_{name}"


def get_data(name, default=None):
    return st.session_state.survey_data.get(name, default)


def set_widget_default(name, default=None):
    k = field_key(name)
    if k not in st.session_state:
        st.session_state[k] = get_data(name, default)


def save_keys(names):
    for name in names:
        k = field_key(name)
        if k in st.session_state:
            st.session_state.survey_data[name] = st.session_state[k]


ALL_FIELD_NAMES = [
    "owner_name", "signature_name", "address", "phone", "property_type", "existing_dong", "existing_ho", "current_size", "current_size_other",
    "family_plan", "family_count", "plan_preference", "room_count", "household_split",
    "factor_rank_1", "factor_rank_2", "factor_rank_3", "factor_rank_4", "factor_rank_5",
    "hope_size",
    "parking", "parking_other",
    "community_rank_1", "community_rank_2", "community_rank_3", "community_rank_4", "community_rank_5", "community_other",
    "landscape_rank_1", "landscape_rank_2", "landscape_rank_3", "landscape_rank_4", "landscape_rank_5", "landscape_other",
    "semi_residential", "semi_residential_other",
    "final_opinion",
]


def save_current_page():
    save_keys(ALL_FIELD_NAMES)


def page_image(page_no):
    img_path = ASSET_DIR / f"page_{page_no:02d}.png"
    if img_path.exists():
        st.image(str(img_path), use_container_width=True)
    else:
        st.warning(f"페이지 이미지가 없습니다: {img_path}")


def go_to_page(new_page):
    save_current_page()
    st.session_state.page_idx = max(1, min(PAGE_COUNT, int(new_page)))
    st.rerun()


def nav_buttons():
    st.divider()
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.session_state.page_idx > 1:
            if st.button("← 이전 장", use_container_width=True):
                go_to_page(st.session_state.page_idx - 1)
    with c2:
        st.markdown(
            f"<div style='text-align:center; padding-top:0.55rem;'>"
            f"<b>{st.session_state.page_idx} / {PAGE_COUNT}</b>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with c3:
        if st.session_state.page_idx < PAGE_COUNT:
            if st.button("다음 장 →", type="primary", use_container_width=True):
                go_to_page(st.session_state.page_idx + 1)


def rank_select(name_prefix, options, count=5, allow_skip=False):
    selected = []
    opts = (["선택 안함"] + options) if allow_skip else options
    cols = st.columns(count)
    for i in range(1, count + 1):
        name = f"{name_prefix}_{i}"
        default = get_data(name, opts[0])
        if default not in opts:
            default = opts[0]
        set_widget_default(name, default)
        with cols[i - 1]:
            selected.append(st.selectbox(f"{i}순위", opts, key=field_key(name)))
    return selected


def validate_unique(values, label):
    vals = [v for v in values if v and v != "선택 안함"]
    if len(vals) != len(set(vals)):
        st.error(f"{label} 순위는 중복 없이 선택해 주세요.")
        return False
    return True


def render_inputs_for_page(page_no):
    if page_no == 1:
        st.subheader("소유주 인적사항 입력")
        st.caption("종이 설문지의 소유주 인적사항 부분을 웹에서 입력합니다.")
        c1, c2 = st.columns(2)
        with c1:
            set_widget_default("owner_name", "")
            st.text_input("성명", key=field_key("owner_name"))
            set_widget_default("address", "")
            st.text_input("주소", key=field_key("address"))
            set_widget_default("phone", "")
            st.text_input("연락처", placeholder="010-0000-0000", key=field_key("phone"))
        with c2:
            set_widget_default("property_type", "아파트")
            st.radio("소유 구분", PROPERTY_TYPE_OPTIONS, horizontal=True, key=field_key("property_type"))
            set_widget_default("existing_dong", "")
            st.text_input("소유 동", placeholder="예: 73동", key=field_key("existing_dong"))
            set_widget_default("existing_ho", "")
            st.text_input("소유 호수", placeholder="예: 1201호", key=field_key("existing_ho"))
            default_size = get_data("current_size", "47.75평")
            if default_size not in CURRENT_SIZE_OPTIONS:
                default_size = "기타"
            set_widget_default("current_size", default_size)
            st.selectbox("현재 평형", CURRENT_SIZE_OPTIONS, key=field_key("current_size"))
            if st.session_state.get(field_key("current_size")) == "기타":
                set_widget_default("current_size_other", "")
                st.text_input("현재 평형 직접 입력", key=field_key("current_size_other"))

    elif page_no == 2:
        st.info("안내 페이지입니다. 내용을 확인한 뒤 다음 장으로 이동하세요.")

    elif page_no == 3:
        st.subheader("Q01 ~ Q03 입력")
        set_widget_default("family_plan", "입주 계획 있음")
        st.radio("Q01-1. 입주 계획 여부", FAMILY_PLAN_OPTIONS, horizontal=True, key=field_key("family_plan"))
        if st.session_state[field_key("family_plan")] == "입주 계획 있음":
            set_widget_default("family_count", 2)
            st.number_input("Q01-1. 입주 시 함께 거주하실 가족인원 수", min_value=1, max_value=20, step=1, key=field_key("family_count"))
        set_widget_default("plan_preference", PLAN_OPTIONS[0])
        st.radio("Q01-2. 희망하시는 평면", PLAN_OPTIONS, key=field_key("plan_preference"))
        set_widget_default("room_count", "4개")
        st.radio("Q01-3. 희망하시는 방의 개수", ROOM_OPTIONS, horizontal=True, key=field_key("room_count"))
        set_widget_default("household_split", "희망 안함")
        st.radio("Q02. 세대구분형 옵션 희망 여부", HOUSEHOLD_SPLIT_OPTIONS, horizontal=True, key=field_key("household_split"))

        st.markdown("**Q03. 평형 외 가장 중요하게 생각하시는 요소**")
        factors = rank_select("factor_rank", IMPORTANT_FACTORS, 5, False)
        validate_unique(factors, "Q03 중요 요소")

    elif page_no == 4:
        st.subheader("Q04. 현재 평형 확인 및 희망 평형 선택")
        st.caption("아래 종이 설문지의 표를 참고하여 희망 평형을 선택해 주세요.")
        default = get_data("hope_size", "48평형")
        if default not in HOPE_SIZE_OPTIONS:
            default = "48평형"
        set_widget_default("hope_size", default)
        st.radio("희망 평형", HOPE_SIZE_OPTIONS, key=field_key("hope_size"))

    elif page_no == 5:
        st.subheader("Q04. 희망 평형 계속")
        st.caption("앞 장에서 선택한 희망 평형이 그대로 유지됩니다. 필요하면 아래에서 다시 수정할 수 있습니다.")
        default = get_data("hope_size", st.session_state.get(field_key("hope_size"), "48평형"))
        if default not in HOPE_SIZE_OPTIONS:
            default = "48평형"
        set_widget_default("hope_size", default)
        st.radio("희망 평형", HOPE_SIZE_OPTIONS, key=field_key("hope_size"))

    elif page_no in [6, 7, 8, 9]:
        st.info("참고자료 페이지입니다. 내용을 확인한 뒤 다음 장으로 이동하세요.")

    elif page_no == 10:
        st.subheader("Q05 ~ Q06 입력")
        set_widget_default("parking", "2.5대 ~ 3대")
        st.radio("Q05. 희망하시는 세대당 주차대수", PARKING_OPTIONS, horizontal=True, key=field_key("parking"))
        if st.session_state[field_key("parking")] == "기타":
            set_widget_default("parking_other", "")
            st.text_input("주차대수 기타 의견", key=field_key("parking_other"))

        st.markdown("**Q06. 희망하시는 커뮤니티 시설**")
        community = rank_select("community_rank", COMMUNITY_OPTIONS, 5, True)
        validate_unique(community, "Q06 커뮤니티 시설")
        set_widget_default("community_other", "")
        st.text_input("커뮤니티 기타 의견", key=field_key("community_other"))

    elif page_no == 11:
        st.subheader("Q07 ~ Q08 입력")
        st.markdown("**Q07. 희망하시는 조경시설**")
        landscape = rank_select("landscape_rank", LANDSCAPE_OPTIONS, 5, True)
        validate_unique(landscape, "Q07 조경시설")
        set_widget_default("landscape_other", "")
        st.text_input("조경시설 기타 의견", key=field_key("landscape_other"))

        set_widget_default("semi_residential", [])
        st.multiselect("Q08. 희망하시는 준주거용지 특화계획시설", SEMI_RESIDENTIAL_OPTIONS, key=field_key("semi_residential"))
        if "기타" in st.session_state.get(field_key("semi_residential"), []):
            set_widget_default("semi_residential_other", "")
            st.text_input("준주거용지 기타 의견", key=field_key("semi_residential_other"))

    elif page_no == 12:
        st.subheader("마지막 의견 제출")
        st.caption("글로 표현하기 어려운 자료가 있으면 파일을 첨부할 수 있습니다. 첨부파일은 50MB 이하만 가능합니다.")
        set_widget_default("final_opinion", "")
        st.text_area("조합원님의 다양한 의견을 듣겠습니다", height=180, key=field_key("final_opinion"))
        uploaded = st.file_uploader("첨부파일 선택 50MB 이하", accept_multiple_files=False, key="uploaded_file_v06")
        if uploaded is not None:
            if uploaded.size > MAX_UPLOAD_BYTES:
                st.error("첨부파일은 50MB 이하만 가능합니다.")
            else:
                st.success(f"첨부파일 선택됨: {uploaded.name} / {uploaded.size / 1024 / 1024:.2f}MB")

        st.divider()
        if st.button("최종 의견 제출하기", type="primary", use_container_width=True):
            submit_survey()


def sanitize_filename(name):
    name = re.sub(r"[^가-힣a-zA-Z0-9_.-]+", "_", name or "attachment")
    return name[:120]


def upload_attachment(unit_key):
    uploaded = st.session_state.get("uploaded_file_v06")
    if uploaded is None:
        return {"attachment_path": None, "attachment_name": None, "attachment_type": None, "attachment_size": None}

    if uploaded.size > MAX_UPLOAD_BYTES:
        raise ValueError("첨부파일은 50MB 이하만 가능합니다.")

    sb = get_supabase()
    safe_name = sanitize_filename(uploaded.name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{unit_key}/{ts}_{safe_name}"
    file_bytes = uploaded.getvalue()

    sb.storage.from_(STORAGE_BUCKET).upload(
        path,
        file_bytes,
        file_options={
            "content-type": uploaded.type or "application/octet-stream",
            "upsert": "true",
        },
    )

    return {
        "attachment_path": path,
        "attachment_name": uploaded.name,
        "attachment_type": uploaded.type,
        "attachment_size": int(uploaded.size),
    }


def collect_payload():
    save_current_page()
    data = dict(st.session_state.survey_data)

    owner_name = normalize_text(data.get("owner_name"))
    dong = normalize_text(data.get("existing_dong"))
    ho = normalize_text(data.get("existing_ho"))
    if not owner_name or not dong or not ho:
        raise ValueError("성명, 소유 동, 소유 호수는 필수 입력입니다.")

    current_size = data.get("current_size")
    if current_size == "기타":
        current_size = data.get("current_size_other", "")
    data["current_size_final"] = current_size
    data["unit_key"] = make_unit_key(owner_name, dong, ho)
    return data


def get_existing_submission(unit_key):
    sb = get_supabase()
    res = (
        sb.table(SUBMISSIONS_TABLE)
        .select("id, edit_count, unit_key, owner_name, existing_dong, existing_ho")
        .eq("unit_key", unit_key)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def insert_submission(payload):
    sb = get_supabase()
    now = datetime.now().isoformat(timespec="seconds")
    payload = {**payload, "created_at": now, "updated_at": None, "edit_count": 0, "consent": True}
    sb.table(SUBMISSIONS_TABLE).insert(payload).execute()


def update_submission(existing, payload):
    if int(existing.get("edit_count", 0)) >= 1:
        raise ValueError("이미 1회 수정하셨습니다. 추가 수정은 관리자에게 문의해 주세요.")

    sb = get_supabase()
    now = datetime.now().isoformat(timespec="seconds")
    payload = {**payload, "updated_at": now, "edit_count": int(existing.get("edit_count", 0)) + 1}
    sb.table(SUBMISSIONS_TABLE).update(payload).eq("id", existing["id"]).execute()
    sb.table(EDIT_LOGS_TABLE).insert({
        "submission_id": existing["id"],
        "edited_at": now,
        "old_data": str(existing),
        "new_data": str(payload),
    }).execute()


def submit_survey():
    try:
        payload = collect_payload()
        attachment_info = upload_attachment(payload["unit_key"])
        payload.update(attachment_info)

        existing = get_existing_submission(payload["unit_key"])
        if existing:
            update_submission(existing, payload)
            st.success("수정 제출이 완료되었습니다.")
        else:
            insert_submission(payload)
            st.success("최종 의견 제출이 완료되었습니다.")
        st.session_state.submitted_ok = True
        st.balloons()
    except Exception as e:
        st.error("저장 중 오류가 발생했습니다. 아래 오류 내용을 알려주세요.")
        st.code(str(e))


def safe_download_csv(df):
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def read_all_submissions():
    sb = get_supabase()
    res = sb.table(SUBMISSIONS_TABLE).select("*").order("created_at", desc=True).execute()
    return pd.DataFrame(res.data or [])


def render_admin():
    st.subheader("관리자 통계")
    password = st.text_input("관리자 비밀번호", type="password")
    if not password:
        st.info("관리자 비밀번호를 입력해 주세요.")
        return
    if not hmac.compare_digest(password, ADMIN_PASSWORD):
        st.error("비밀번호가 맞지 않습니다.")
        return

    try:
        df = read_all_submissions()
    except Exception as e:
        st.error("DB 조회 중 오류가 발생했습니다.")
        st.code(str(e))
        return

    if df.empty:
        st.warning("아직 제출된 응답이 없습니다.")
        return

    st.success("관리자 인증 완료")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체 제출", f"{len(df):,}건")
    c2.metric("첨부파일", f"{df['attachment_path'].notna().sum():,}건" if "attachment_path" in df.columns else "0건")
    c3.metric("희망평형 종류", f"{df['hope_size'].nunique():,}개" if "hope_size" in df.columns else "0개")
    c4.metric("수정 제출", f"{(pd.to_numeric(df.get('edit_count', 0), errors='coerce').fillna(0) > 0).sum():,}건")

    st.subheader("희망 평형")
    if "hope_size" in df.columns:
        tab = df["hope_size"].fillna("미응답").replace("", "미응답").value_counts().rename_axis("희망평형").reset_index(name="응답 수")
        tab["비율"] = (tab["응답 수"] / len(df) * 100).round(1).astype(str) + "%"
        st.dataframe(tab, use_container_width=True)

    st.subheader("현재 평형 × 희망 평형")
    if "current_size_final" in df.columns and "hope_size" in df.columns:
        st.dataframe(pd.crosstab(df["current_size_final"], df["hope_size"]), use_container_width=True)

    st.subheader("원본 데이터")
    st.dataframe(df, use_container_width=True)
    st.download_button(
        "CSV 다운로드",
        data=safe_download_csv(df),
        file_name="apgujeong3_survey_raw_v06.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.caption("첨부파일은 Supabase Storage의 survey-attachments-v06 버킷에 저장됩니다. CSV에는 파일 경로가 기록됩니다.")


def render_survey():
    st.markdown("### 통합심의 건축계획 수립을 위한 3차 설문조사")
    st.caption("종이 설문지를 한 장씩 넘기듯이 진행합니다. 이전/다음 장으로 이동해도 입력값은 유지됩니다.")

    progress = st.progress(st.session_state.page_idx / PAGE_COUNT)
    page_image(st.session_state.page_idx)

    with st.container(border=True):
        render_inputs_for_page(st.session_state.page_idx)

    nav_buttons()


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🏙️", layout="wide")
    init_state()
    st.title(APP_TITLE)

    tab1, tab2 = st.tabs(["설문 작성", "관리자"])
    with tab1:
        render_survey()
    with tab2:
        render_admin()


if __name__ == "__main__":
    main()
