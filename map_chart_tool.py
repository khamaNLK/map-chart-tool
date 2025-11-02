"""
map_chart_tool_v3.py
Interactive Map + Analysis tool for NDVI-LST at commune/ward level.

Features:
- Robust CSV reading (tries different separators, skips bad lines)
- Auto-detect columns: name, lon/lat, NDVI, LST, TDVI (if present)
- Normalize numeric formats (comma decimal -> dot)
- Folium map with markers + HeatMap layer
- Plotly scatter (NDVI vs LST) and histogram (NDVI)
- Click marker or select commune in sidebar -> updates charts
- Cached data loading for speed
"""

import sys
from io import StringIO
from typing import Optional, Tuple, List

# Safe imports with helpful error message
try:
    import streamlit as st
    import pandas as pd
    import folium
    from streamlit_folium import st_folium
    import plotly.express as px
    from folium.plugins import HeatMap
except Exception as e:
    print("Một số thư viện cần thiết chưa được cài. Chạy:")
    print("pip install streamlit pandas folium streamlit-folium plotly")
    raise e

# -------------------------
# Utilities & Data Loading
# -------------------------
@st.cache_data(show_spinner=False)
def try_read_csv(path_or_buffer) -> pd.DataFrame:
    """
    Try to read csv with common separators. Returns DataFrame.
    path_or_buffer: path string or file-like object (from st.file_uploader).
    """
    # If path_or_buffer is a Streamlit UploadedFile, convert to BytesIO and try multiple separators
    seps = [",", ";", "\t"]
    last_exception = None
    for sep in seps:
        try:
            # pandas >= 1.3 supports on_bad_lines
            df = pd.read_csv(path_or_buffer, sep=sep, encoding="utf-8", on_bad_lines="skip")
            return df
        except Exception as e:
            last_exception = e
            # try next sep
            continue
    # final attempt with utf-8-sig (BOM) and comma
    try:
        df = pd.read_csv(path_or_buffer, sep=",", encoding="utf-8-sig", on_bad_lines="skip")
        return df
    except Exception:
        # re-raise last exception for debugging
        raise last_exception

def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Return first matching column name in df from candidates (case-insensitive)."""
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        key = cand.lower()
        if key in cols_lower:
            return cols_lower[key]
    # try contains
    for cand in candidates:
        for col in df.columns:
            if cand.lower() in col.lower():
                return col
    return None

def coerce_numeric_column(df: pd.DataFrame, col: str) -> pd.Series:
    """
    Convert a column to numeric robustly:
    - replace comma decimal separators with dot
    - remove spaces
    - coerce errors to NaN
    """
    s = df[col].astype(str).str.strip()
    # If strings use comma as decimal (e.g. '0,4851') convert to '0.4851'
    # But careful: coordinates sometimes use comma as decimal.
    s = s.str.replace(r"\s+", "", regex=True)
    # Replace comma decimal only when there's no other dot
    # Simpler approach: always replace comma with dot then coerce
    s = s.str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")

@st.cache_data(show_spinner=False)
def load_and_prepare(df_source) -> Tuple[pd.DataFrame, dict]:
    """
    Read CSV (or use uploaded file) and prepare:
    - detect columns
    - coerce numeric fields
    Returns cleaned df and a dictionary of detected column names
    """
    df = try_read_csv(df_source)

    # Trim column names
    df.columns = [c.strip() for c in df.columns]

    # Detect name column (tenXa, name, xa, phuong)
    name_col = find_column(df, ["tenXa", "ten_xa", "ten", "xa", "phuong", "tenxa", "commune", "name"])
    # Detect coordinate columns: POINT_X/POINT_Y, X/Y, lon/lat
    lon_col = find_column(df, ["POINT_X", "POINT_X ", "POINTX", "long", "lon", "x", "longitude"])
    lat_col = find_column(df, ["POINT_Y", "POINT_Y ", "POINTY", "lat", "y", "latitude"])

    # Detect NDVI, LST, TDVI
    ndvi_col = find_column(df, ["NDVI", "ndvi_hcm", "ndvi_hcm_b", "ndvi"])
    lst_col = find_column(df, ["LST", "LST_HCM", "LST_HCM_BD", "lst"])
    tdvi_col = find_column(df, ["TDVI", "tdvi_hcm_b", "tdvi"])

    detected = {
        "name": name_col,
        "lon": lon_col,
        "lat": lat_col,
        "ndvi": ndvi_col,
        "lst": lst_col,
        "tdvi": tdvi_col
    }

    # Basic checks
    if detected["name"] is None:
        raise ValueError("Không tìm thấy cột tên xã (cột như tenXa, name, phuong...). Vui lòng kiểm tra file CSV.")
    if detected["lon"] is None or detected["lat"] is None:
        raise ValueError("Không tìm thấy cột toạ độ (POINT_X/POINT_Y hoặc lon/lat). Vui lòng kiểm tra file CSV.")

    # Clean numeric columns: coordinates and numeric values
    # Coordinates may use comma decimal; coerce them.
    df[detected["lon"]] = coerce_numeric_column(df, detected["lon"])
    df[detected["lat"]] = coerce_numeric_column(df, detected["lat"])

    for key in ("ndvi", "lst", "tdvi"):
        col = detected.get(key)
        if col and col in df.columns:
            df[col] = coerce_numeric_column(df, col)

    # Drop rows without valid coordinates
    df = df.dropna(subset=[detected["lon"], detected["lat"]]).reset_index(drop=True)

    return df, detected

# -------------------------
# App UI & Logic
# -------------------------
def main():
    st.set_page_config(page_title="Map & Scatter Tool v3.0", layout="wide")
    st.title("🗺️ Công cụ phân tích NDVI – LST (v3.0)")

    # Sidebar: file uploader and options
    st.sidebar.header("Dữ liệu & Tùy chọn")
    uploaded = st.sidebar.file_uploader("Upload CSV (hoặc để trống dùng file mặc định)", type=["csv", "txt"])
    use_default = False
    if uploaded is None:
        # try default file in working dir
        default_path = "1_1_2018.csv"
        try:
            with open(default_path, "rb") as fh:
                df, detected = load_and_prepare(default_path)
                use_default = True
        except FileNotFoundError:
            st.sidebar.info("Upload file CSV hoặc đặt file '1_1_2018.csv' vào folder app.")
            st.stop()
        except Exception as e:
            st.sidebar.error(f"Lỗi khi đọc file mặc định: {e}")
            st.stop()
    else:
        try:
            # st.file_uploader returns UploadedFile which pandas can read; pass buffer
            df, detected = load_and_prepare(uploaded)
        except Exception as e:
            st.sidebar.error("Lỗi khi đọc file upload: " + str(e))
            st.stop()

    # Show summary of detected columns
    st.sidebar.markdown("**Cột được phát hiện**")
    st.sidebar.write(detected)

    name_col = detected["name"]
    lon_col = detected["lon"]
    lat_col = detected["lat"]
    ndvi_col = detected["ndvi"]
    lst_col = detected["lst"]
    tdvi_col = detected["tdvi"]

    # Basic statistics
    st.sidebar.markdown("---")
    st.sidebar.subheader("Thống kê nhanh")
    if ndvi_col in df.columns:
        st.sidebar.write(f"NDVI — mean: {df[ndvi_col].mean():.3f}  |  min: {df[ndvi_col].min():.3f}  |  max: {df[ndvi_col].max():.3f}")
    else:
        st.sidebar.write("NDVI: Không tìm thấy cột NDVI")
    if lst_col in df.columns:
        st.sidebar.write(f"LST — mean: {df[lst_col].mean():.3f}  |  min: {df[lst_col].min():.2f}  |  max: {df[lst_col].max():.2f}")
    else:
        st.sidebar.write("LST: Không tìm thấy cột LST")

    # Dropdown to select commune
    communes = sorted(df[name_col].dropna().unique().tolist())
    select_commune = st.sidebar.selectbox("Chọn xã/phường (hoặc click marker trên bản đồ)", ["(Tất cả)"] + communes)

    # Map options
    st.sidebar.markdown("---")
    st.sidebar.subheader("Map options")
    show_heatmap = st.sidebar.checkbox("Hiển thị Heatmap (NDVI)", value=False)
    heatmap_radius = st.sidebar.slider("Heatmap radius", 4, 25, 12)
    marker_size = st.sidebar.slider("Kích thước marker", 4, 12, 6)
    color_by_ndvi = st.sidebar.checkbox("Màu marker theo NDVI", value=True)

    # Main layout: tabs
    tab_map, tab_scatter, tab_hist = st.tabs(["Bản đồ", "Scatter NDVI–LST", "Histogram NDVI"])

    # Prepare map
    center_lat = df[lat_col].mean()
    center_lon = df[lon_col].mean()
    folium_map = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="CartoDB positron")

    # Add feature groups
    markers_group = folium.FeatureGroup(name="Markers").add_to(folium_map)
    heat_data = []

    # color scaling for NDVI
    def ndvi_to_color(val):
        # val: numeric or NaN. Return hex color scale from brown (low) to green (high)
        try:
            v = float(val)
        except Exception:
            return "#3388ff"
        # normalize roughly between -0.5 and 1.0 (typical NDVI)
        vmin, vmax = -0.5, 1.0
        t = max(0.0, min(1.0, (v - vmin) / (vmax - vmin)))
        # gradient: brown (#8B4513) -> yellow -> lightgreen -> green
        # simple interpolation between two colors for simplicity: brown -> green
        import math
        r1, g1, b1 = (139, 69, 19)  # brown
        r2, g2, b2 = (34, 139, 34)  # green
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    # Add points and heat data
    for _, row in df.iterrows():
        lat = row[lat_col]
        lon = row[lon_col]
        name = row[name_col]
        ndvi_val = row[ndvi_col] if ndvi_col in df.columns else None
        lst_val = row[lst_col] if lst_col in df.columns else None
        tdvi_val = row[tdvi_col] if (tdvi_col and tdvi_col in df.columns) else None

        if pd.isna(lat) or pd.isna(lon):
            continue

        # popup html
        popup_html = f"<b>{name}</b><br>"
        if ndvi_col in df.columns:
            popup_html += f"NDVI: {ndvi_val if not pd.isna(ndvi_val) else 'NA'}<br>"
        if lst_col in df.columns:
            popup_html += f"LST: {lst_val if not pd.isna(lst_val) else 'NA'}<br>"
        if tdvi_col and tdvi_col in df.columns:
            popup_html += f"TDVI: {tdvi_val if not pd.isna(tdvi_val) else 'NA'}<br>"

        # choose color
        if color_by_ndvi and (ndvi_col in df.columns):
            color = ndvi_to_color(ndvi_val)
            fill_color = color
        else:
            color = "blue"
            fill_color = "cyan"

        marker = folium.CircleMarker(
            location=[lat, lon],
            radius=marker_size,
            color=color,
            fill=True,
            fill_color=fill_color,
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=name
        )
        marker.add_to(markers_group)

        # heatmap weight uses NDVI if available, else 1
        heat_w = float(ndvi_val) if (ndvi_col in df.columns and not pd.isna(ndvi_val)) else 0.5
        heat_data.append([lat, lon, heat_w])

    # Add heatmap layer if requested
    if show_heatmap and len(heat_data) > 0:
        HeatMap(heat_data, radius=heatmap_radius, min_opacity=0.2, max_zoom=13).add_to(folium_map)

    # Add layer control
    folium.LayerControl().add_to(folium_map)

    # Render Map tab
    with tab_map:
        st.subheader("Bản đồ tương tác")
        map_return = st_folium(folium_map, width="100%", height=650)

        # map_return may contain 'last_object_clicked' or 'last_object_clicked_popup'
        clicked_popup = None
        if isinstance(map_return, dict):
            # new versions: 'last_object_clicked_popup' exists when clicking popup text
            clicked_popup = map_return.get("last_object_clicked_popup") or map_return.get("last_object_clicked", {}).get("popup") if map_return.get("last_object_clicked") else None
            # sometimes last_object_clicked contains lat/lng only
            last_clicked = map_return.get("last_clicked")
            if last_clicked and not clicked_popup:
                # try to find nearest point by lat/lng
                try:
                    lat = last_clicked.get("lat")
                    lon = last_clicked.get("lng")
                    # find nearest commune within small tolerance
                    dists = ((df[lat_col] - lat)**2 + (df[lon_col] - lon)**2)
                    idx = dists.idxmin()
                    # ensure distance reasonable
                    if dists.iloc[idx] < 1.0:  # threshold squared deg ~ safe
                        clicked_popup = df.loc[idx, name_col]
                except Exception:
                    clicked_popup = None

        # Determine active commune: click overrides dropdown
        active_commune = select_commune
        if clicked_popup:
            active_commune = clicked_popup

        if active_commune != "(Tất cả)":
            st.info(f"Đang xem: {active_commune}")

    # Scatter Tab: NDVI vs LST
    with tab_scatter:
        st.subheader("Scatter: NDVI vs LST")
        if (ndvi_col not in df.columns) or (lst_col not in df.columns):
            st.warning("Thiếu NDVI hoặc LST. Không thể hiển thị scatter.")
        else:
            # if a specific commune selected, show its points (usually 1) and context
            if active_commune != "(Tất cả)":
                subset = df[df[name_col] == active_commune]
                if subset.empty:
                    st.warning("Không tìm thấy dữ liệu cho xã đã chọn.")
                else:
                    fig = px.scatter(subset, x=ndvi_col, y=lst_col, hover_name=name_col,
                                     title=f"NDVI vs LST — {active_commune}",
                                     labels={ndvi_col: "NDVI", lst_col: "LST"})
                    # add trendline if more than 1 point
                    if len(subset) > 1:
                        fig = px.scatter(subset, x=ndvi_col, y=lst_col, trendline="ols", hover_name=name_col,
                                         title=f"NDVI vs LST — {active_commune}", labels={ndvi_col: "NDVI", lst_col: "LST"})
                    st.plotly_chart(fig, use_container_width=True)
                    # show stats
                    st.write(subset[[ndvi_col, lst_col]].describe().loc[["mean","min","max"]])
            else:
                # show all points colored by NDVI or by commune
                color_mode = st.radio("Color by", options=["NDVI value", "Commune"], index=0, horizontal=True)
                if color_mode == "NDVI value":
                    fig = px.scatter(df, x=ndvi_col, y=lst_col, color=ndvi_col,
                                     hover_name=name_col, title="NDVI vs LST (All communes)",
                                     labels={ndvi_col: "NDVI", lst_col: "LST"})
                else:
                    fig = px.scatter(df, x=ndvi_col, y=lst_col, color=name_col,
                                     hover_name=name_col, title="NDVI vs LST (All communes)",
                                     labels={ndvi_col: "NDVI", lst_col: "LST"})
                st.plotly_chart(fig, use_container_width=True)
                st.write(df[[ndvi_col, lst_col]].describe().loc[["mean","min","max"]])

    # Histogram Tab: NDVI distribution
    with tab_hist:
        st.subheader("Histogram NDVI (phân bố NDVI toàn vùng)")
        if ndvi_col not in df.columns:
            st.warning("Không tìm thấy cột NDVI để vẽ histogram.")
        else:
            bins = st.slider("Số bins", 5, 100, 20)
            fig = px.histogram(df, x=ndvi_col, nbins=bins, title="Histogram NDVI", marginal="box")
            mean_val = df[ndvi_col].mean()
            fig.add_vline(x=mean_val, line_dash="dash", annotation_text=f"Mean: {mean_val:.3f}", annotation_position="top right")
            st.plotly_chart(fig, use_container_width=True)
            st.write(df[ndvi_col].describe().loc[["count","mean","std","min","max"]])

    # Footer / tips
    st.markdown("---")
    st.caption("Gợi ý: Click marker trên bản đồ để xem biểu đồ riêng của xã; hoặc chọn xã trong sidebar. \
               Nếu muốn deploy lên Streamlit Cloud, đừng quên cập nhật requirements.txt với các thư viện cần thiết.")

if __name__ == "__main__":
    main()


