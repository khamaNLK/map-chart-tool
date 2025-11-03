import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt

# ==============================
# HÀM ĐỌC VÀ LÀM SẠCH DỮ LIỆU
# ==============================
@st.cache_data
def load_data(uploaded_file):
    try:
        # Đọc dữ liệu CSV, bỏ dòng lỗi
        df = pd.read_csv(uploaded_file, on_bad_lines='skip', encoding='utf-8', dtype=str)
        df = df.dropna(how='all')  # bỏ dòng trống

        # Chuẩn hóa tên cột
        df.columns = df.columns.str.strip().str.lower()

        # Tìm các cột có thể là lat/lon
        possible_lat = [c for c in df.columns if 'lat' in c.lower()]
        possible_lon = [c for c in df.columns if 'lon' in c.lower() or 'long' in c.lower()]

        if possible_lat and possible_lon:
            lat_col = possible_lat[0]
            lon_col = possible_lon[0]

            # Làm sạch giá trị (loại dấu chấm ngăn nghìn)
            def clean_coord(x):
                if isinstance(x, str):
                    x = x.replace('.', '').replace(',', '.')
                try:
                    return float(x)
                except:
                    return None

            df[lat_col] = df[lat_col].apply(clean_coord)
            df[lon_col] = df[lon_col].apply(clean_coord)

            # Bỏ dòng thiếu tọa độ
            df = df.dropna(subset=[lat_col, lon_col])

            return df, lat_col, lon_col
        else:
            st.error("⚠️ Không tìm thấy cột latitude / longitude trong dữ liệu!")
            return None, None, None
    except Exception as e:
        st.error(f"❌ Lỗi đọc CSV: {e}")
        return None, None, None

# ==============================
# HÀM TẠO BẢN ĐỒ
# ==============================
def create_map(df, lat_col, lon_col):
    try:
        center_lat = df[lat_col].mean()
        center_lon = df[lon_col].mean()

        m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="CartoDB positron")

        for _, row in df.iterrows():
            popup_text = "<br>".join([f"<b>{col}</b>: {row[col]}" for col in df.columns[:5]])
            folium.CircleMarker(
                location=[row[lat_col], row[lon_col]],
                radius=4,
                color="blue",
                fill=True,
                fill_opacity=0.6,
                popup=popup_text
            ).add_to(m)

        return m
    except Exception as e:
        st.error(f"❌ Lỗi tạo bản đồ: {e}")
        return None

# ==============================
# GIAO DIỆN CHÍNH
# ==============================
def main():
    st.title("🗺️ Ứng dụng hiển thị bản đồ CSV tương tác")

    uploaded_file = st.file_uploader("📂 Tải lên file CSV", type=["csv"])
    if uploaded_file:
        df, lat_col, lon_col = load_data(uploaded_file)
        if df is not None:
            st.success(f"✅ Đọc thành công {len(df)} dòng dữ liệu.")
            st.dataframe(df.head())

            folium_map = create_map(df, lat_col, lon_col)
            if folium_map:
                st_folium(folium_map, width=800, height=500)

            # Vẽ biểu đồ tương quan NDVI - LST nếu có
            if 'ndvi' in df.columns and 'lst' in df.columns:
                st.subheader("📈 Biểu đồ tương quan NDVI – LST")
                fig, ax = plt.subplots()
                ax.scatter(df['ndvi'].astype(float), df['lst'].astype(float), alpha=0.6)
                ax.set_xlabel("NDVI")
                ax.set_ylabel("LST")
                ax.set_title("Mối tương quan NDVI – LST")
                st.pyplot(fig)

if __name__ == "__main__":
    main()
