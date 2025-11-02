import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import matplotlib.pyplot as plt

# -------------------------------
# HÀM ĐỌC DỮ LIỆU LINH HOẠT
# -------------------------------
@st.cache_data
def load_data(path):
    try:
        df = pd.read_csv(path)
    except Exception:
        try:
            df = pd.read_csv(path, sep=';')
        except Exception:
            df = pd.read_csv(path, sep=None, engine='python')

    # Chuẩn hóa tọa độ
    for col in ['POINT_X', 'POINT_Y']:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(',', '.', regex=False)
                .replace('nan', None)
                .astype(float)
            )

    # Đảm bảo không có NaN trong tọa độ
    df = df.dropna(subset=['POINT_X', 'POINT_Y']).reset_index(drop=True)
    return df


# -------------------------------
# HIỂN THỊ BẢN ĐỒ FOLIUM
# -------------------------------
def show_map(df, selected_xa=None):
    avg_lat = df["POINT_Y"].mean()
    avg_lon = df["POINT_X"].mean()

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=10, tiles="CartoDB positron")
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():
        popup = f"""
        <b>{row.get('tenXa', 'Không rõ')}</b><br>
        NDVI: {row.get('NDVI_HCM_B', 'N/A')}<br>
        LST: {row.get('LST_HCM_BD', 'N/A')}<br>
        TDVI: {row.get('TDVI_HCM_B', 'N/A')}<br>
        Dân số: {row.get('danSo', 'N/A')}<br>
        Diện tích: {row.get('dienTich', 'N/A')}
        """
        folium.Marker(
            location=[row["POINT_Y"], row["POINT_X"]],
            popup=popup,
            icon=folium.Icon(
                color="red" if row.get("tenXa") == selected_xa else "blue", icon="info-sign"
            ),
        ).add_to(marker_cluster)

    st_data = st_folium(m, width=800, height=600)
    return st_data


# -------------------------------
# HIỂN THỊ BIỂU ĐỒ TƯƠNG QUAN NDVI - LST
# -------------------------------
def show_scatter(df, xa_name):
    df = df.dropna(subset=["NDVI_HCM_B", "LST_HCM_BD"])
    if xa_name:
        sub_df = df[df["tenXa"] == xa_name]
        if sub_df.empty:
            st.warning(f"Không có dữ liệu NDVI và LST cho {xa_name}")
            return
        st.subheader(f"Biểu đồ NDVI – LST của {xa_name}")
    else:
        sub_df = df
        st.subheader("Biểu đồ NDVI – LST (toàn bộ dữ liệu)")

    plt.figure(figsize=(6, 4))
    plt.scatter(sub_df["NDVI_HCM_B"], sub_df["LST_HCM_BD"], c="green", alpha=0.7)
    plt.xlabel("NDVI")
    plt.ylabel("LST (°C)")
    plt.title("Mối tương quan NDVI – LST")
    plt.grid(True)
    st.pyplot(plt)


# -------------------------------
# GIAO DIỆN CHÍNH APP
# -------------------------------
def main():
    st.set_page_config(page_title="Map & Chart Tool", layout="wide")
    st.title("🧭 Map & Chart Tool – Phân tích NDVI, LST, TDVI")

    uploaded_file = st.file_uploader("Tải lên file CSV dữ liệu:", type=["csv"])
    if not uploaded_file:
        st.info("⬆️ Hãy tải file dữ liệu CSV của bạn lên để bắt đầu")
        return

    df = load_data(uploaded_file)

    # Chuẩn hóa kiểu dữ liệu số
    for col in ["NDVI_HCM_B", "LST_HCM_BD", "TDVI_HCM_B"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", ".", regex=False)
                .replace("nan", None)
                .astype(float)
            )

    # Bộ lọc
    st.sidebar.header("⚙️ Bộ lọc dữ liệu")
    unique_tinh = df["maTinh"].dropna().unique().tolist() if "maTinh" in df.columns else []
    unique_xa = df["tenXa"].dropna().unique().tolist() if "tenXa" in df.columns else []

    selected_tinh = st.sidebar.selectbox("Chọn tỉnh:", ["Tất cả"] + unique_tinh)
    selected_xa = st.sidebar.selectbox("Chọn xã:", ["Tất cả"] + unique_xa)

    # Lọc theo NDVI và LST
    if "NDVI_HCM_B" in df.columns:
        ndvi_min, ndvi_max = float(df["NDVI_HCM_B"].min()), float(df["NDVI_HCM_B"].max())
        ndvi_range = st.sidebar.slider("Khoảng NDVI", ndvi_min, ndvi_max, (ndvi_min, ndvi_max))
        df = df[(df["NDVI_HCM_B"] >= ndvi_range[0]) & (df["NDVI_HCM_B"] <= ndvi_range[1])]

    if "LST_HCM_BD" in df.columns:
        lst_min, lst_max = float(df["LST_HCM_BD"].min()), float(df["LST_HCM_BD"].max())
        lst_range = st.sidebar.slider("Khoảng LST", lst_min, lst_max, (lst_min, lst_max))
        df = df[(df["LST_HCM_BD"] >= lst_range[0]) & (df["LST_HCM_BD"] <= lst_range[1])]

    # Áp dụng bộ lọc
    if selected_tinh != "Tất cả":
        df = df[df["maTinh"] == selected_tinh]
    if selected_xa != "Tất cả":
        df = df[df["tenXa"] == selected_xa]

    # Hiển thị bản đồ
    st.subheader("🗺️ Bản đồ phân bố dữ liệu")
    show_map(df, selected_xa if selected_xa != "Tất cả" else None)

    # Biểu đồ tương quan
    show_scatter(df, selected_xa if selected_xa != "Tất cả" else None)

    # Bảng dữ liệu
    with st.expander("📋 Xem dữ liệu chi tiết"):
        st.dataframe(df)


if __name__ == "__main__":
    main()
