# map_chart_tool.py
# Phiên bản 2.0 – Click marker cập nhật biểu đồ NDVI–LST
# Đại ca build: 2025-11-02

import sys

# --- Import an toàn ---
try:
    import streamlit as st
    import pandas as pd
    import folium
    from streamlit_folium import st_folium
    import plotly.express as px
except Exception as e:
    print(f"Lỗi import thư viện: {e}")
    print("→ Cài bằng lệnh: pip install streamlit pandas folium streamlit-folium plotly")
    sys.exit(1)

# --- Đọc dữ liệu ---
@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    required = ["tenXa", "POINT_X", "POINT_Y", "NDVI_HCM_B", "LST_HCM_BD"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Thiếu cột trong dữ liệu: {missing}")
        st.stop()
    return df

# --- App chính ---
def main():
    st.set_page_config(page_title="Map & Scatter Tool 2.0", layout="wide")
    st.title("🗺️ Công cụ tương tác NDVI – LST theo xã (v2.0)")

    csv_path = "1_1_2018.csv"
    df = load_data(csv_path)

    # Sidebar
    st.sidebar.header("⚙️ Tùy chọn hiển thị")
    all_communes = sorted(df["tenXa"].dropna().unique())
    manual_select = st.sidebar.selectbox("Chọn xã (hoặc click marker):", ["(Tất cả)"] + list(all_communes))

    # Tâm bản đồ
    m = folium.Map(
        location=[df["POINT_Y"].mean(), df["POINT_X"].mean()],
        zoom_start=10,
        tiles="CartoDB positron"
    )

    # Tạo marker cho từng xã
    for _, row in df.iterrows():
        popup = f"{row['tenXa']}"
        color = "red" if row["tenXa"] == manual_select else "blue"
        folium.CircleMarker(
            location=[row["POINT_Y"], row["POINT_X"]],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=popup
        ).add_to(m)

    # Hiển thị bản đồ & lấy sự kiện click
    map_event = st_folium(m, width=1000, height=600)

    # Xác định xã được chọn
    clicked_commune = None
    if map_event and map_event.get("last_object_clicked_popup"):
        clicked_commune = map_event["last_object_clicked_popup"]

    # Ưu tiên: click > chọn tay
    active_commune = clicked_commune or manual_select

    # --- Biểu đồ Scatter ---
    st.subheader("📈 Biểu đồ tương quan NDVI – LST")
    if active_commune == "(Tất cả)":
        fig = px.scatter(
            df,
            x="NDVI_HCM_B",
            y="LST_HCM_BD",
            color="tenXa",
            hover_name="tenXa",
            title="Mối tương quan NDVI – LST (Tất cả xã)",
            labels={"NDVI_HCM_B": "NDVI", "LST_HCM_BD": "LST (°C)"}
        )
        st.info("💡 Chọn xã trong danh sách hoặc click marker để xem biểu đồ riêng.")
    else:
        subset = df[df["tenXa"] == active_commune]
        if subset.empty:
            st.warning(f"⚠️ Không có dữ liệu cho xã {active_commune}.")
            return
        fig = px.scatter(
            subset,
            x="NDVI_HCM_B",
            y="LST_HCM_BD",
            color_discrete_sequence=["red"],
            title=f"Mối tương quan NDVI – LST của {active_commune}",
            labels={"NDVI_HCM_B": "NDVI", "LST_HCM_BD": "LST (°C)"}
        )
        st.success(f"✅ Đang hiển thị xã: {active_commune}")

    fig.update_traces(marker=dict(size=10, opacity=0.8))
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()

