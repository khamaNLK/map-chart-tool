import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import io, base64, re, os, sys, json, warnings
import pandas as pd
from matplotlib.patches import Polygon

sns.set(style="whitegrid", rc={'figure.figsize':(7,4)})

warnings.filterwarnings("ignore", category=UserWarning)

# =========================================================
# 🔹 Utility chung
# =========================================================

def _fig_to_base64(fig, dpi=150):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

def _safe_float(x):
    """Chuyển đổi an toàn sang float (bỏ dấu . hoặc , trong số liệu)."""
    if pd.isna(x): 
        return np.nan
    if isinstance(x, (int, float)): 
        return float(x)
    s = str(x).strip()
    s = re.sub(r'[^0-9,\.\-]', '', s)
    s = s.replace(',', '.')
    try:
        # xử lý kiểu 10.759.047 hoặc 10,759,047
        s = re.sub(r'(?<=\d)\.(?=\d{3}\b)', '', s)
        return float(s)
    except:
        return np.nan

# =========================================================
# 🔹 CÁC HÀM VẼ BIỂU ĐỒ
# =========================================================

def line_series(df_series, index_name='NDVI', title=None):
    fig, ax = plt.subplots(figsize=(6,3))
    ax.plot(df_series['Date'], df_series[index_name], marker='o', linewidth=2)
    ax.set_xlabel('Date'); ax.set_ylabel(index_name)
    if title: ax.set_title(title)
    fig.autofmt_xdate(rotation=40)
    return _fig_to_base64(fig)

def bar_mean_by(df, by='TenPhuong', index_name='NDVI', top_n=20, title=None):
    g = df.groupby(by)[index_name].mean().sort_values(ascending=False).head(top_n)
    fig, ax = plt.subplots(figsize=(7,4))
    g.plot(kind='bar', ax=ax)
    ax.set_ylabel(f"Mean {index_name}")
    if title: ax.set_title(title)
    plt.xticks(rotation=90)
    return _fig_to_base64(fig)

def scatter_ndvi_lst(df, x='NDVI', y='LST', c='TVDI', title=None):
    df = df.copy()
    for col in [x, y, c]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=[x, y])
    if df.empty:
        raise ValueError("Không đủ dữ liệu để vẽ scatter NDVI-LST.")

    fig, ax = plt.subplots(figsize=(6,4))
    sc = ax.scatter(df[x], df[y], c=df[c], cmap='RdYlBu_r', s=50, alpha=0.8, edgecolor='k', linewidth=0.3)
    ax.set_xlabel(x); ax.set_ylabel(y)
    if title: ax.set_title(title)
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label(c)
    return _fig_to_base64(fig)

def boxplot(df, by='TenPhuong', index_name='LST', title=None):
    fig, ax = plt.subplots(figsize=(8,4))
    sns.boxplot(x=by, y=index_name, data=df, ax=ax)
    plt.xticks(rotation=90)
    if title: ax.set_title(title)
    return _fig_to_base64(fig)

def histogram(df, col='NDVI', title=None):
    fig, ax = plt.subplots(figsize=(6,4))
    sns.histplot(df[col].dropna(), kde=True, ax=ax)
    if title: ax.set_title(title)
    return _fig_to_base64(fig)

def corr_matrix(df, cols=['NDVI','LST','TVDI'], title=None):
    cm = df[cols].corr()
    fig, ax = plt.subplots(figsize=(4,4))
    sns.heatmap(cm, annot=True, cmap='coolwarm', ax=ax, vmin=-1, vmax=1)
    if title: ax.set_title(title)
    return _fig_to_base64(fig)

def combination_bar_line(df_series, index_bar='NDVI', index_line='LST', title=None):
    fig, ax1 = plt.subplots(figsize=(7,4))
    ax1.bar(df_series['Date'], df_series[index_bar], alpha=0.7, label=index_bar)
    ax1.set_xlabel('Date')
    ax1.set_ylabel(index_bar)
    ax2 = ax1.twinx()
    ax2.plot(df_series['Date'], df_series[index_line], color='red', marker='o', label=index_line)
    ax2.set_ylabel(index_line)
    if title: ax1.set_title(title)
    fig.autofmt_xdate(rotation=40)
    return _fig_to_base64(fig)

def radar_chart(df_agg, vars_list=['NDVI','LST','TVDI'], groups=None, title=None):
    labels = vars_list
    N = len(labels)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(polar=True))
    for g in (groups if groups is not None else df_agg.index.tolist()):
        values = df_agg.loc[g, labels].tolist()
        values += values[:1]
        ax.plot(angles, values, label=str(g))
        ax.fill(angles, values, alpha=0.15)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    if title: ax.set_title(title)
    ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
    return _fig_to_base64(fig)

def tvdi_triangle(df, ndvi_col='NDVI', lst_col='LST', title=None, sample_size=None):
    d = df.copy()
    for col in [ndvi_col, lst_col, 'TVDI']:
        d[col] = pd.to_numeric(d[col], errors='coerce')
    d = d.dropna(subset=[ndvi_col, lst_col])
    if sample_size and len(d) > sample_size:
        d = d.sample(sample_size)

    x = d[ndvi_col].astype(float)
    y = d[lst_col].astype(float)
    c = d['TVDI'].astype(float) if 'TVDI' in d.columns else None

    fig, ax = plt.subplots(figsize=(6,6))
    sc = ax.scatter(x, y, c=c, cmap='plasma', s=40, edgecolor='k', linewidth=0.2)
    ax.set_xlabel('NDVI'); ax.set_ylabel('LST (°C)')
    if title: ax.set_title(title)
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label('TVDI')

    tri = np.array([[0.0, min(y)], [0.8, min(y)], [0.2, max(y)]])
    poly = Polygon(tri, closed=True, fill=False, edgecolor='gray', linewidth=1.5, linestyle='--')
    ax.add_patch(poly)
    return _fig_to_base64(fig)

# =========================================================
# 🔹 DATALOADER NÂNG CẤP
# =========================================================

class DataLoader:
    def __init__(self, data_folder="data"):
        base_path = os.path.abspath(os.path.dirname(__file__))
        self.data_folder = os.path.join(base_path, data_folder)
        self.df_long = None
        self.last_loaded_time = 0

    def _parse_date_from_filename(self, fname):
        m = re.search(r'(\d{1,2})[^\d](\d{1,2})[^\d](\d{4})', fname)
        if m:
            d, mth, y = m.groups()
            try:
                return pd.to_datetime(f"{y}-{mth}-{d}")
            except:
                pass
        return None

    def _find_cols(self, df):
        cols = df.columns.str.lower()
        def match(keys):
            for k in keys:
                idx = [c for c in df.columns if k in c.lower()]
                if idx: return idx[0]
            return None
        return {
            'NDVI': match(['ndvi']),
            'LST': match(['lst']),
            'TVDI': match(['tvdi']),
            'lon': match(['lon','toa_do_x','longitude','x']),
            'lat': match(['lat','toa_do_y','latitude','y']),
            'ma_xa': match(['ma_xa','maphuong']),
            'ten_xa': match(['ten_xa','tenphuong']),
            'quan': match(['quan','tinh']),
            'landuse': match(['loai'])
        }

    def load_all(self, force=False):
        mtimes = [os.path.getmtime(os.path.join(self.data_folder, f)) for f in os.listdir(self.data_folder) if f.lower().endswith('.csv')]
        latest_mtime = max(mtimes) if mtimes else 0
        if not force and self.df_long is not None and self.last_loaded_time == latest_mtime:
            return self.df_long

        frames = []
        for f in sorted(os.listdir(self.data_folder)):
            if not f.lower().endswith('.csv'):
                continue
            path = os.path.join(self.data_folder, f)
            try:
                df = pd.read_csv(path, encoding='utf-8-sig', sep=None, engine='python', dtype=str)
            except Exception:
                df = pd.read_csv(path, encoding='latin1', sep=None, engine='python', dtype=str)
            cols = self._find_cols(df)
            date = self._parse_date_from_filename(f) or pd.to_datetime(os.path.getmtime(path), unit='s')
            rows = []
            for _, r in df.iterrows():
                try:
                    lon = _safe_float(r.get(cols['lon']))
                    lat = _safe_float(r.get(cols['lat']))
                    if not (8 < lat < 12 and 105 < lon < 108): 
                        continue
                    rows.append({
                        'MaPhuong': r.get(cols['ma_xa']),
                        'TenPhuong': r.get(cols['ten_xa']),
                        'Quan': r.get(cols['quan']),
                        'Landuse': r.get(cols['landuse']),
                        'Date': date,
                        'Lon': lon,
                        'Lat': lat,
                        'NDVI': _safe_float(r.get(cols['NDVI'])),
                        'LST': _safe_float(r.get(cols['LST'])),
                        'TVDI': _safe_float(r.get(cols['TVDI']))
                    })
                except:
                    continue
            if rows:
                frames.append(pd.DataFrame(rows))

        self.df_long = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        self.last_loaded_time = latest_mtime
        print(f"✅ Loaded {len(self.df_long)} rows total.")
        return self.df_long

    def get_timepoints(self):
        self.load_all()
        return sorted(self.df_long['Date'].dropna().unique())

    def get_values_for_date(self, date, index_name='NDVI'):
        self.load_all()
        date = pd.to_datetime(date)
        df = self.df_long[self.df_long['Date'] == date]
        return df[['MaPhuong','TenPhuong','Lon','Lat',index_name,'Quan','Landuse','NDVI','LST','TVDI']].copy()

    def get_series_for_phuong(self, ten_phuong):
        self.load_all()
        return self.df_long[self.df_long['TenPhuong'] == ten_phuong].sort_values('Date')
