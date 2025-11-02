import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import seaborn as sns
import io

st.set_page_config(page_title="🗺️ Công cụ tương tác NDVI – LST theo xã (v3.0)", layout="wide")

# ------------------------
# 🔧 Đọc và xử lý dữ liệu
# ------------------------
@st.cache_data
def load_data(path):
    df = pd.read_csv(path, dtype=str)

    # Chuẩn hóa tọa độ
    for col in ["POINT_X", "POINT_Y"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .replace("nan", None)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Chuẩn hóa các chỉ số NDVI, LST, TDVI
    for col in ["NDVI_HCM_B", "LST_HCM_BD", "TDVI_HCM_B"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Loại bỏ dòng không có tọa độ
    df = df.dropna(subset=["POINT_X", "POINT_Y"])
    return df


# ------------------------
# 🗺️ Vẽ bản đồ
# ------------------------
def create_map(df, heat_type="NDVI_HCM_B"):
    if df.empty:
        st.warning("Không có dữ liệu để hiển thị bản đồ.")
        return None

    center_lat = df["POINT_Y"].mean()
    center_lon = df["POINT_X"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="CartoDB positron")

    # Marker từng xã
    for _, row in df.iterrows():
        popup_text = (
            f"<b>{row.get('tenXa', 'Không rõ')}</b><br>"
            f"NDVI: {row.get('NDVI_HCM_B', 'N/A')}<br>"
            f"LST: {row.get('LST_HCM_BD', 'N/A')}<br>"
            f"TDVI: {row.get('TDVI_HCM_B', 'N/A')}"
        )
        folium.CircleMarker(
            location=[row["POINT_Y"], row["POINT_X"]],
            radius=5,
            color="blue",
            fill=True,
            fill_opacity=0.6,
            popup=popup_text,
        ).add_to(m)

    # Heatmap NDVI hoặc LST
    if heat_type in df.columns:
        heat_data = df[["POINT_Y", "POINT_X", heat_type]].dropna().values.tolist()
        HeatMap(heat_data, radius=18).add_to(m)

    return m


# ------------------------
# 📊 Scatter & Histogram
# ------------------------
def scatter_plot(df, selected_commune=None):
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.scatterplot(data=df, x="NDVI_HCM_B", y="LST_HCM_BD", ax=ax)
    sns.regplot(data=df, x="NDVI_HCM_B", y="LST_HCM_BD", scatter=False, ax=ax, color="red")

    if selected_commune:
        commune_data = df[df["tenXa"] == selected_commune]
        if not commune_data.empty:
            ax.scatter(commune_data["NDVI_HCM_B"], commune_data["LST_HCM_BD"], color="orange", s=100, label=selected_commune)
            ax.legend()

    ax.set_title("Mối tương quan NDVI – LST")
    ax.set_xlabel("NDVI")
    ax.set_ylabel("LST (°C)")
    st.pyplot(fig)


def histogram_plot(df):
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.histplot(df["NDVI_HCM_B"].dropna(), bins=10, kde=True, ax=ax)
    ax.set_title("Phân bố giá trị NDVI toàn vùng")
    ax.set_xlabel("NDVI")
    st.pyplot(fig)


# ------------------------
# 🚀 Giao diện chính
# ------------------------
def main():
    st.title("🗺️ Công cụ tương tác NDVI – LST theo xã (v3.0)")

    uploaded_file = st.file_uploader("Tải lên file CSV dữ liệu xã/phường", type=["csv"])
    if not uploaded_file:
        st.info("📂 Vui lòng tải lên file CSV (ví dụ: 1_1_2018.csv).")
        st.stop()

    df = load_data(uploaded_file)

    st.success(f"Đã tải {len(df)} dòng dữ liệu hợp lệ.")

    # Thống kê nhanh
    col1, col2, col3 = st.columns(3)
    col1.metric("🌿 NDVI TB", f"{df['NDVI_HCM_B'].mean():.3f}")
    col2.metric("🔥 LST TB (°C)", f"{df['LST_HCM_BD'].mean():.2f}")
    col3.metric("📊 Số xã/phường", len(df))

    st.markdown("---")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["🗺️ Bản đồ tương tác", "📈 Scatter NDVI–LST", "📊 Phân bố NDVI"])

    # --- Tab 1 ---
    with tab1:
        heat_choice = st.selectbox("Chọn lớp hiển thị nhiệt:", ["NDVI_HCM_B", "LST_HCM_BD"])
        m = create_map(df, heat_type=heat_choice)
        if m:
            st_data = st_folium(m, height=600, width=1000)

    # --- Tab 2 ---
    with tab2:
        commune_list = sorted(df["tenXa"].dropna().unique())
        selected_commune = st.selectbox("Chọn xã để hiển thị riêng:", ["(Tất cả)"] + commune_list)
        if selected_commune != "(Tất cả)":
            scatter_plot(df, selected_commune)
        else:
            scatter_plot(df)

    # --- Tab 3 ---
    with tab3:
        histogram_plot(df)

    st.markdown("----")
    st.caption("© 2025 NDVI–LST Map Tool v3.0 | Developed by Đại ca & ChatGPT")

# ------------------------
# Run app
# ------------------------
if __name__ == "__main__":
    main()
