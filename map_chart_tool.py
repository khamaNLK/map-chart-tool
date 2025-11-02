import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point
import plotly.express as px
import io
import tempfile

# ==========================
# 🔹 HÀM ĐỌC CSV AN TOÀN
# ==========================
def safe_read_csv(file_path_or_obj):
    try:
        df = pd.read_csv(file_path_or_obj, engine='python', sep=None, on_bad_lines='skip')
    except Exception:
        try:
            df = pd.read_csv(file_path_or_obj, delimiter=';', engine='python', on_bad_lines='skip')
        except Exception:
            try:
                df = pd.read_csv(file_path_or_obj, delimiter='\t', engine='python', on_bad_lines='skip')
            except Exception as e:
                st.error(f"❌ Lỗi đọc CSV: {e}")
                return None
    return df


# ==========================
# 🔹 APP STREAMLIT
# ==========================
def main():
    st.set_page_config(page_title="Bản đồ NDVI - LST", layout="wide")
    st.title("🛰️ Phân tích mối tương quan NDVI – LST theo khu vực")

    uploaded_file = st.file_uploader("📂 Tải lên file CSV dữ liệu (NDVI, LST, xã...)", type=["csv"])
    if uploaded_file is None:
        st.info("⬆️ Hãy tải lên file CSV để bắt đầu.")
        st.stop()

    # Đọc file CSV
    df = safe_read_csv(uploaded_file)
    if df is None:
        st.stop()

    st.success(f"✅ Đã đọc {len(df)} dòng và {len(df.columns)} cột.")
    st.write("**Các cột có trong dữ liệu:**", list(df.columns))

    # ==========================
    # 🔹 XÁC ĐỊNH CỘT TỌA ĐỘ
    # ==========================
    lat_col = None
    lon_col = None
    for c in df.columns:
        c_lower = c.lower()
        if "lat" in c_lower or "y" == c_lower or "point_y" in c_lower:
            lat_col = c
        if "lon" in c_lower or "x" == c_lower or "point_x" in c_lower:
            lon_col = c

    if lat_col is None or lon_col is None:
        st.error("⚠️ Không tìm thấy cột tọa độ (lat/lon hoặc POINT_X, POINT_Y). Hãy kiểm tra lại CSV.")
        st.stop()

    df = df.dropna(subset=[lat_col, lon_col])
    if df.empty:
        st.error("⚠️ Dữ liệu trống sau khi bỏ dòng thiếu tọa độ.")
        st.stop()

    # ==========================
    # 🔹 TẠO BẢN ĐỒ FOLIUM
    # ==========================
    try:
        center_lat = df[lat_col].astype(float).mean()
        center_lon = df[lon_col].astype(float).mean()
        folium_map = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="CartoDB positron")
    except Exception as e:
        st.error(f"❌ Lỗi tạo bản đồ: {e}")
        st.stop()

    # Thêm điểm lên bản đồ
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row[lat_col], row[lon_col]],
            radius=3,
            color="blue",
            fill=True,
            fill_opacity=0.6
        ).add_to(folium_map)

    st.subheader("🗺️ Bản đồ hiển thị vị trí các điểm")
    st_folium(folium_map, height=500)

    # ==========================
    # 🔹 CHỌN XÃ & VẼ SCATTER NDVI - LST
    # ==========================
    st.subheader("📊 Biểu đồ tương quan NDVI – LST theo xã")

    # Tìm cột xã
    xa_col = None
    for c in df.columns:
        if "xa" in c.lower() or "commune" in c.lower() or "ward" in c.lower():
            xa_col = c
            break

    if xa_col is None:
        st.error("⚠️ Không tìm thấy cột tên xã (xa / commune / ward).")
        st.stop()

    ndvi_col = None
    lst_col = None
    for c in df.columns:
        if "ndvi" in c.lower():
            ndvi_col = c
        if "lst" in c.lower():
            lst_col = c

    if ndvi_col is None or lst_col is None:
        st.error("⚠️ Không tìm thấy cột NDVI hoặc LST trong dữ liệu.")
        st.stop()

    xa_selected = st.selectbox("Chọn xã để hiển thị biểu đồ:", sorted(df[xa_col].dropna().unique()))

    df_xa = df[df[xa_col] == xa_selected]
    if df_xa.empty:
        st.warning("❗ Không có dữ liệu cho xã đã chọn.")
    else:
        fig = px.scatter(
            df_xa,
            x=ndvi_col,
            y=lst_col,
            title=f"Mối tương quan NDVI – LST của xã {xa_selected}",
            trendline="ols",
            labels={ndvi_col: "NDVI", lst_col: "LST"}
        )
        st.plotly_chart(fig, use_container_width=True)

    # ==========================
    # 🔹 TẢI XUỐNG DỮ LIỆU ĐÃ XỬ LÝ
    # ==========================
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        df.to_csv(tmp.name, index=False)
        with open(tmp.name, "rb") as f:
            st.download_button("💾 Tải xuống dữ liệu đã xử lý", f, file_name="processed_data.csv")


if __name__ == "__main__":
    main()
