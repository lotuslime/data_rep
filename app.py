# -*- coding: utf-8 -*-
"""
서울특별시 종로구 공공시설 태양광 설치현황 분석 대시보드
Streamlit + Plotly
"""

import re
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="종로구 공공시설 태양광 설치현황 분석",
    page_icon="☀️",
    layout="wide",
)

DATA_PATH = "서울특별시_종로구_공공시설_태양광_설치현황_20210423.csv"


# -----------------------------------------------------------------------------
# 데이터 로드 & 전처리
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # --- 동(행정동) 추출 -----------------------------------------------------
    def get_dong(row):
        for addr in [row["도로명 주소"], row["지번 주소"]]:
            m = re.search(r"\(([^)]+)\)", str(addr))
            if m:
                return m.group(1)
        for addr in [row["지번 주소"], row["도로명 주소"]]:
            m2 = re.search(r"종로구\s*([가-힣0-9]+(?:동|가))", str(addr))
            if m2:
                return m2.group(1)
        return "기타"

    df["동"] = df.apply(get_dong, axis=1)

    # --- 시설 유형 분류 -------------------------------------------------------
    def get_category(name: str) -> str:
        name = str(name)
        if "어린이집" in name:
            return "어린이집"
        if "복지관" in name or "복지센터" in name:
            return "복지시설"
        if "경로당" in name:
            return "경로당"
        if "주민센터" in name or "자치회관" in name or "청사" in name:
            return "행정복지센터"
        if "주차장" in name or "주차안내소" in name:
            return "주차시설"
        if "화장실" in name:
            return "공중화장실"
        if "문화체육" in name or "구민회관" in name:
            return "문화체육시설"
        return "기타"

    df["시설유형"] = df["시설명"].apply(get_category)

    df = df.rename(columns={"설치용량(킬로와트)": "설치용량_kW"})
    df["설치년도"] = df["설치년도"].astype(int)

    return df


df = load_data(DATA_PATH)

# -----------------------------------------------------------------------------
# 사이드바 - 필터
# -----------------------------------------------------------------------------
st.sidebar.title("🔎 필터")

years = sorted(df["설치년도"].unique())
year_range = st.sidebar.slider(
    "설치년도 범위",
    min_value=int(min(years)),
    max_value=int(max(years)),
    value=(int(min(years)), int(max(years))),
)

types = sorted(df["시설유형"].unique())
selected_types = st.sidebar.multiselect("시설 유형", types, default=types)

dongs = sorted(df["동"].unique())
selected_dongs = st.sidebar.multiselect("행정동", dongs, default=dongs)

filtered = df[
    (df["설치년도"] >= year_range[0])
    & (df["설치년도"] <= year_range[1])
    & (df["시설유형"].isin(selected_types))
    & (df["동"].isin(selected_dongs))
]

st.sidebar.markdown("---")
st.sidebar.caption(f"기준일자: {df['기준일자'].iloc[0]}")
st.sidebar.caption("출처: 서울특별시 종로구 공공시설 태양광 설치현황 (2021.04.23)")

# -----------------------------------------------------------------------------
# 헤더
# -----------------------------------------------------------------------------
st.title("☀️ 종로구 공공시설 태양광 설치현황 분석")
st.caption("서울특별시 종로구 공공시설 태양광 설치현황 (기준일자 2021-04-23) 데이터를 기반으로 한 분석 대시보드")

if filtered.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다. 필터를 조정해 주세요.")
    st.stop()

# -----------------------------------------------------------------------------
# 핵심 지표 (KPI)
# -----------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

total_facilities = len(filtered)
total_capacity = filtered["설치용량_kW"].sum()
avg_capacity = filtered["설치용량_kW"].mean()
max_row = filtered.loc[filtered["설치용량_kW"].idxmax()]

col1.metric("총 설치 시설 수", f"{total_facilities} 개")
col2.metric("총 설치 용량", f"{total_capacity:,.2f} kW")
col3.metric("시설당 평균 용량", f"{avg_capacity:,.2f} kW")
col4.metric("최대 설치 용량 시설", max_row["시설명"], f"{max_row['설치용량_kW']:.2f} kW")

st.markdown("---")

# -----------------------------------------------------------------------------
# 1. 연도별 설치 추이
# -----------------------------------------------------------------------------
st.subheader("📈 연도별 태양광 설치 추이")

yearly = (
    filtered.groupby("설치년도")
    .agg(설치건수=("시설명", "count"), 설치용량_kW=("설치용량_kW", "sum"))
    .reindex(range(year_range[0], year_range[1] + 1), fill_value=0)
    .reset_index()
    .rename(columns={"index": "설치년도"})
)
yearly["누적용량_kW"] = yearly["설치용량_kW"].cumsum()
yearly["누적건수"] = yearly["설치건수"].cumsum()

c1, c2 = st.columns(2)

with c1:
    fig_bar = go.Figure()
    fig_bar.add_trace(
        go.Bar(
            x=yearly["설치년도"],
            y=yearly["설치용량_kW"],
            name="연도별 설치용량(kW)",
            marker_color="#F5A623",
        )
    )
    fig_bar.add_trace(
        go.Scatter(
            x=yearly["설치년도"],
            y=yearly["누적용량_kW"],
            name="누적 설치용량(kW)",
            mode="lines+markers",
            line=dict(color="#2E86AB", width=3),
            yaxis="y2",
        )
    )
    fig_bar.update_layout(
        title="연도별 / 누적 설치용량",
        xaxis=dict(title="설치년도", dtick=1),
        yaxis=dict(title="연도별 설치용량(kW)"),
        yaxis2=dict(title="누적 설치용량(kW)", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        height=420,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with c2:
    fig_count = px.bar(
        yearly,
        x="설치년도",
        y="설치건수",
        text="설치건수",
        title="연도별 설치 건수",
        color_discrete_sequence=["#6C63FF"],
    )
    fig_count.update_traces(textposition="outside")
    fig_count.update_layout(xaxis=dict(dtick=1), height=420)
    st.plotly_chart(fig_count, use_container_width=True)

# -----------------------------------------------------------------------------
# 2. 시설 유형별 분석
# -----------------------------------------------------------------------------
st.subheader("🏢 시설 유형별 분석")

type_agg = (
    filtered.groupby("시설유형")
    .agg(설치건수=("시설명", "count"), 총설치용량=("설치용량_kW", "sum"), 평균용량=("설치용량_kW", "mean"))
    .sort_values("총설치용량", ascending=False)
    .reset_index()
)

c3, c4 = st.columns(2)

with c3:
    fig_pie = px.pie(
        type_agg,
        names="시설유형",
        values="총설치용량",
        title="시설 유형별 설치용량 비중",
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_pie.update_traces(textinfo="label+percent")
    st.plotly_chart(fig_pie, use_container_width=True)

with c4:
    fig_type_bar = px.bar(
        type_agg,
        x="시설유형",
        y="평균용량",
        text=type_agg["평균용량"].round(1),
        title="시설 유형별 평균 설치용량(kW)",
        color="시설유형",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_type_bar.update_traces(textposition="outside")
    fig_type_bar.update_layout(showlegend=False, height=450)
    st.plotly_chart(fig_type_bar, use_container_width=True)

# -----------------------------------------------------------------------------
# 3. 설치용량 분포
# -----------------------------------------------------------------------------
st.subheader("📊 설치용량 분포")

c5, c6 = st.columns(2)

with c5:
    fig_hist = px.histogram(
        filtered,
        x="설치용량_kW",
        nbins=10,
        title="설치용량 분포 히스토그램",
        color_discrete_sequence=["#F5A623"],
    )
    fig_hist.update_layout(bargap=0.1)
    st.plotly_chart(fig_hist, use_container_width=True)

with c6:
    fig_box = px.box(
        filtered,
        x="시설유형",
        y="설치용량_kW",
        points="all",
        title="시설 유형별 설치용량 분포(박스플롯)",
        color="시설유형",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

# -----------------------------------------------------------------------------
# 4. 시설별 랭킹
# -----------------------------------------------------------------------------
st.subheader("🏆 설치용량 상위 시설")

top_n = st.slider("표시할 시설 수", 5, min(20, len(filtered)), min(10, len(filtered)))
top_facilities = filtered.sort_values("설치용량_kW", ascending=False).head(top_n)

fig_top = px.bar(
    top_facilities.sort_values("설치용량_kW"),
    x="설치용량_kW",
    y="시설명",
    orientation="h",
    color="시설유형",
    text="설치용량_kW",
    title=f"설치용량 상위 {top_n}개 시설",
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig_top.update_traces(texttemplate="%{text:.1f} kW", textposition="outside")
fig_top.update_layout(height=max(400, 30 * top_n))
st.plotly_chart(fig_top, use_container_width=True)

# -----------------------------------------------------------------------------
# 5. 행정동별 분포
# -----------------------------------------------------------------------------
st.subheader("🗺️ 행정동별 설치 현황")

dong_agg = (
    filtered.groupby("동")
    .agg(설치건수=("시설명", "count"), 총설치용량=("설치용량_kW", "sum"))
    .sort_values("총설치용량", ascending=False)
    .reset_index()
)

fig_dong = px.bar(
    dong_agg,
    x="동",
    y="총설치용량",
    text="설치건수",
    title="행정동별 총 설치용량(kW) — 막대 위 숫자는 설치 건수",
    color="총설치용량",
    color_continuous_scale="Oranges",
)
fig_dong.update_traces(textposition="outside")
fig_dong.update_layout(height=450, coloraxis_showscale=False)
st.plotly_chart(fig_dong, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. 인사이트 요약
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("💡 데이터 인사이트")

top_type = type_agg.iloc[0]
top_dong = dong_agg.iloc[0]
early_years = yearly[yearly["설치건수"] > 0]["설치년도"].min()
recent_years = yearly[yearly["설치건수"] > 0]["설치년도"].max()

insight_col1, insight_col2 = st.columns(2)

with insight_col1:
    st.markdown(
        f"""
**1. 전반적 현황**
- 분석 기간({int(early_years)}년 ~ {int(recent_years)}년) 동안 총 **{total_facilities}개** 공공시설에 태양광 설비가 설치되었습니다.
- 총 설치용량은 **{total_capacity:,.2f} kW**이며, 발전유형은 모두 **태양광**으로 단일합니다.
- 시설 1곳당 평균 설치용량은 **{avg_capacity:.2f} kW**로, 개별 건물 단위의 소규모 분산형 설비 위주입니다.

**2. 설치용량 편차**
- 최대 설치용량은 **{max_row['시설명']}**의 **{max_row['설치용량_kW']:.2f} kW**로, 최소값 대비 편차가 큰 편입니다.
- 표준편차가 평균의 80% 이상으로, 시설 규모(면적/유형)에 따라 설치 용량 격차가 상당합니다.
        """
    )

with insight_col2:
    st.markdown(
        f"""
**3. 시설 유형별 특징**
- 총 설치용량 기준 **{top_type['시설유형']}**이 가장 큰 비중을 차지합니다({top_type['총설치용량']:.1f} kW).
- 어린이집·경로당 등 생활밀착형 시설에도 고르게 소규모 설비가 분산 설치되어 있어, 특정 대형시설 집중이 아닌 **전방위적 보급 전략**이 확인됩니다.

**4. 지역 및 시기적 특징**
- 행정동 기준으로는 **{top_dong['동']}**의 설치용량이 가장 높습니다.
- 2009년(초기 보급기)과 2015~2018년(확대기)에 설치 건수가 몰려 있어, 특정 시점에 정책적으로 설치가 집중된 패턴을 보입니다.
        """
    )

with st.expander("📋 원본 데이터 보기"):
    st.dataframe(filtered.reset_index(drop=True), use_container_width=True)

st.caption("본 대시보드는 서울열린데이터광장 등에서 제공한 공공데이터를 기반으로 제작되었습니다.")
