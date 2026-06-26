import os, hmac, hashlib
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client

APP_TITLE='압구정3구역 희망평형·위치 조사'
UNIT=['49평','56평','64평','74평','기타']
FLOOR=['저층','중층','고층','초고층','상관없음']
LOC=['한강변','내부','도로변','역세권','상관없음']
PRI=['평형','한강변/위치','층','추가분담금 최소화','기존 위치 유지','상관없음']
COMPLEX=['1·2차','3차','4차','6·7차','10차','13차','대림아크빌','대림빌라트','현대빌라트','기타']
SIZE=['35평 이하','36평','42평','48평','50평','52평','53평','54평','65평','80평 이상','기타']

def secret(k, default=''):
    try:
        return str(st.secrets.get(k, default))
    except Exception:
        return os.getenv(k, default)

ADMIN_PASSWORD=secret('SURVEY_ADMIN_PASSWORD','admin123')

@st.cache_resource
def sb():
    url=secret('SUPABASE_URL')
    key=secret('SUPABASE_SERVICE_ROLE_KEY') or secret('SUPABASE_ANON_KEY')
    if not url or not key:
        st.error('Supabase 연결 정보가 없습니다. README의 secrets 설정을 먼저 해주세요.')
        st.stop()
    return create_client(url,key)

def norm(x): return str(x).strip().replace(' ','')
def unit_key(name, phone, complex_name, dong, ho):
    raw='|'.join([norm(name),norm(phone),norm(complex_name),norm(dong),norm(ho)])
    return hashlib.sha256(raw.encode()).hexdigest()

def get_one(key):
    r=sb().table('submissions').select('*').eq('unit_key',key).limit(1).execute()
    return r.data[0] if r.data else None

def get_all():
    r=sb().table('submissions').select('*').order('created_at',desc=True).execute()
    return pd.DataFrame(r.data or [])

def save_new(data):
    data={**data,'created_at':datetime.now().isoformat(timespec='seconds'),'updated_at':None,'edit_count':0,'consent':True}
    sb().table('submissions').insert(data).execute()

def save_update(old,data):
    if int(old.get('edit_count',0))>=1:
        return False,'이미 1회 수정하셨습니다. 추가 수정은 관리자에게 문의해 주세요.'
    payload={k:data[k] for k in ['hope_size_1','hope_size_2','hope_size_3','hope_floor','hope_location','top_priority','memo']}
    payload['updated_at']=datetime.now().isoformat(timespec='seconds')
    payload['edit_count']=int(old.get('edit_count',0))+1
    sb().table('submissions').update(payload).eq('id',old['id']).execute()
    sb().table('edit_logs').insert({'submission_id':old['id'],'edited_at':payload['updated_at'],'old_data':str(old),'new_data':str(data)}).execute()
    return True,'수정이 완료되었습니다.'

def intro():
    st.markdown('''### 조사 목적
본 조사는 압구정3구역 조합원들의 **희망 평형 및 희망 위치**를 파악하기 위한 의견수렴 조사입니다.  
본 조사 결과는 향후 배치도 검토 및 그룹핑 논의의 참고자료로 활용될 수 있으며, **공식 분양신청 또는 동·호수 배정을 의미하지 않습니다.**

---
### 개인정보 수집·이용 안내
- 수집 목적: 조합원 본인 확인 및 희망 평형·위치 의견수렴
- 수집 항목: 성명, 휴대폰번호, 기존 단지, 기존 동·호수, 기존 평형, 희망 평형, 희망 층, 희망 위치
- 보유 기간: 조사 종료 후 6개월 또는 사용 목적 달성 시까지
- 제3자 제공: 없음
- 결과 공개: 개인 식별이 불가능한 통계 형태로만 공개
''')

def survey():
    intro(); consent=st.checkbox('위 내용을 확인했고 개인정보 수집·이용에 동의합니다.')
    st.subheader('1. 조합원 확인')
    a,b=st.columns(2)
    with a:
        name=st.text_input('성명'); phone=st.text_input('휴대폰번호',placeholder='01012345678'); complex_name=st.selectbox('기존 단지',COMPLEX)
    with b:
        dong=st.text_input('기존 동',placeholder='예: 73동'); ho=st.text_input('기존 호수',placeholder='예: 1201호'); existing_size=st.selectbox('기존 평형',SIZE)
    st.subheader('2. 희망 평형')
    c1,c2,c3=st.columns(3)
    with c1: h1=st.selectbox('1순위 희망 평형',UNIT,index=1)
    with c2: h2=st.selectbox('2순위 희망 평형',UNIT,index=2)
    with c3: h3=st.selectbox('3순위 희망 평형',UNIT,index=3)
    st.subheader('3. 희망 층·위치')
    c4,c5=st.columns(2)
    with c4: floor=st.selectbox('희망 층 등급',FLOOR,index=2)
    with c5: loc=st.selectbox('희망 위치 등급',LOC,index=0)
    st.subheader('4. 최우선 기준')
    pri=st.selectbox('평형, 위치, 층 중 하나만 우선해야 한다면 무엇이 가장 중요합니까?',PRI)
    memo=st.text_area('추가 의견',height=90)
    st.divider(); st.subheader('제출 전 확인')
    st.write(f'기존 정보: {complex_name} / {dong} {ho} / 기존 {existing_size}')
    st.write(f'희망 평형: 1순위 {h1}, 2순위 {h2}, 3순위 {h3}')
    st.write(f'희망 층: {floor} / 희망 위치: {loc} / 최우선 기준: {pri}')
    st.caption('제출 후 수정은 1회만 가능합니다.')
    if st.button('제출하기',type='primary',use_container_width=True):
        if not consent: st.error('개인정보 수집·이용에 동의해야 제출할 수 있습니다.'); return
        if any(not str(x).strip() for x in [name,phone,dong,ho]): st.error('성명, 휴대폰번호, 기존 동·호수를 입력해 주세요.'); return
        if len({h1,h2,h3})<3: st.error('희망 평형 1·2·3순위는 서로 다르게 선택해 주세요.'); return
        key=unit_key(name,phone,complex_name,dong,ho); old=get_one(key)
        data={'name':name.strip(),'phone':phone.strip(),'complex_name':complex_name,'existing_dong':dong.strip(),'existing_ho':ho.strip(),'existing_size':existing_size,'unit_key':key,'hope_size_1':h1,'hope_size_2':h2,'hope_size_3':h3,'hope_floor':floor,'hope_location':loc,'top_priority':pri,'memo':memo.strip()}
        if old is None:
            save_new(data); st.success('제출이 완료되었습니다.'); st.balloons()
        else:
            ok,msg=save_update(old,data); (st.success if ok else st.error)(msg)

def check():
    st.subheader('내 제출 확인')
    name=st.text_input('성명',key='ck1'); phone=st.text_input('휴대폰번호',key='ck2'); complex_name=st.selectbox('기존 단지',COMPLEX,key='ck3')
    a,b=st.columns(2)
    with a: dong=st.text_input('기존 동',key='ck4')
    with b: ho=st.text_input('기존 호수',key='ck5')
    if st.button('확인하기',use_container_width=True):
        old=get_one(unit_key(name,phone,complex_name,dong,ho))
        if not old: st.warning('제출 내역을 찾을 수 없습니다.')
        else:
            st.success('제출 내역이 확인되었습니다.')
            st.write(f"기존 정보: {old['complex_name']} / {old['existing_dong']} {old['existing_ho']} / 기존 {old['existing_size']}")
            st.write(f"희망 평형: 1순위 {old['hope_size_1']}, 2순위 {old['hope_size_2']}, 3순위 {old['hope_size_3']}")
            st.write(f"희망 층: {old['hope_floor']} / 희망 위치: {old['hope_location']} / 최우선 기준: {old['top_priority']}")
            st.write(f"수정 횟수: {old.get('edit_count',0)}회 / 1회 가능")

def admin():
    st.subheader('관리자 화면'); pw=st.text_input('관리자 비밀번호',type='password')
    if not pw: st.info('관리자 비밀번호를 입력해 주세요.'); return
    if not hmac.compare_digest(pw,ADMIN_PASSWORD): st.error('비밀번호가 맞지 않습니다.'); return
    df=get_all()
    if df.empty: st.warning('아직 제출된 응답이 없습니다.'); return
    st.success('관리자 인증 완료')
    a,b,c,d=st.columns(4); a.metric('전체 참여자 수',f'{len(df):,}명'); b.metric('기존 단지 수',df['complex_name'].nunique()); c.metric('기존 평형 수',df['existing_size'].nunique()); d.metric('수정 제출',int((pd.to_numeric(df['edit_count'],errors='coerce').fillna(0)>0).sum()))
    st.subheader('전체 희망 평형')
    size=df['hope_size_1'].value_counts().reindex(UNIT,fill_value=0).rename_axis('희망 평형').reset_index(name='1순위 희망자')
    allr=pd.concat([df['hope_size_1'],df['hope_size_2'],df['hope_size_3']]).value_counts().reindex(UNIT,fill_value=0)
    size['1·2·3순위 포함 희망자']=size['희망 평형'].map(allr).fillna(0).astype(int)
    st.dataframe(size,use_container_width=True); st.bar_chart(size.set_index('희망 평형')[['1순위 희망자']])
    st.subheader('기존 평형별 희망 평형'); st.dataframe(pd.crosstab(df['existing_size'],df['hope_size_1']).reindex(columns=UNIT,fill_value=0),use_container_width=True)
    st.subheader('기존 단지별 희망 평형'); st.dataframe(pd.crosstab(df['complex_name'],df['hope_size_1']).reindex(columns=UNIT,fill_value=0),use_container_width=True)
    st.subheader('위치 선호')
    lc=df['hope_location'].value_counts().reindex(LOC,fill_value=0).rename_axis('위치').reset_index(name='희망자 수'); lc['비율']=(lc['희망자 수']/len(df)*100).round(1).astype(str)+'%'
    st.dataframe(lc,use_container_width=True); st.bar_chart(lc.set_index('위치')[['희망자 수']])
    st.subheader('평형 × 위치 교차표'); st.dataframe(pd.crosstab(df['hope_size_1'],df['hope_location']).reindex(index=UNIT,columns=LOC,fill_value=0),use_container_width=True)
    st.subheader('최우선 기준')
    pc=df['top_priority'].value_counts().reindex(PRI,fill_value=0).rename_axis('최우선 기준').reset_index(name='희망자 수'); pc['비율']=(pc['희망자 수']/len(df)*100).round(1).astype(str)+'%'
    st.dataframe(pc,use_container_width=True)
    st.divider(); st.subheader('CSV 다운로드')
    anon=df.drop(columns=['id','name','phone','unit_key'],errors='ignore')
    st.download_button('개인정보 제외 응답 CSV 다운로드',anon.to_csv(index=False,encoding='utf-8-sig').encode('utf-8-sig'),'apgujeong3_survey_anonymized.csv','text/csv',use_container_width=True)
    with st.expander('원본 응답 데이터 보기 / 다운로드'):
        st.warning('원본 데이터에는 개인정보가 포함됩니다. 접근 권한을 제한해 주세요.'); st.dataframe(df,use_container_width=True)
        st.download_button('원본 응답 CSV 다운로드',df.to_csv(index=False,encoding='utf-8-sig').encode('utf-8-sig'),'apgujeong3_survey_raw.csv','text/csv',use_container_width=True)

st.set_page_config(page_title=APP_TITLE,page_icon='🏙️',layout='wide')
st.title(APP_TITLE); st.caption('온라인 버전: 휴대폰 접속 → 입력 → 중앙 DB 저장 → 관리자 통계 확인')
t1,t2,t3=st.tabs(['조사 참여','내 제출 확인','관리자 통계'])
with t1: survey()
with t2: check()
with t3: admin()
