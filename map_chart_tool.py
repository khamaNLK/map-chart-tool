import sys
from pathlib import Path

HAS_STREAMLIT = True
try:
    import streamlit as st
    from streamlit_folium import st_folium
except Exception:
    HAS_STREAMLIT = False

import pandas as pd
import folium
import plotly.express as px
from folium.plugins import HeatMap

# ==========================================================
# Utility Functions
# ==========================================================

def normalize_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa dữ liệu CSV: đổi , → ., ép kiểu số."""
    df = df.copy()
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].str.replace(',', '.', regex=False)
            try:
                df[c] = df[c].astype(float)
            except Exception:
                pass
    return df

def auto_detect_columns(df):
    """Tự phát hiện các cột NDVI, LST, TDVI nếu có."""
    cols = list(df.columns)
    ndvi = next((c for c in cols if "NDVI" in c.upper()), None)
    lst = next((c for c in cols if "LST" in c.upper()), None)
    tdvi = next((c for c in cols if "TDVI" in c.upper()), None)
    return ndvi, lst, tdvi


# ==========================================================
# Streamlit App
# ==========================================================

def run_streamlit_app():
    st.set_page_config(layout="wide", page_title="🗺️ NDVI–LST Interactive Tool v3.1")
    st.title("🗺️ Công cụ tương tác NDVI – LST theo xã (v3.1)")
    st.markdown("Upload file CSV có chứa cột **NDVI, LST, TDVI, lat, lng, name (hoặc tenXa)**.")

    uploaded_file = st.file_uploader("Tải lên file CSV dữ liệu", type=["csv"])
    if not uploaded_file:
        st.info("Hãy tải lên file CSV để bắt đầu.")
        st.stop()

    # Đọc và chuẩn hóa CSV
    try:
        df = pd.read_csv(uploaded_file, dtype=str)
    except Exception as e:
        st.error(f"Lỗi đọc CSV: {e}")
        st.stop()

    df = normalize_csv(df)
    df.columns = [c.strip() for c in df.columns]

    # Xác định các cột chính
    lat_col = next((c for c in df.columns if "POINT_Y" in c.upper() or "LAT" == c.upper()), None)
    lon_col = next((c for c in df.columns if "POINT_X" in c.upper() or "LON" == c.upper() or "LONG" == c.upper()), None)
    name_col = next((c for c in df.columns if "TENXA" in c.upper() or "NAME" == c.upper()), None)

    if not lat_col or not lon_col:
        st.error("Không tìm thấy cột tọa độ (lat/lng hoặc POINT_X/POINT_Y).")
        st.stop()

    ndvi_col, lst_col, tdvi_col = auto_detect_columns(df)
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    with st.sidebar:
        st.header("⚙️ Cài đặt hiển thị")
        value_col = st.selectbox("Chọn chỉ số hiển thị", [ndvi_col, lst_col, tdvi_col] + numeric_cols)
        show_heatmap = st.checkbox("Hiển thị Heatmap", value=True)
        scatter_mode = st.checkbox("Hiển thị biểu đồ tương quan NDVI–LST", value=True)
        zoom_level = st.slider("Độ phóng to bản đồ", 6, 16, 10)

    # Bỏ hàng thiếu tọa độ
    df = df.dropna(subset=[lat_col, lon_col])
    df[lat_col] = df[lat_col].astype(float)
    df[lon_col] = df[lon_col].astype(float)
    df[value_col] = pd.to_numeric(df[value_col], errors='coerce')

    # ==========================================================
    #  MAP SECTION
    # ==========================================================
    st.subheader("🗺️ Bản đồ phân bố chỉ số")

    center = [df[lat_col].mean(), df[lon_col].mean()]
    m = folium.Map(location=center, zoom_start=zoom_level, tiles="CartoDB positron")

    if show_heatmap and value_col:
        heat_data = df[[lat_col, lon_col, value_col]].dropna().values.tolist()
        HeatMap(heat_data, radius=12, blur=8).add_to(m)
    else:
        for _, r in df.iterrows():
            val = r.get(value_col, None)
            popup = f"<b>{r.get(name_col, '')}</b><br>{value_col}: {val}"
            folium.CircleMarker(
                location=(r[lat_col], r[lon_col]),
                radius=6,
                color='blue',
                fill=True,
                fill_opacity=0.7,
                popup=popup
            ).add_to(m)

    st_data = st_folium(m, height=600, width="100%")

    # ==========================================================
    #  CHART SECTION
    # ==========================================================
    st.markdown("---")
    st.subheader("📊 Biểu đồ")

    if scatter_mode and ndvi_col and lst_col:
        scatter_df = df[[ndvi_col, lst_col, name_col]].dropna()
        fig = px.scatter(
            scatter_df,
            x=ndvi_col,
            y=lst_col,
            color=lst_col,
            hover_data=[name_col],
            title="Mối quan hệ NDVI – LST",
            labels={ndvi_col: "NDVI", lst_col: "LST (°C)"}
        )
    else:
        chart_df = df[[name_col, value_col]].dropna()
        fig = px.bar(chart_df.sort_values(by=value_col, ascending=False),
                     x=name_col, y=value_col, title=f"Giá trị {value_col} theo {name_col}")

    st.plotly_chart(fig, use_container_width=True)

    # ==========================================================
    #  DATA TABLE
    # ==========================================================
    st.markdown("---")
    st.subheader("🧾 Bảng dữ liệu gốc")
    st.dataframe(df[[name_col, lat_col, lon_col, value_col]].head(100))

    st.success("✅ Đã tải và hiển thị dữ liệu thành công!")


if __name__ == "__main__":
    if HAS_STREAMLIT:
        run_streamlit_app()
    else:
        print("Streamlit không khả dụng. Chạy ở chế độ CLI tĩnh không được hỗ trợ trong v3.1.")
