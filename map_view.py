# map_view.py — phiên bản chuẩn, hiển thị ranh giới TP.HCM thật
import folium
import pandas as pd
import os, json
from folium import CircleMarker

def make_map(df_points, index_name='NDVI'):
    # ✅ Tâm bản đồ đặt giữa TP.HCM
    center = [10.7769, 106.7009]
    m = folium.Map(location=center, zoom_start=11, tiles='CartoDB positron')

    # ✅ 1. Vẽ ranh giới thật TP.HCM (nếu có file geojson)
    geojson_path = os.path.join("data", "tp_hcm.geojson")
    if os.path.exists(geojson_path):
        try:
            with open(geojson_path, encoding="utf-8-sig") as f:  # ⚠️ dòng quan trọng để tránh lỗi JSON
                gj = json.load(f)
            folium.GeoJson(
                gj,
                name="TP. Hồ Chí Minh",
                style_function=lambda x: {
                    'color': '#1976d2',
                    'weight': 2.5,
                    'fillOpacity': 0.05
                },
                tooltip="Ranh giới TP. Hồ Chí Minh"
            ).add_to(m)
        except Exception as e:
            print("⚠️ Lỗi khi đọc tp_hcm.geojson:", e)
    else:
        print("⚠️ Không tìm thấy file tp_hcm.geojson trong thư mục data/")

    # ✅ 2. Vẽ các điểm dữ liệu
    vals = df_points[index_name].astype(float)
    vmin, vmax = float(vals.min()), float(vals.max())

    import matplotlib.cm as cm, matplotlib.colors as colors
    cmap = cm.get_cmap('RdYlBu_r')

    def color_for(v):
        try:
            t = (float(v) - vmin) / (vmax - vmin) if vmax > vmin else 0.5
        except:
            t = 0.5
        rgba = cmap(t)
        return colors.to_hex(rgba)

    for _, r in df_points.iterrows():
        lat, lon = r['Lat'], r['Lon']
        if pd.isna(lat) or pd.isna(lon):
            continue
        popup_html = f"""
        <b>{r['TenPhuong']}</b><br>
        <b>{index_name}</b>: {r[index_name]}<br>
        NDVI: {r.get('NDVI')}<br>
        LST: {r.get('LST')}<br>
        TVDI: {r.get('TVDI')}
        """
        CircleMarker(
            location=[lat, lon],
            radius=6,
            color=color_for(r[index_name]),
            fill=True,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)

    # ✅ 3. Thêm tiêu đề overlay (hiển thị trên bản đồ)
    title_html = '''
        <div style="
            position: fixed;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            background-color: rgba(255,255,255,0.9);
            padding: 6px 15px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            color: #01579b;
            box-shadow: 0px 2px 6px rgba(0,0,0,0.2);
        ">
        Khu vực nghiên cứu: TP. Hồ Chí Minh (2023)
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    return m
