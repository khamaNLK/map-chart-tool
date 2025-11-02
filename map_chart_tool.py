"""
map_chart_tool.py

This file is a resilient prototype for a Map ↔ Chart tool for phường/xã-level data.

Behavior:
- If `streamlit` is installed and importable, the script will run as a Streamlit app (interactive web UI).
- If `streamlit` is NOT installed, the script falls back to a CLI/static mode: it will create two self-contained HTML files in the current directory:
    - `map_output.html` (folium map with markers or choropleth-like polygons)
    - `chart_output.html` (plotly interactive chart)
  and print instructions to the console.

This fallback lets you run the same code on environments where Streamlit is unavailable (avoids ModuleNotFoundError on import).

Notes:
- For the full interactive experience (Streamlit app), install dependencies listed in `requirements.txt`:
    pip install streamlit pandas geopandas folium streamlit-folium plotly shapely pyproj

- The CLI mode still requires: pandas, folium, plotly. Geo features will be created from lat/lng if GeoPandas is not available.

"""

import sys
from pathlib import Path

# Try to import optional libraries and set flags
HAS_STREAMLIT = True
try:
    import streamlit as st
    from streamlit_folium import st_folium
except Exception:
    HAS_STREAMLIT = False

HAS_PANDAS = True
try:
    import pandas as pd
except Exception:
    HAS_PANDAS = False

HAS_GEOPANDAS = True
try:
    import geopandas as gpd
    from shapely.geometry import Point
except Exception:
    HAS_GEOPANDAS = False
    try:
        from shapely.geometry import Point
    except Exception:
        Point = None

HAS_FOLIUM = True
try:
    import folium
except Exception:
    HAS_FOLIUM = False

HAS_PLOTLY = True
try:
    import plotly.express as px
    import plotly.io as pio
except Exception:
    HAS_PLOTLY = False


# Utility: create sample dataframe
def create_sample_df():
    if not HAS_PANDAS:
        raise RuntimeError("pandas is required to create sample data. Please install pandas.")
    return pd.DataFrame([
        {"id":"07901","name":"Phường A","lat":10.7626,"lng":106.6602,"value_2023":123,"population":15000},
        {"id":"07902","name":"Phường B","lat":10.7650,"lng":106.6630,"value_2023":95,"population":9000},
        {"id":"07903","name":"Phường C","lat":10.7580,"lng":106.6550,"value_2023":210,"population":20000},
        {"id":"07904","name":"Phường D","lat":10.7550,"lng":106.6700,"value_2023":60,"population":5000},
    ])


# Core logic to produce folium.Map and plotly figure from a DataFrame
def build_map_and_chart(df, value_col=None, marker_mode=True, basemap="OpenStreetMap", chart_type="Bar"):
    # df: pandas DataFrame with at least id, name, lat, lng (or geometry if geopandas)
    # value_col: str name of numeric column to visualize

    if not HAS_PANDAS:
        raise RuntimeError("pandas is required to run this tool")
    # Ensure expected columns
    required = {"id", "name"}
    if not required.issubset(df.columns):
        raise ValueError(f"DataFrame must include columns: {required}. Found: {list(df.columns)}")

    # Detect lat/lng
    has_latlng = {"lat", "lng"}.issubset(df.columns)

    # Auto-detect numeric value column if not provided
    if value_col is None or value_col == "":
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        candidates = [c for c in numeric_cols if c not in ("lat","lng")]
        value_col = candidates[0] if candidates else None

    # Build folium map
    if not HAS_FOLIUM:
        raise RuntimeError("folium is required to create maps. Install folium to use mapping features.")

    if has_latlng:
        center = [df['lat'].mean(), df['lng'].mean()]
    else:
        center = [10.776889, 106.700806]  # fallback center (HCMC)

    # map tiles selection
    tiles = basemap if basemap in ["OpenStreetMap","Stamen Terrain","Stamen Toner"] else "OpenStreetMap"
    m = folium.Map(location=center, zoom_start=13, tiles=tiles)

    if marker_mode:
        # Add markers
        for _, row in df.iterrows():
            if has_latlng:
                popup_html = f"<b>{row.get('name','')}</b>"
                if value_col and value_col in row:
                    popup_html += f"<br>{value_col}: {row.get(value_col,'')}"
                folium.CircleMarker(location=(row['lat'], row['lng']), radius=6, popup=folium.Popup(popup_html, max_width=300), tooltip=row.get('name','')).add_to(m)
    else:
        # Try to produce small polygons (buffers) if geometry exists (geopandas) or lat/lng available
        if HAS_GEOPANDAS and 'geometry' in df.columns:
            gj = gpd.GeoDataFrame(df.copy(), geometry='geometry')
            try:
                folium.GeoJson(gj.to_crs(epsg=4326).to_json(), tooltip=folium.features.GeoJsonTooltip(fields=['name', value_col] if value_col else ['name'])).add_to(m)
            except Exception:
                # fallback to markers
                for _, row in df.iterrows():
                    if has_latlng:
                        folium.CircleMarker(location=(row['lat'], row['lng']), radius=6, popup=row.get('name','')).add_to(m)
        elif has_latlng and Point is not None:
            # create small buffer polygons from points
            try:
                import geopandas as _gpd
                # points_from_xy returns a GeoSeries; we'll iterate and add small buffers as GeoJson
                geo_s = _gpd.points_from_xy(df['lng'], df['lat'])
                temp_gdf = _gpd.GeoDataFrame(df.copy(), geometry=geo_s)
                temp_gdf['poly'] = temp_gdf.geometry.buffer(0.002)
                folium.GeoJson(temp_gdf.set_geometry('poly').to_crs(epsg=4326).to_json(), tooltip=folium.features.GeoJsonTooltip(fields=['name', value_col] if value_col else ['name'])).add_to(m)
            except Exception:
                # create simple circular markers as fallback
                for _, row in df.iterrows():
                    folium.CircleMarker(location=(row['lat'], row['lng']), radius=6, popup=row.get('name','')).add_to(m)
        else:
            # fallback markers
            for _, row in df.iterrows():
                if has_latlng:
                    folium.CircleMarker(location=(row['lat'], row['lng']), radius=6, popup=row.get('name','')).add_to(m)

    # Build plotly figure
    fig = None
    if HAS_PLOTLY and value_col and value_col in df.columns:
        chart_df = df[['id','name',value_col]].copy()
        chart_df = chart_df.sort_values(by=value_col, ascending=False)
        if chart_type == 'Bar':
            fig = px.bar(chart_df, x='name', y=value_col, hover_data=['id'])
        elif chart_type == 'Line':
            fig = px.line(chart_df, x='name', y=value_col, markers=True, hover_data=['id'])
        else:
            fig = px.scatter(chart_df, x='name', y=value_col, size=value_col, hover_data=['id'])
    return m, fig, value_col


# CLI/static fallback
def run_cli_mode(csv_path=None, out_dir='.'):
    print("Running in CLI/static mode (Streamlit not available).\n")
    if not HAS_PANDAS:
        print("Error: pandas is required. Install with: pip install pandas")
        return
    if not HAS_FOLIUM:
        print("Error: folium is required. Install with: pip install folium")
        return
    if not HAS_PLOTLY:
        print("Warning: plotly not installed. Chart HTML will not be produced. Install with: pip install plotly")

    if csv_path is None:
        df = create_sample_df()
        print("Using built-in sample data.")
    else:
        if not Path(csv_path).exists():
            print(f"CSV file not found: {csv_path}")
            return
        df = pd.read_csv(csv_path)
        print(f"Loaded CSV: {csv_path}")

    try:
        m, fig, value_col = build_map_and_chart(df, marker_mode=True)
    except Exception as e:
        print("Error while building map/chart:", e)
        return

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    map_out = out_dir / 'map_output.html'
    m.save(str(map_out))
    print(f"Wrote map to: {map_out.resolve()}")

    if fig is not None and HAS_PLOTLY:
        chart_out = out_dir / 'chart_output.html'
        # Use plotly offline save
        try:
            pio.write_html(fig, file=str(chart_out), auto_open=False)
            print(f"Wrote chart to: {chart_out.resolve()}")
        except Exception as e:
            print("Failed to write chart HTML:", e)
    else:
        print("No chart produced (missing plotly or no numeric column detected).")

    print("\nOpen the generated HTML files in a browser to view the results.")
    print("If you want the full interactive Streamlit app experience, install streamlit and run: pip install streamlit && streamlit run map_chart_tool.py")


# Streamlit UI (if available)
def run_streamlit_app():
    # Note: all imports here should be safe as we've already checked availability
    st.set_page_config(layout="wide", page_title="Tool: Map + Chart for Phường/Xã", initial_sidebar_state="expanded")
    st.title("Tool: Bản đồ ↔ Biểu đồ (Python prototype)")
    st.write("Upload CSV or GeoJSON. CSV must include columns: id, name, lat, lng, and at least one numeric 'value' column.")

    with st.sidebar:
        st.header("Dữ liệu")
        upload = st.file_uploader("Upload CSV or GeoJSON", type=["csv","geojson","json"])
        sample_btn = st.button("Load sample data")

        st.markdown("---")
        st.header("Map settings")
        basemap = st.selectbox("Basemap tiles", ["OpenStreetMap","Stamen Terrain","Stamen Toner"]) if 'basemap' in globals() else st.selectbox("Basemap tiles", ["OpenStreetMap","Stamen Terrain","Stamen Toner"]) 
        marker_type = st.selectbox("Marker / Choropleth", ["Marker (points)", "Choropleth (requires geometry)"])
        st.markdown("---")
        st.header("Chart settings")
        chart_type = st.selectbox("Chart type", ["Bar", "Scatter", "Line"])
        value_column = st.text_input("Value column (auto-detected if left empty)", "")

    # Load data
    if sample_btn or (upload is None and not sample_btn):
        df = create_sample_df()
    else:
        if upload is None:
            st.info("Please upload a CSV or GeoJSON, or press 'Load sample data'.")
            st.stop()
        fname = upload.name.lower()
        if fname.endswith('.csv'):
            df = pd.read_csv(upload)
        elif fname.endswith('.geojson') or fname.endswith('.json'):
            if HAS_GEOPANDAS:
                gj = gpd.read_file(upload)
                if 'geometry' in gj.columns:
                    gj = gj.to_crs(epsg=4326)
                    gj['centroid'] = gj.geometry.centroid
                    gj['lat'] = gj.centroid.y
                    gj['lng'] = gj.centroid.x
                    df = pd.DataFrame(gj.drop(columns=['geometry','centroid']))
                else:
                    df = pd.DataFrame(gj)
            else:
                st.error('GeoJSON upload requires geopandas. Install geopandas or provide CSV with lat/lng.')
                st.stop()
        else:
            st.error('Unsupported file type.')
            st.stop()

    # Validation
    required_cols = {'id','name'}
    if not required_cols.issubset(df.columns):
        st.warning("CSV should contain at least columns: 'id', 'name'. If you have geometry, upload GeoJSON.")
        st.write("Current columns detected: ", df.columns.tolist())
        st.stop()

    has_latlng = {'lat','lng'}.issubset(df.columns)
    if not has_latlng:
        st.error("No 'lat' and 'lng' columns found. For point mapping you need lat/lng; or upload GeoJSON with geometries.")
        st.stop()

    # Auto-detect value column
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    value_col = value_column.strip() if value_column.strip() else None
    if not value_col:
        candidates = [c for c in numeric_cols if c not in ('lat','lng')]
        if candidates:
            value_col = candidates[0]
        else:
            st.warning('No numeric value column found. Add one or edit your CSV.')
            st.stop()

    st.sidebar.markdown(f"Using value column: **{value_col}**")

    # Convert to GeoDataFrame for internal use (if geopandas available)
    if HAS_GEOPANDAS:
        gdf = gpd.GeoDataFrame(df.copy(), geometry=[Point(xy) for xy in zip(df['lng'], df['lat'])], crs='EPSG:4326')
    else:
        gdf = df.copy()

    # Layout
    col1, col2 = st.columns([2,1])
    with col1:
        st.subheader('Bản đồ')
        center = [df['lat'].mean(), df['lng'].mean()] if 'lat' in df and 'lng' in df else [10.776889, 106.700806]
        tiles = 'OpenStreetMap'
        if 'basemap' in locals():
            tiles = basemap
        m = folium.Map(location=center, zoom_start=13, tiles=tiles)

        if marker_type == 'Marker (points)':
            for _, row in df.iterrows():
                folium.CircleMarker(location=(row['lat'], row['lng']), radius=7,
                                    popup=folium.Popup(f"<b>{row['name']}</b><br>{value_col}: {row.get(value_col, '')}", max_width=300),
                                    tooltip=row['name']).add_to(m)
        else:
            # try to draw polygons if geopandas available
            try:
                if HAS_GEOPANDAS and 'geometry' in gdf.columns:
                    folium.GeoJson(gdf.to_crs(epsg=4326).to_json(), tooltip=folium.features.GeoJsonTooltip(fields=['name', value_col] if value_col else ['name'])).add_to(m)
                else:
                    for _, row in df.iterrows():
                        folium.CircleMarker(location=(row['lat'], row['lng']), radius=7, popup=row['name']).add_to(m)
            except Exception as e:
                st.error('Choropleth mode requires geometry or geopandas. Error: ' + str(e))
                st.stop()

        map_data = st_folium(m, width='100%', height=600)

    with col2:
        st.subheader('Biểu đồ')
        st.write('Interactive chart based on value column. Click bars/points to select.')
        chart_df = df[['id','name',value_col,'lat','lng']].copy()
        chart_df = chart_df.sort_values(by=value_col, ascending=False)
        if chart_type == 'Bar':
            fig = px.bar(chart_df, x='name', y=value_col, hover_data=['id','lat','lng'], labels={value_col: value_col, 'name':'Phường/Xã'})
        elif chart_type == 'Line':
            fig = px.line(chart_df, x='name', y=value_col, markers=True, hover_data=['id','lat','lng'])
        else:
            fig = px.scatter(chart_df, x='name', y=value_col, size=value_col, hover_data=['id','lat','lng'])

        st.plotly_chart(fig, use_container_width=True)

        st.markdown('---')
        st.subheader('Bảng dữ liệu')
        selected_idx = st.selectbox('Chọn phường/xã để highlight', options=[None] + chart_df['name'].tolist(), index=0)
        if selected_idx:
            sel_row = chart_df[chart_df['name'] == selected_idx].iloc[0]
            st.write(f"**{sel_row['name']}** — {value_col}: {sel_row[value_col]} — lat/lng: ({sel_row['lat']:.6f}, {sel_row['lng']:.6f})")
            m2 = folium.Map(location=[sel_row['lat'], sel_row['lng']], zoom_start=15, tiles=tiles)
            folium.CircleMarker(location=(sel_row['lat'], sel_row['lng']), radius=10, popup=sel_row['name'], color='red', fill=True).add_to(m2)
            st_folium(m2, width=300, height=300)

    st.markdown('---')
    st.write('Notes: This is a prototype. For large datasets or real administrative boundaries, upload GeoJSON with proper polygons and consider using vector tiles (mbtiles) and server-side tiling.')


if __name__ == '__main__':
    if HAS_STREAMLIT:
        # Running under streamlit: the run_streamlit_app function will be executed by Streamlit when file is run
        # but to be safe we call it when executed directly
        run_streamlit_app()
    else:
        # CLI mode: allow an optional CSV path via argv
        csv_path = sys.argv[1] if len(sys.argv) > 1 else None
        out_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
        run_cli_mode(csv_path=csv_path, out_dir=out_dir)
