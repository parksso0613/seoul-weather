import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="서울 100년 기온 변화 분석",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E293B;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #64748B;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)


DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul.csv"

@st.cache_data
def load_data():
    """CSV 데이터를 불러와 정리하는 함수 (인코딩 자동 감지 및 결측치 처리)"""
    encodings = ['utf-8', 'cp949', 'euc-kr']
    df = None
    
    for enc in encodings:
        try:
            df = pd.read_csv(DATA_URL, encoding=enc)
            break
        except Exception:
            continue
            
    if df is None:
        st.error("데이터를 불러오는 데 실패했습니다.")
        return None

    # 열 이름 정리 (공백 제거)
    df.columns = df.columns.str.strip()
    
    # 열 이름 유연한 매핑
    col_map = {}
    for col in df.columns:
        if '날짜' in col:
            col_map[col] = '날짜'
        elif '지점' in col:
            col_map[col] = '지점'
        elif '평균' in col:
            col_map[col] = '평균기온'
        elif '최저' in col:
            col_map[col] = '최저기온'
        elif '최고' in col:
            col_map[col] = '최고기온'
            
    df = df.rename(columns=col_map)

    # 날짜 변환 및 수치형 데이터 정리
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜'])
    
    temp_cols = ['평균기온', '최저기온', '최고기온']
    for col in temp_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 연도 추출
    df['연도'] = df['날짜'].dt.year
    return df


with st.spinner("서울 기온 데이터를 불러오는 중입니다..."):
    raw_df = load_data()

if raw_df is not None:
    # 연도별 평균 및 극값 계산
    annual_df = raw_df.groupby('연도').agg(
        연평균기온=('평균기온', 'mean'),
        연평균최저기온=('최저기온', 'mean'),
        연평균최고기온=('최고기온', 'mean'),
        역대최고기온=('최고기온', 'max'),
        역대최저기온=('최저기온', 'min'),
        데이터수=('평균기온', 'count')
    ).reset_index()

    # 데이터 수 부족한 해(300일 미만) 제외
    annual_df = annual_df[annual_df['데이터수'] >= 300].copy()
    annual_df['연평균기온'] = annual_df['연평균기온'].round(2)
    
    # 이동평균계산 (5년)
    annual_df['5년_이동평균'] = annual_df['연평균기온'].rolling(window=5, min_periods=1).mean().round(2)

    st.sidebar.header("⚙️ 분석 설정")
    min_year = int(annual_df['연도'].min())
    max_year = int(annual_df['연도'].max())
    
    selected_range = st.sidebar.slider(
        "조회 연도 범위 선택",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year)
    )
    
    show_ma = st.sidebar.checkbox("5년 이동평균선 표시", value=True)
    show_trend = st.sidebar.checkbox("추세선(선형 회귀) 표시", value=True)

    # 선택 범위 데이터 필터링
    filtered_df = annual_df[(annual_df['연도'] >= selected_range[0]) & (annual_df['연도'] <= selected_range[1])]

    st.markdown('<div class="main-title">🌡️ 지난 100년간 서울의 기온은 어떻게 변했을까?</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">1907년부터 최근까지 서울의 연평균 기온 변화 추이를 한눈에 살펴봅니다. ({selected_range[0]}년 ~ {selected_range[1]}년)</div>', unsafe_allow_html=True)

    # 주요지표 요약 Metric Cards
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    
    first_temp = filtered_df.iloc[0]['연평균기온']
    last_temp = filtered_df.iloc[-1]['연평균기온']
    diff_temp = round(last_temp - first_temp, 2)
    avg_total = round(filtered_df['연평균기온'].mean(), 2)
    max_record = filtered_df['역대최고기온'].max()
    min_record = filtered_df['역대최저기온'].min()

    m_col1.metric("선택 구간 첫해 연평균", f"{first_temp} ℃", f"{selected_range[0]}년")
    m_col2.metric("선택 구간 최근해 연평균", f"{last_temp} ℃", f"{diff_temp:+} ℃ (변화량)", delta_color="inverse")
    m_col3.metric("구간 전체 평균기온", f"{avg_total} ℃")
    m_col4.metric("구간 역대 최고 / 최저", f"{max_record}℃ / {min_record}℃")

    st.markdown("---")

    st.subheader("📈 연도별 서울 연평균 기온 변화 추이")

    fig = go.Figure()

    # 연평균기온 꺾은선
    fig.add_trace(go.Scatter(
        x=filtered_df['연도'],
        y=filtered_df['연평균기온'],
        mode='lines+markers',
        name='연평균 기온',
        line=dict(color='#EF4444', width=2),
        marker=dict(size=5),
        hovertemplate='%{x}년: <b>%{y}℃</b><extra></extra>'
    ))

    # 5년 이동평균선
    if show_ma:
        fig.add_trace(go.Scatter(
            x=filtered_df['연도'],
            y=filtered_df['5년_이동평균'],
            mode='lines',
            name='5년 이동평균',
            line=dict(color='#F59E0B', width=2.5, dash='dash'),
            hovertemplate='%{x}년 (5년 평균): <b>%{y}℃</b><extra></extra>'
        ))

    # 추세선 (Plotly Express Trendline 활용)
    if show_trend and len(filtered_df) > 1:
        trend_fig = px.scatter(filtered_df, x='연도', y='연평균기온', trendline='ols')
        trend_trace = trend_fig.data[1]
        trend_trace.line.color = '#10B981'
        trend_trace.line.width = 2
        trend_trace.name = '상승 추세선'
        fig.add_trace(trend_trace)

    fig.update_layout(
        xaxis_title="연도 (Year)",
        yaxis_title="평균 기온 (℃)",
        hovermode="x unified",
        template="plotly_white",
        height=520,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=20, r=20, t=60, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📄 데이터 상세 보기 및 다운로드"):
        st.write(f"총 **{len(filtered_df)}**개 연도의 데이터가 조회되었습니다.")
        st.dataframe(filtered_df[['연도', '연평균기온', '연평균최저기온', '연평균최고기온', '역대최고기온', '역대최저기온']], use_container_width=True)
        
        csv_bytes = filtered_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 요약 데이터 CSV 다운로드",
            data=csv_bytes,
            file_name="seoul_annual_temperature.csv",
            mime="text/csv"
        )
