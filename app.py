
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
SUBMISSIONS_TABLE = "survey_submissions_v07"
EDIT_LOGS_TABLE = "survey_edit_logs_v07"
STORAGE_BUCKET = "survey-attachments-v07"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
PAGE_COUNT = 12
ASSET_DIR = Path(__file__).parent / "assets"

CURRENT_SIZE_OPTIONS = [
    "31.72평 / 61,62,63,64동", "32.10평 / 203,204,205,206동", "34.56평 / 71,72동",
    "35.42평 / 202동", "36.74평 / 208,209,210,211동",
    "43.29평 / 31,32,33동", "43.24평 / 51~56동", "47.75평 / 73,74,81,83,84,87동",
    "50.40평 / 201동", "51.96평 / 75,77,78,82,86동", "52.92평 / 24,25동",
    "54.03평 / 20,21,22,23동", "64.52평 / 12,13동", "64.55평 / 10,11동",
    "64.99평 / 79,80,85동", "80.30평 / 76동", "87.75평 / 65동", "92.01평 / 65동",
    "빌라트 72.79평", "빌라트 75.98평", "빌라트 86.89평", "빌라트 92.26평", "기타"
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
    "거실, 주방의 면적이 다소 줄어도 방의 개수가 많은 평면",
    "방의 개수보다 거실, 주방의 면적이 넓은 평면",
]
ROOM_OPTIONS = ["3개", "4개", "5개", "6개 이상"]
HOUSEHOLD_SPLIT_OPTIONS = ["희망함", "희망 안함"]
IMPORTANT_FACTORS = ["조망", "위치(역세권, 학세권, 숲세권 등)", "분담금", "향", "층수"]
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
    "하이엔드 오피스텔", "시니어 특화형 공동주택", "교육시설(비인가 국제학교)", "하이엔드 브랜드 상업시설", "기타"
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
SUPABASE_KEY = str(get_secret("SUPABASE_SERVICE_ROLE_KEY") or get_secret("SUPABASE_ANON_KEY") or "").strip().strip('"').strip("'")
ADMIN_PASSWORD = get_secret("SURVEY_ADMIN_PASSWORD", "admin123")


@st.cache_resource
def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Supabase 연결 정보가 없습니다. Streamlit Secrets를 확인해 주세요.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def css():
    st.markdown("""
    <style>
    .block-container {max-width: 980px; padding-top: 1.2rem;}
    .paper {
        background: #fff;
        border: 1.8px solid #222;
        border-radius: 4px;
        padding: 24px 30px;
        box-shadow: 0 3px 12px rgba(0,0,0,0.08);
        margin: 8px 0 18px 0;
    }
    .orange-title {
        background:#f36c21;
        color:white;
        font-weight:800;
        font-size: 1.35rem;
        text-align:center;
        padding: 14px;
        border-radius: 14px 14px 0 0;
        margin:-24px -30px 20px -30px;
    }
    .section-title {color:#e96518; font-weight:800; font-size:1.35rem; margin-bottom:10px; border-left:5px solid #e96518; padding-left:10px;}
    .q-label {display:inline-block; background:#333; color:#f36c21; font-weight:900; padding:8px 18px; margin-right:10px; font-size:1.15rem;}
    .subtle-box {border:1px solid #555; padding:14px 16px; background:#fafafa; margin:8px 0 16px 0;}
    .small-red {color:#e22; font-weight:700;}
    .grid-note {font-size:0.92rem; color:#555;}
    div[data-testid="stRadio"] label {font-size: 1rem;}
    .stButton button {border-radius: 10px;}
    </style>
    """, unsafe_allow_html=True)


def init_state():
    if "page_idx" not in st.session_state:
        st.session_state.page_idx = 1
    if "data" not in st.session_state:
        st.session_state.data = {}
    if "submitted_ok" not in st.session_state:
        st.session_state.submitted_ok = False


def normalize_text(x):
    return str(x or "").strip().replace(" ", "")




def k(name): return f"f_{name}"
def get(name, default=None): return st.session_state.data.get(name, default)
def set_default(name, default=None):
    key = k(name)
    if key not in st.session_state:
        st.session_state[key] = get(name, default)
def save(names):
    for name in names:
        if k(name) in st.session_state:
            st.session_state.data[name] = st.session_state[k(name)]


FIELDS = [
    "owner_name","signature_name","address","phone","property_type","existing_dong","existing_ho","current_size","current_size_other",
    "family_plan","family_count","plan_preference","room_count","household_split",
    "factor_rank_1","factor_rank_2","factor_rank_3","factor_rank_4","factor_rank_5",
    "hope_size","parking","parking_other",
    "community_rank_1","community_rank_2","community_rank_3","community_rank_4","community_rank_5","community_other",
    "landscape_rank_1","landscape_rank_2","landscape_rank_3","landscape_rank_4","landscape_rank_5","landscape_other",
    "semi_residential","semi_residential_other","final_opinion"
]


def save_all(): save(FIELDS)


def go(page):
    save_all()
    st.session_state.page_idx = max(1, min(PAGE_COUNT, int(page)))
    st.rerun()


def nav():
    st.divider()
    c1,c2,c3 = st.columns([1,1,1])
    with c1:
        if st.session_state.page_idx > 1 and st.button("← 이전 장", use_container_width=True):
            go(st.session_state.page_idx - 1)
    with c2:
        st.markdown(f"<div style='text-align:center;padding-top:0.55rem;'><b>{st.session_state.page_idx} / {PAGE_COUNT}</b></div>", unsafe_allow_html=True)
    with c3:
        if st.session_state.page_idx < PAGE_COUNT and st.button("다음 장 →", type="primary", use_container_width=True):
            go(st.session_state.page_idx + 1)


def rank_select(prefix, options, allow_skip=False):
    opts = (["선택 안함"] + options) if allow_skip else options
    cols = st.columns(5)
    vals = []
    for i in range(1,6):
        name = f"{prefix}_{i}"
        default = get(name, opts[0])
        if default not in opts: default = opts[0]
        set_default(name, default)
        with cols[i-1]:
            vals.append(st.selectbox(f"{i}순위", opts, key=k(name)))
    vals2 = [v for v in vals if v != "선택 안함"]
    if len(vals2) != len(set(vals2)):
        st.error("순위는 중복 없이 선택해 주세요.")
    return vals


def page_image(n):
    path = ASSET_DIR / f"page_{n:02d}.png"
    if path.exists(): st.image(str(path), use_container_width=True)
    else: st.info("이 페이지는 종이 설문지와 같은 형태로 웹에서 재구성했습니다.")


def page1():
    st.markdown("<div class='paper'><div class='orange-title'>- 아파트 조합원 설문조사 -</div>", unsafe_allow_html=True)
    st.markdown("### 「통합심의 건축계획 수립을 위한 3차 설문조사」")
    st.markdown("""
    본 설문조사는 서울시 통합심의 신청을 위한 건축계획 수립을 목적으로 진행합니다.  
    조합원 여러분의 의견을 파악하여 설계에 반영하고자 하오니 성실히 작성하여 주시기 바랍니다.
    """)
    st.markdown("<div class='subtle-box'><b>■ 소유주 인적사항</b></div>", unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        set_default("owner_name",""); st.text_input("성명", key=k("owner_name"))
        set_default("address",""); st.text_input("주소", key=k("address"))
        set_default("phone",""); st.text_input("연락처", key=k("phone"))
    with c2:
        set_default("property_type","아파트"); st.radio("소유 구분", PROPERTY_TYPE_OPTIONS, horizontal=True, key=k("property_type"))
        set_default("existing_dong",""); st.text_input("소유 동", key=k("existing_dong"), placeholder="예: 73동")
        set_default("existing_ho",""); st.text_input("소유 호수", key=k("existing_ho"), placeholder="예: 1201호")
        default = get("current_size", "47.75평 / 73,74,81,83,84,87동")
        if default not in CURRENT_SIZE_OPTIONS: default = "기타"
        set_default("current_size", default)
        st.selectbox("현재 평형", CURRENT_SIZE_OPTIONS, key=k("current_size"))
        if st.session_state[k("current_size")] == "기타":
            set_default("current_size_other",""); st.text_input("현재 평형 직접 입력", key=k("current_size_other"))
    st.markdown("</div>", unsafe_allow_html=True)


def page3():
    st.markdown("<div class='paper'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>희망평형 관련 설문</div>", unsafe_allow_html=True)
    st.markdown("<span class='q-label'>Q 01</span> <b>재건축 후 입주 시 함께 거주하실 가족인원 수와 희망하시는 평면 및 방의 개수</b>", unsafe_allow_html=True)
    set_default("family_plan", "입주 계획 있음")
    st.radio("1) 입주 계획 여부", FAMILY_PLAN_OPTIONS, horizontal=True, key=k("family_plan"))
    if st.session_state[k("family_plan")] == "입주 계획 있음":
        set_default("family_count", 2)
        st.number_input("입주 시 함께 거주하실 가족인원 수", min_value=1, max_value=20, step=1, key=k("family_count"))
    set_default("plan_preference", PLAN_OPTIONS[0])
    st.radio("2) 희망하시는 평면", PLAN_OPTIONS, key=k("plan_preference"))
    set_default("room_count", "4개")
    st.radio("3) 희망하시는 방의 개수", ROOM_OPTIONS, horizontal=True, key=k("room_count"))

    st.markdown("<br><span class='q-label'>Q 02</span> <b>‘세대구분형 옵션’ 희망 여부</b> <span class='small-red'>(출입구 분리, 분양면적 60평형 이상 적용 가능)</span>", unsafe_allow_html=True)
    set_default("household_split", "희망 안함")
    st.radio("세대구분형 옵션", HOUSEHOLD_SPLIT_OPTIONS, horizontal=True, key=k("household_split"))

    st.markdown("<br><span class='q-label'>Q 03</span> <b>평형 외에 가장 중요하게 생각하시는 요소</b>", unsafe_allow_html=True)
    rank_select("factor_rank", IMPORTANT_FACTORS)
    st.markdown("<div class='grid-note'>① 조망　② 위치(역세권, 학세권, 숲세권 등)　③ 분담금　④ 향　⑤ 층수</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def page4_5(n):
    st.markdown("<div class='paper'>", unsafe_allow_html=True)
    st.markdown("<span class='q-label'>Q 04</span> <b>추정분담금, 이주비 이자 및 보유세 추정액 등을 참고하여 희망하시는 평형을 체크해 주시기 바랍니다.</b>", unsafe_allow_html=True)
    st.markdown("<div class='subtle-box'>본 설문은 조합원의 수요를 조사하여 건축계획에 반영하기 위한 목적으로 사용됩니다.<br>희망하시는 평형 1곳에만 선택해 주십시오. <span class='small-red'>(복수체크불가)</span></div>", unsafe_allow_html=True)
    st.markdown("#### 현재 평형")
    set_default("current_size", get("current_size", "47.75평 / 73,74,81,83,84,87동"))
    st.selectbox("현재 평형 확인", CURRENT_SIZE_OPTIONS, key=k("current_size"))
    if st.session_state[k("current_size")] == "기타":
        set_default("current_size_other",""); st.text_input("현재 평형 직접 입력", key=k("current_size_other"))
    st.markdown("#### 희망 평형")
    set_default("hope_size", get("hope_size", "48평형"))
    st.radio("원하는 평형 1곳 선택", HOPE_SIZE_OPTIONS, key=k("hope_size"))
    st.markdown("</div>", unsafe_allow_html=True)


def page10():
    st.markdown("<div class='paper'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>주차대수, 커뮤니티, 조경, 준주거용지 특화계획 설문</div>", unsafe_allow_html=True)
    st.markdown("<span class='q-label'>Q 05</span> <b>희망하시는 세대당 주차대수를 체크해 주십시오.</b>", unsafe_allow_html=True)
    set_default("parking", "2.5대 ~ 3대")
    st.radio("세대당 주차대수", PARKING_OPTIONS, horizontal=True, key=k("parking"))
    if st.session_state[k("parking")] == "기타":
        set_default("parking_other",""); st.text_input("기타 주차대수", key=k("parking_other"))

    st.markdown("<br><span class='q-label'>Q 06</span> <b>희망하시는 커뮤니티 시설을 선호하는 순서대로 선택해 주십시오.</b>", unsafe_allow_html=True)
    rank_select("community_rank", COMMUNITY_OPTIONS, allow_skip=True)
    set_default("community_other",""); st.text_input("기타 커뮤니티 시설", key=k("community_other"))
    st.markdown("</div>", unsafe_allow_html=True)


def page11():
    st.markdown("<div class='paper'>", unsafe_allow_html=True)
    st.markdown("<span class='q-label'>Q 07</span> <b>희망하시는 조경시설을 선호하는 순서대로 선택해 주십시오.</b>", unsafe_allow_html=True)
    rank_select("landscape_rank", LANDSCAPE_OPTIONS, allow_skip=True)
    set_default("landscape_other",""); st.text_input("기타 조경시설", key=k("landscape_other"))

    st.markdown("<br><span class='q-label'>Q 08</span> <b>희망하시는 준주거용지 특화계획시설에 체크해주십시오.</b>", unsafe_allow_html=True)
    set_default("semi_residential", [])
    st.multiselect("준주거용지 특화계획시설", SEMI_RESIDENTIAL_OPTIONS, key=k("semi_residential"))
    if "기타" in st.session_state.get(k("semi_residential"), []):
        set_default("semi_residential_other",""); st.text_input("기타 시설", key=k("semi_residential_other"))
    st.markdown("<div class='grid-note'>주1) 시니어 특화형 공동주택: 다양한 의료 서비스와 커뮤니티시설, 주거 공간 구성 특징 반영<br>주2) 준주거용지 허용용도 이외의 용도 추가 시 정비계획 변경 절차 필요</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def page12():
    st.markdown("<div class='paper'>", unsafe_allow_html=True)
    st.markdown("<div class='orange-title'>조합원님의 다양한 의견을 듣겠습니다!</div>", unsafe_allow_html=True)
    set_default("final_opinion","")
    st.text_area("마지막 의견 제출", height=220, key=k("final_opinion"), placeholder="글로 의견을 입력해 주세요.")
    uploaded = st.file_uploader("파일 첨부 50MB 이하", accept_multiple_files=False, key="upload_file")
    if uploaded:
        if uploaded.size > MAX_UPLOAD_BYTES:
            st.error("첨부파일은 50MB 이하만 가능합니다.")
        else:
            st.success(f"첨부파일 선택됨: {uploaded.name} / {uploaded.size/1024/1024:.2f}MB")
    st.markdown("</div>", unsafe_allow_html=True)
    if st.button("최종 의견 제출하기", type="primary", use_container_width=True):
        submit()


def image_page(n):
    page_image(n)


def sanitize_filename(name):
    """
    Supabase Storage object key는 한글/공백/특수문자가 섞이면 InvalidKey가 날 수 있습니다.
    파일명은 DB에 원본명으로 따로 저장하고, Storage 저장용 key는 ASCII만 사용합니다.
    """
    name = str(name or "attachment")
    suffix = Path(name).suffix.lower()
    if not suffix or len(suffix) > 10:
        suffix = ".bin"
    # 확장자도 혹시 특수문자가 있으면 정리
    suffix = re.sub(r"[^a-z0-9.]", "", suffix)
    return suffix


def upload_attachment(unit_key):
    uploaded = st.session_state.get("upload_file")
    if not uploaded:
        return {"attachment_path": None, "attachment_name": None, "attachment_type": None, "attachment_size": None}

    if uploaded.size > MAX_UPLOAD_BYTES:
        raise ValueError("첨부파일은 50MB 이하만 가능합니다.")

    sb = get_supabase()
    ext = sanitize_filename(uploaded.name)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    short_key = re.sub(r"[^a-zA-Z0-9]", "", str(unit_key))[:16]

    # Storage용 key는 ASCII/숫자/언더바/점만 사용합니다.
    # 원본 파일명은 attachment_name 컬럼에 따로 저장합니다.
    path = f"att_{short_key}_{ts}{ext}"

    try:
        sb.storage.from_(STORAGE_BUCKET).upload(
            path,
            uploaded.getvalue(),
            file_options={
                "content-type": uploaded.type or "application/octet-stream",
                "x-upsert": "true",
            },
        )
    except Exception as e:
        raise ValueError(f"첨부파일 저장 오류: {e}")

    return {
        "attachment_path": path,
        "attachment_name": uploaded.name,
        "attachment_type": uploaded.type,
        "attachment_size": int(uploaded.size),
    }

def current_size_final(data):
    return data.get("current_size_other") if data.get("current_size") == "기타" else data.get("current_size")


def payload():
    save_all()
    data = dict(st.session_state.data)
    if not normalize_text(data.get("owner_name")) or not normalize_text(data.get("existing_dong")) or not normalize_text(data.get("existing_ho")):
        raise ValueError("성명, 소유 동, 소유 호수는 필수 입력입니다.")
    data["current_size_final"] = current_size_final(data)
    data["unit_key"] = hashlib.sha256("|".join([normalize_text(data.get("owner_name")), normalize_text(data.get("existing_dong")), normalize_text(data.get("existing_ho"))]).encode("utf-8")).hexdigest()
    return data


def get_existing(unit_key):
    res = get_supabase().table(SUBMISSIONS_TABLE).select("id, edit_count, unit_key").eq("unit_key", unit_key).limit(1).execute()
    return res.data[0] if res.data else None


def submit():
    try:
        p = payload()
        p.update(upload_attachment(p["unit_key"]))
        sb = get_supabase()
        old = get_existing(p["unit_key"])
        now = datetime.now().isoformat(timespec="seconds")
        if old:
            if int(old.get("edit_count",0)) >= 1:
                raise ValueError("이미 1회 수정하셨습니다. 추가 수정은 관리자에게 문의해 주세요.")
            p.update({"updated_at": now, "edit_count": int(old.get("edit_count",0))+1})
            sb.table(SUBMISSIONS_TABLE).update(p).eq("id", old["id"]).execute()
            sb.table(EDIT_LOGS_TABLE).insert({"submission_id": old["id"], "edited_at": now, "old_data": str(old), "new_data": str(p)}).execute()
            st.success("수정 제출이 완료되었습니다.")
        else:
            p.update({"created_at": now, "updated_at": None, "edit_count": 0, "consent": True})
            sb.table(SUBMISSIONS_TABLE).insert(p).execute()
            st.success("최종 의견 제출이 완료되었습니다.")
        st.session_state.submitted_ok = True
        st.balloons()
    except Exception as e:
        st.error("저장 중 오류가 발생했습니다. 아래 오류 내용을 알려주세요.")
        st.code(str(e))


def read_all():
    return pd.DataFrame(get_supabase().table(SUBMISSIONS_TABLE).select("*").order("created_at", desc=True).execute().data or [])


def render_admin():
    st.subheader("관리자")
    pw = st.text_input("관리자 비밀번호", type="password")
    if not pw:
        st.info("관리자 비밀번호를 입력하세요.")
        return
    if not hmac.compare_digest(pw, ADMIN_PASSWORD):
        st.error("비밀번호가 맞지 않습니다.")
        return
    try:
        df = read_all()
    except Exception as e:
        st.error("DB 조회 오류")
        st.code(str(e))
        return
    if df.empty:
        st.warning("아직 제출된 응답이 없습니다.")
        return
    c1,c2,c3 = st.columns(3)
    c1.metric("제출 수", len(df))
    c2.metric("첨부파일", int(df["attachment_path"].notna().sum()) if "attachment_path" in df.columns else 0)
    c3.metric("희망평형 종류", df["hope_size"].nunique() if "hope_size" in df.columns else 0)
    if "hope_size" in df.columns:
        st.subheader("희망 평형")
        st.dataframe(df["hope_size"].fillna("미응답").value_counts().rename_axis("희망평형").reset_index(name="응답 수"), use_container_width=True)
    if "current_size_final" in df.columns and "hope_size" in df.columns:
        st.subheader("현재 평형 × 희망 평형")
        st.dataframe(pd.crosstab(df["current_size_final"], df["hope_size"]), use_container_width=True)
    st.subheader("원본 데이터")
    st.dataframe(df, use_container_width=True)
    st.download_button("CSV 다운로드", data=df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), file_name="apgujeong3_survey_v07.csv", mime="text/csv", use_container_width=True)


def render_page():
    st.markdown("#### 종이 설문지 재현형 v0.7.3.3.2")
    st.caption("한 장씩 넘기듯 진행합니다. 이전/다음 장을 오가도 입력값은 유지됩니다.")
    st.progress(st.session_state.page_idx / PAGE_COUNT)
    n = st.session_state.page_idx
    if n == 1: page1()
    elif n == 2: image_page(2)
    elif n == 3: page3()
    elif n in [4,5]: page4_5(n)
    elif n in [6,7,8,9]: image_page(n)
    elif n == 10: page10()
    elif n == 11: page11()
    elif n == 12: page12()
    nav()


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🏙️", layout="wide")
    css()
    init_state()
    st.title(APP_TITLE)
    tab1, tab2 = st.tabs(["설문 작성", "관리자"])
    with tab1: render_page()
    with tab2: render_admin()

if __name__ == "__main__":
    main()
