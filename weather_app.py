# -*- coding: utf-8 -*-
"""
기상청 단기예보 조회서비스(getVilageFcst) 기반
오늘/내일 날씨 예보 Streamlit 앱
"""

import requests
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# ------------------------------------------------------------------
# 기본 설정
# ------------------------------------------------------------------
ENDPOINT = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
SERVICE_KEY = "c677ae584dbb6c5cbf94bf38fbcea516d94951ca9d62f6b4bb2bbe5063b4d4bf"

# 주요 도시별 예보지점 좌표 (nx, ny) - 기상청 격자 좌표계 기준
CITY_GRID = {
    "서울": (60, 127),
    "인천": (55, 124),
    "수원": (60, 121),
    "춘천": (73, 134),
    "강릉": (92, 131),
    "청주": (69, 106),
    "대전": (67, 100),
    "세종": (66, 103),
    "전주": (63, 89),
    "광주": (58, 74),
    "목포": (50, 67),
    "여수": (73, 66),
    "대구": (89, 90),
    "부산": (98, 76),
    "울산": (102, 84),
    "창원": (91, 77),
    "제주": (52, 38),
}

SKY_CODE = {"1": "맑음", "3": "구름많음", "4": "흐림"}
PTY_CODE = {
    "0": "없음", "1": "비", "2": "비/눈", "3": "눈",
    "4": "소나기", "5": "빗방울", "6": "빗방울눈날림", "7": "눈날림",
}
SKY_ICON = {"1": "☀️", "3": "⛅", "4": "☁️"}
PTY_ICON = {
    "0": "", "1": "🌧️", "2": "🌨️", "3": "❄️",
    "4": "🌦️", "5": "🌧️", "6": "🌨️", "7": "❄️",
}

CATEGORY_LABEL = {
    "POP": "강수확률(%)",
    "PTY": "강수형태",
    "PCP": "1시간 강수량",
    "REH": "습도(%)",
    "SNO": "1시간 신적설",
    "SKY": "하늘상태",
    "TMP": "기온(℃)",
    "TMN": "최저기온(℃)",
    "TMX": "최고기온(℃)",
    "UUU": "풍속(동서성분)",
    "VVV": "풍속(남북성분)",
    "WAV": "파고(M)",
    "VEC": "풍향(deg)",
    "WSD": "풍속(m/s)",
}


# ------------------------------------------------------------------
# base_date / base_time 계산
# 단기예보 발표시각: 02,05,08,11,14,17,20,23시 (매시각 10분 이후 제공)
# ------------------------------------------------------------------
def get_base_datetime(now: datetime):
    base_hours = [2, 5, 8, 11, 14, 17, 20, 23]
    candidate = now - timedelta(minutes=10)  # API는 발표 후 10분 뒤부터 제공
    for h in reversed(base_hours):
        base_dt = candidate.replace(hour=h, minute=0, second=0, microsecond=0)
        if base_dt <= candidate:
            return base_dt
    # 오늘 자정 이전이면 전날 23시 사용
    prev_day = candidate - timedelta(days=1)
    return prev_day.replace(hour=23, minute=0, second=0, microsecond=0)


def wind_dir_16(deg):
    try:
        deg = float(deg)
    except (TypeError, ValueError):
        return ""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]
    idx = int((deg + 22.5 * 0.5) / 22.5)
    return dirs[idx] if 0 <= idx < len(dirs) else ""


# ------------------------------------------------------------------
# API 호출
# ------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def fetch_forecast(nx: int, ny: int, base_date: str, base_time: str):
    params = {
        "serviceKey": SERVICE_KEY,
        "pageNo": "1",
        "numOfRows": "1000",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }
    resp = requests.get(ENDPOINT, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    header = data.get("response", {}).get("header", {})
    result_code = header.get("resultCode")
    result_msg = header.get("resultMsg")

    if result_code != "00":
        raise RuntimeError(f"API 오류 [{result_code}] {result_msg}")

    items = data["response"]["body"]["items"]["item"]
    return items


def build_dataframe(items):
    df = pd.DataFrame(items)
    if df.empty:
        return df
    # fcstDate + fcstTime 기준 pivot
    pivot = df.pivot_table(
        index=["fcstDate", "fcstTime"],
        columns="category",
        values="fcstValue",
        aggfunc="first",
    ).reset_index()
    pivot = pivot.sort_values(["fcstDate", "fcstTime"])
    return pivot


# ------------------------------------------------------------------
# Streamlit UI
# ------------------------------------------------------------------
st.set_page_config(page_title="오늘/내일 날씨", page_icon="🌤️", layout="wide")

st.title("🌤️ 오늘 · 내일 날씨 예보")
st.caption("기상청 단기예보 조회서비스(VilageFcstInfoService_2.0 - getVilageFcst) 기반")

with st.sidebar:
    st.header("설정")
    city = st.selectbox("지역 선택", list(CITY_GRID.keys()), index=0)
    nx, ny = CITY_GRID[city]

    with st.expander("좌표 직접 입력 (선택)"):
        custom = st.checkbox("직접 좌표 사용")
        if custom:
            nx = st.number_input("nx", value=nx, step=1)
            ny = st.number_input("ny", value=ny, step=1)

    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear()

now = datetime.now()
base_dt = get_base_datetime(now)
base_date = base_dt.strftime("%Y%m%d")
base_time = base_dt.strftime("%H%M")

st.sidebar.markdown("---")
st.sidebar.write(f"**조회 지점:** {city} (nx={nx}, ny={ny})")
st.sidebar.write(f"**발표시각(base_time):** {base_date} {base_time}")
st.sidebar.write(f"**조회시각:** {now.strftime('%Y-%m-%d %H:%M:%S')}")

# ------------------------------------------------------------------
# 데이터 조회
# ------------------------------------------------------------------
try:
    with st.spinner("날씨 정보를 불러오는 중..."):
        items = fetch_forecast(nx, ny, base_date, base_time)
except Exception as e:
    st.error(f"날씨 정보를 불러오지 못했습니다: {e}")
    st.stop()

df = build_dataframe(items)

if df.empty:
    st.warning("예보 데이터가 없습니다.")
    st.stop()

today_str = now.strftime("%Y%m%d")
tomorrow_str = (now + timedelta(days=1)).strftime("%Y%m%d")

df_today = df[df["fcstDate"] == today_str].copy()
df_tomorrow = df[df["fcstDate"] == tomorrow_str].copy()


def summary_card(day_label, day_df, date_str):
    st.subheader(day_label)
    if day_df.empty:
        st.info("해당 날짜의 예보 데이터가 없습니다.")
        return

    # 최저/최고 기온 (TMN/TMX는 일부 발표시각에만 존재)
    tmn = day_df["TMN"].dropna().iloc[0] if "TMN" in day_df.columns and day_df["TMN"].notna().any() else None
    tmx = day_df["TMX"].dropna().iloc[0] if "TMX" in day_df.columns and day_df["TMX"].notna().any() else None

    # 현재 시각과 가장 가까운(또는 다음) 시간대 골라 대표 정보 표시
    now_hhmm = now.strftime("%H%M") if date_str == today_str else "0600"
    future = day_df[day_df["fcstTime"] >= now_hhmm]
    rep_row = future.iloc[0] if not future.empty else day_df.iloc[0]

    sky = rep_row.get("SKY")
    pty = rep_row.get("PTY")
    tmp = rep_row.get("TMP")
    pop = rep_row.get("POP")
    reh = rep_row.get("REH")

    icon = PTY_ICON.get(pty, "") or SKY_ICON.get(sky, "🌡️")
    condition = PTY_CODE.get(pty, "") if pty and pty != "0" else SKY_CODE.get(sky, "-")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("현재/예상 기온", f"{tmp}℃" if tmp is not None else "-")
    col2.metric("최저 / 최고", f"{tmn if tmn is not None else '-'}℃ / {tmx if tmx is not None else '-'}℃")
    col3.metric("강수확률", f"{pop}%" if pop is not None else "-")
    col4.metric("습도", f"{reh}%" if reh is not None else "-")

    st.markdown(f"### {icon} {condition}")

    st.markdown("**시간대별 예보**")
    hourly = day_df.copy()
    hourly["시간"] = hourly["fcstTime"].apply(lambda t: f"{t[:2]}:{t[2:]}")
    hourly["하늘/강수"] = hourly.apply(
        lambda r: (PTY_ICON.get(r.get("PTY"), "") or SKY_ICON.get(r.get("SKY"), ""))
        + " "
        + (PTY_CODE.get(r.get("PTY"), "") if r.get("PTY") and r.get("PTY") != "0" else SKY_CODE.get(r.get("SKY"), "-")),
        axis=1,
    )
    hourly["기온(℃)"] = hourly.get("TMP")
    hourly["강수확률(%)"] = hourly.get("POP")
    hourly["습도(%)"] = hourly.get("REH")
    if "VEC" in hourly.columns:
        hourly["풍향"] = hourly["VEC"].apply(wind_dir_16)
    else:
        hourly["풍향"] = ""
    hourly["풍속(m/s)"] = hourly.get("WSD")

    show_cols = ["시간", "하늘/강수", "기온(℃)", "강수확률(%)", "습도(%)", "풍향", "풍속(m/s)"]
    st.dataframe(hourly[show_cols], use_container_width=True, hide_index=True)

    # 기온 추이 차트
    chart_df = hourly[["시간", "기온(℃)"]].dropna()
    if not chart_df.empty:
        chart_df["기온(℃)"] = pd.to_numeric(chart_df["기온(℃)"], errors="coerce")
        st.line_chart(chart_df.set_index("시간"))


tab1, tab2 = st.tabs(["오늘", "내일"])
with tab1:
    summary_card("오늘 날씨", df_today, today_str)
with tab2:
    summary_card("내일 날씨", df_tomorrow, tomorrow_str)

st.markdown("---")
st.caption(
    "데이터 출처: 기상청 단기예보 조회서비스(공공데이터포털) · "
    "예보는 매 발표시각(02,05,08,11,14,17,20,23시) 기준 10분 뒤부터 갱신됩니다."
)
