
import os, hmac, hashlib
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client

APP_TITLE = "압구정3구역 조합원 희망평형·위치 조사"
SUBMISSIONS_TABLE = "survey_submissions_v05"
EDIT_LOGS_TABLE = "survey_edit_logs_v05"

CURRENT_SIZE_OPTIONS = ["30평형대","31.72평","32.10평","34.56평","35.42평","36.74평","40평형대","43.29평","43.24평","47.75평","50평형대","50.40평","51.96평","52.92평","54.03평","60평형대","64.52평","64.55평","64.99평","80평형대","80.30평","87.75평","92.01평","빌라트","72.79평","75.98평","86.89평","92.26평","기타"]
HOPE_SIZE_OPTIONS = ["25평형","36평형","43평형","48평형","53평형","58평형","65평형","75평형","85평형","90평형","준펜트하우스 90평형","준펜트하우스 95평형","펜트하우스 90평형","펜트하우스 95평형","펜트하우스 105평형"]
FAMILY_PLAN_OPTIONS = ["입주 계획 있음", "입주 계획 없음(임대 등)"]
PLAN_OPTIONS = ["거실·주방 면적이 다소 줄어도 방의 개수가 많은 평면", "방의 개수보다 거실·주방 면적이 넓은 평면"]
ROOM_OPTIONS = ["3개", "4개", "5개", "6개 이상"]
HOUSEHOLD_SPLIT_OPTIONS = ["희망함", "희망 안함"]
IMPORTANT_FACTORS = ["조망", "위치(역세권·학세권·숲세권 등)", "분담금", "향", "층수"]
PARKING_OPTIONS = ["2.5대", "2.5대 ~ 3대", "3대 초과", "기타"]
COMMUNITY_OPTIONS = ["다목적체육관","실내수영장","실내골프연습장","스크린골프","인도어 골프장","피트니스센터","사우나","클라이밍","실내테니스장","볼링장","프라이빗피트니스","프라이빗 사우나","펫 라운지","펫 호텔","시니어살롱(노인정)","시니어케어센터","실내놀이터","스터디룸","도서관","아트 수장고","게스트하우스","올데이다이닝","파티룸","웰컴센터","소공연장","공유오피스","주민카페","스카이커뮤니티(게스트하우스)","스카이커뮤니티(카페&라운지)","스카이커뮤니티(피트니스)"]
LANDSCAPE_OPTIONS = ["산책로","사계절 정원","프라이빗 정원","대형 중앙공원","예술·조각정원","숲속 정원","사계절실내온실","압구정지 갤러리","티하우스","명상 공간","캠핑장","리조트형수경시설","생태 연못","바닥분수","어린이 놀이터","펫 놀이터","야외 공연장","한강전망대"]
SEMI_RESIDENTIAL_OPTIONS = ["하이엔드 오피스텔", "시니어 특화형 공동주택", "교육시설(비인가 국제학교)", "하이엔드 브랜드 상업시설", "기타"]

def get_secret(name, default=""):
    try:
        if name in st.secrets: return str(st.secrets[name])
    except Exception: pass
    return os.getenv(name, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_SERVICE_ROLE_KEY") or get_secret("SUPABASE_ANON_KEY")
ADMIN_PASSWORD = get_secret("SURVEY_ADMIN_PASSWORD", "admin123")

@st.cache_resource
def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Supabase 연결 정보가 없습니다. Streamlit Secrets를 확인해 주세요."); st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def normalize_text(x): return str(x).strip().replace(" ", "")
def make_unit_key(name, dong, ho):
    raw = "|".join([normalize_text(name), normalize_text(dong), normalize_text(ho)])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def read_all_submissions():
    res = get_supabase().table(SUBMISSIONS_TABLE).select("*").order("created_at", desc=True).execute()
    return pd.DataFrame(res.data or [])

def get_submission_by_key(unit_key):
    res = get_supabase().table(SUBMISSIONS_TABLE).select("id,edit_count,unit_key,name,existing_dong,existing_ho,existing_size,hope_size").eq("unit_key", unit_key).limit(1).execute()
    return res.data[0] if res.data else None

def insert_submission(data):
    payload = {"created_at": datetime.now().isoformat(timespec="seconds"), "updated_at": None, "edit_count": 0, "consent": True, **data}
    get_supabase().table(SUBMISSIONS_TABLE).insert(payload).execute()

def update_submission(existing, data):
    if int(existing.get("edit_count", 0)) >= 1: return False, "이미 1회 수정하셨습니다. 추가 수정은 관리자에게 문의해 주세요."
    payload = {"updated_at": datetime.now().isoformat(timespec="seconds"), "edit_count": int(existing.get("edit_count", 0)) + 1, **data}
    for k in ["name","existing_dong","existing_ho","existing_size","unit_key"]: payload.pop(k, None)
    sb = get_supabase()
    sb.table(SUBMISSIONS_TABLE).update(payload).eq("id", existing["id"]).execute()
    sb.table(EDIT_LOGS_TABLE).insert({"submission_id": existing["id"], "edited_at": datetime.now().isoformat(timespec="seconds"), "old_data": str(existing), "new_data": str(data)}).execute()
    return True, "수정이 완료되었습니다."

def safe_download_csv(df): return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

def init_state():
    if "step" not in st.session_state: st.session_state.step = 1
    if "verified" not in st.session_state: st.session_state.verified = {}

def go_step(n): st.session_state.step = n; st.rerun()

def check_unique_rank(values, label):
    vals = [v for v in values if v and v != "선택 안함"]
    return (len(vals) == len(set(vals)), f"{label} 순위는 중복 없이 선택해 주세요.")

def render_header_notice():
    st.markdown("""본 조사는 조합원들의 희망 평형·평면·커뮤니티·조경·준주거용지 특화계획 수요를 파악하기 위한 온라인 의견수렴 조사입니다.\n\n**공식 분양신청 또는 동·호수 배정을 의미하지 않습니다.**  \n결과는 개인 식별이 불가능한 통계 형태로만 활용됩니다.""")
    st.info("설문은 대부분 클릭 방식으로 구성되어 있으며, 꼭 필요한 항목만 직접 입력하도록 만들었습니다.")

def render_step1():
    st.subheader("1단계. 조합원 확인")
    st.caption("성명, 기존 동·호수, 현재 평형만 입력한 뒤 다음 단계로 넘어갑니다.")
    consent = st.checkbox("개인정보 수집·이용 및 통계 활용에 동의합니다.", value=False)
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("성명", placeholder="예: 홍길동")
        existing_dong = st.text_input("소유 동", placeholder="예: 73동")
    with c2:
        existing_ho = st.text_input("소유 호수", placeholder="예: 1201호")
        existing_size = st.selectbox("현재 평형", CURRENT_SIZE_OPTIONS, index=9)
    current_size_other = st.text_input("현재 평형 직접 입력", placeholder="예: 48평") if existing_size == "기타" else ""
    if st.button("다음으로", type="primary", use_container_width=True):
        if not consent: st.error("개인정보 수집·이용에 동의해야 다음 단계로 진행할 수 있습니다."); return
        if not all([name.strip(), existing_dong.strip(), existing_ho.strip(), existing_size]): st.error("성명, 동, 호수, 현재 평형을 모두 입력해 주세요."); return
        if existing_size == "기타" and not current_size_other.strip(): st.error("현재 평형을 직접 입력해 주세요."); return
        st.session_state.verified = {"name": name.strip(), "existing_dong": existing_dong.strip(), "existing_ho": existing_ho.strip(), "existing_size": current_size_other.strip() if existing_size == "기타" else existing_size, "unit_key": make_unit_key(name, existing_dong, existing_ho)}
        go_step(2)

def rank_selectors(title, options, prefix, count=5, allow_skip=False):
    st.markdown(f"**{title}**")
    cols = st.columns(count); selected = []
    select_options = (["선택 안함"] + options) if allow_skip else options
    for i in range(count):
        with cols[i]: selected.append(st.selectbox(f"{i+1}순위", select_options, key=f"{prefix}_{i}"))
    return selected

def render_step2():
    v = st.session_state.verified
    st.subheader("2단계. 설문조사")
    st.caption(f"확인 정보: {v['name']} / {v['existing_dong']} {v['existing_ho']} / 현재 {v['existing_size']}")
    with st.expander("Q01. 입주 가족인원·희망 평면·방 개수", expanded=True):
        family_plan = st.radio("입주 계획 여부", FAMILY_PLAN_OPTIONS, horizontal=True)
        family_count = st.number_input("입주 시 함께 거주하실 가족인원 수", 1, 20, 2, 1) if family_plan == "입주 계획 있음" else None
        plan_preference = st.radio("희망하시는 평면", PLAN_OPTIONS)
        room_count = st.radio("희망하시는 방의 개수", ROOM_OPTIONS, horizontal=True)
    with st.expander("Q02. 세대구분형 옵션 희망 여부", expanded=True):
        st.caption("출입구 분리를 위해 분양면적 60평형 이상만 적용 가능합니다.")
        household_split = st.radio("세대구분형 옵션", HOUSEHOLD_SPLIT_OPTIONS, horizontal=True)
    with st.expander("Q03. 평형 외 가장 중요하게 생각하는 요소", expanded=True):
        factor_rank = rank_selectors("중요한 순서대로 선택해 주세요.", IMPORTANT_FACTORS, "factor", 5)
    with st.expander("Q04. 희망 평형", expanded=True):
        st.caption("원하는 평형 1곳을 선택해 주세요.")
        hope_size = st.radio("희망 평형", HOPE_SIZE_OPTIONS)
    with st.expander("Q05. 희망 세대당 주차대수", expanded=False):
        parking = st.radio("희망하시는 세대당 주차대수", PARKING_OPTIONS, horizontal=True)
        parking_other = st.text_input("주차대수 기타 의견", placeholder="예: 3.5대 이상") if parking == "기타" else ""
    with st.expander("Q06. 희망 커뮤니티 시설", expanded=False):
        community_rank = rank_selectors("선호하는 순서대로 선택해 주세요.", COMMUNITY_OPTIONS, "community", 5, True)
        community_other = st.text_input("커뮤니티 기타 의견", placeholder="예: 의료상담실, 소규모 강의실 등")
    with st.expander("Q07. 희망 조경시설", expanded=False):
        landscape_rank = rank_selectors("선호하는 순서대로 선택해 주세요.", LANDSCAPE_OPTIONS, "landscape", 5, True)
        landscape_other = st.text_input("조경시설 기타 의견", placeholder="예: 반려견 산책로 등")
    with st.expander("Q08. 준주거용지 특화계획시설", expanded=False):
        semi_residential = st.multiselect("희망하시는 시설을 선택해 주세요.", SEMI_RESIDENTIAL_OPTIONS)
        semi_residential_other = st.text_input("준주거용지 기타 의견", placeholder="희망 시설을 입력해 주세요.") if "기타" in semi_residential else ""
    memo = st.text_area("추가 의견", placeholder="선택 사항입니다.", height=100)
    st.divider(); c1, c2 = st.columns(2)
    with c1:
        if st.button("이전 단계로", use_container_width=True): go_step(1)
    with c2:
        if st.button("제출 내용 확인", type="primary", use_container_width=True):
            for vals, label in [(factor_rank,"중요 요소"),(community_rank,"커뮤니티"),(landscape_rank,"조경시설")]:
                ok, msg = check_unique_rank(vals, label)
                if not ok: st.error(msg); return
            st.session_state.survey = {"family_plan":family_plan,"family_count":int(family_count) if family_count else None,"plan_preference":plan_preference,"room_count":room_count,"household_split":household_split,"factor_rank_1":factor_rank[0],"factor_rank_2":factor_rank[1],"factor_rank_3":factor_rank[2],"factor_rank_4":factor_rank[3],"factor_rank_5":factor_rank[4],"hope_size":hope_size,"parking":parking,"parking_other":parking_other.strip(),"community_rank_1":community_rank[0],"community_rank_2":community_rank[1],"community_rank_3":community_rank[2],"community_rank_4":community_rank[3],"community_rank_5":community_rank[4],"community_other":community_other.strip(),"landscape_rank_1":landscape_rank[0],"landscape_rank_2":landscape_rank[1],"landscape_rank_3":landscape_rank[2],"landscape_rank_4":landscape_rank[3],"landscape_rank_5":landscape_rank[4],"landscape_other":landscape_other.strip(),"semi_residential":", ".join(semi_residential),"semi_residential_other":semi_residential_other.strip(),"memo":memo.strip()}
            go_step(3)

def render_step3():
    v, s = st.session_state.verified, st.session_state.get("survey", {})
    st.subheader("3단계. 최종 제출 전 확인")
    st.markdown("### 조합원 확인 정보")
    st.write(f"- 성명: {v['name']}"); st.write(f"- 소유 동·호수: {v['existing_dong']} {v['existing_ho']}"); st.write(f"- 현재 평형: {v['existing_size']}")
    st.markdown("### 설문 응답 요약")
    st.write(f"- 입주 계획: {s.get('family_plan')}")
    if s.get("family_count"): st.write(f"- 가족인원 수: {s.get('family_count')}명")
    st.write(f"- 희망 평면: {s.get('plan_preference')}"); st.write(f"- 방 개수: {s.get('room_count')}"); st.write(f"- 세대구분형 옵션: {s.get('household_split')}"); st.write(f"- 희망 평형: **{s.get('hope_size')}**")
    st.write(f"- 주차대수: {s.get('parking')} {s.get('parking_other') or ''}")
    st.write(f"- 중요 요소 순위: {s.get('factor_rank_1')} → {s.get('factor_rank_2')} → {s.get('factor_rank_3')} → {s.get('factor_rank_4')} → {s.get('factor_rank_5')}")
    st.write(f"- 커뮤니티 1~5순위: {s.get('community_rank_1')}, {s.get('community_rank_2')}, {s.get('community_rank_3')}, {s.get('community_rank_4')}, {s.get('community_rank_5')}")
    st.write(f"- 조경 1~5순위: {s.get('landscape_rank_1')}, {s.get('landscape_rank_2')}, {s.get('landscape_rank_3')}, {s.get('landscape_rank_4')}, {s.get('landscape_rank_5')}")
    st.write(f"- 준주거용지 특화계획: {s.get('semi_residential') or '선택 없음'}")
    st.warning("제출 후 수정은 1회만 가능합니다.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("설문 수정하기", use_container_width=True): go_step(2)
    with c2:
        if st.button("최종 제출", type="primary", use_container_width=True):
            try:
                existing = get_submission_by_key(v["unit_key"])
                if existing is None: insert_submission({**v, **s}); st.success("제출이 완료되었습니다."); st.balloons()
                else:
                    success, msg = update_submission(existing, {**v, **s}); st.success(msg) if success else st.error(msg)
            except Exception as e:
                st.error("저장 중 오류가 발생했습니다. 아래 오류 내용을 알려주세요."); st.code(str(e))

def render_check():
    st.subheader("내 제출 확인")
    name = st.text_input("성명", key="check_name"); c1,c2 = st.columns(2)
    with c1: dong = st.text_input("소유 동", key="check_dong")
    with c2: ho = st.text_input("소유 호수", key="check_ho")
    if st.button("확인하기", key="check_btn", use_container_width=True):
        if not all([name.strip(), dong.strip(), ho.strip()]): st.error("성명, 동, 호수를 입력해 주세요.")
        else:
            try:
                existing = get_submission_by_key(make_unit_key(name,dong,ho))
                if not existing: st.warning("제출 내역을 찾을 수 없습니다.")
                else:
                    st.success("제출 내역이 확인되었습니다."); st.write(f"성명: {existing.get('name')}"); st.write(f"소유 동·호수: {existing.get('existing_dong')} {existing.get('existing_ho')}"); st.write(f"현재 평형: {existing.get('existing_size')}"); st.write(f"희망 평형: {existing.get('hope_size')}"); st.write(f"수정 횟수: {existing.get('edit_count', 0)}회 / 1회 가능")
            except Exception as e: st.error("조회 중 오류가 발생했습니다."); st.code(str(e))

def counts_table(df, column, options=None):
    if column not in df.columns: return pd.DataFrame()
    vc = df[column].fillna("미응답").replace("", "미응답").value_counts()
    if options: vc = vc.reindex(options + ["미응답"], fill_value=0)
    out = vc.rename_axis("항목").reset_index(name="응답 수"); out["비율"] = (out["응답 수"] / len(df) * 100).round(1).astype(str) + "%"; return out

def render_admin():
    st.subheader("관리자 통계")
    password = st.text_input("관리자 비밀번호", type="password")
    if not password: st.info("관리자 비밀번호를 입력해 주세요."); return
    if not hmac.compare_digest(password, ADMIN_PASSWORD): st.error("비밀번호가 맞지 않습니다."); return
    try: df = read_all_submissions()
    except Exception as e: st.error("DB 조회 중 오류가 발생했습니다."); st.code(str(e)); return
    if df.empty: st.warning("아직 제출된 응답이 없습니다."); return
    st.success("관리자 인증 완료")
    m1,m2,m3,m4 = st.columns(4); m1.metric("전체 참여자 수", f"{len(df):,}명"); m2.metric("현재 평형 수", f"{df['existing_size'].nunique():,}개"); m3.metric("희망 평형 수", f"{df['hope_size'].nunique():,}개" if "hope_size" in df.columns else "0개"); m4.metric("수정 제출", f"{(pd.to_numeric(df.get('edit_count',0), errors='coerce').fillna(0)>0).sum():,}건")
    st.divider(); st.subheader("희망 평형")
    hst = counts_table(df,"hope_size",HOPE_SIZE_OPTIONS); st.dataframe(hst,use_container_width=True)
    if not hst.empty: st.bar_chart(hst.set_index("항목")[["응답 수"]])
    st.subheader("현재 평형 × 희망 평형")
    if "existing_size" in df.columns and "hope_size" in df.columns: st.dataframe(pd.crosstab(df["existing_size"], df["hope_size"]), use_container_width=True)
    st.subheader("Q03 중요 요소 1순위"); st.dataframe(counts_table(df,"factor_rank_1",IMPORTANT_FACTORS), use_container_width=True)
    st.subheader("Q05 주차대수"); st.dataframe(counts_table(df,"parking",PARKING_OPTIONS), use_container_width=True)
    st.subheader("Q06 커뮤니티 1순위"); st.dataframe(counts_table(df,"community_rank_1",COMMUNITY_OPTIONS), use_container_width=True)
    st.subheader("Q07 조경 1순위"); st.dataframe(counts_table(df,"landscape_rank_1",LANDSCAPE_OPTIONS), use_container_width=True)
    st.subheader("Q08 준주거용지 특화계획")
    if "semi_residential" in df.columns:
        exploded = df["semi_residential"].fillna("").str.split(", ").explode(); exploded = exploded[exploded != ""]
        st.dataframe(exploded.value_counts().rename_axis("항목").reset_index(name="응답 수"), use_container_width=True)
    st.divider(); anonymized = df.drop(columns=["id","name","unit_key"], errors="ignore")
    st.download_button("개인정보 제외 응답 CSV 다운로드", data=safe_download_csv(anonymized), file_name="apgujeong3_survey_anonymized_v05.csv", mime="text/csv", use_container_width=True)
    with st.expander("원본 응답 데이터 보기 / 다운로드"):
        st.warning("원본 데이터에는 개인정보가 포함됩니다. 접근 권한을 제한해 주세요."); st.dataframe(df, use_container_width=True)
        st.download_button("원본 응답 CSV 다운로드", data=safe_download_csv(df), file_name="apgujeong3_survey_raw_v05.csv", mime="text/csv", use_container_width=True)

def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🏙️", layout="wide")
    init_state(); st.title(APP_TITLE); st.caption("모바일 클릭형 설문 v0.5 안정판")
    tab1,tab2,tab3 = st.tabs(["조사 참여","내 제출 확인","관리자 통계"])
    with tab1:
        render_header_notice()
        if st.session_state.step == 1: render_step1()
        elif st.session_state.step == 2: render_step2()
        elif st.session_state.step == 3: render_step3()
    with tab2: render_check()
    with tab3: render_admin()
if __name__ == "__main__": main()
