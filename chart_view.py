# chart_view.py
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import io, base64, pandas as pd
from matplotlib.patches import Polygon

sns.set(style="whitegrid", rc={'figure.figsize': (7, 4)})

def _clean_numeric(series):
    """Chuyển chuỗi có dấu chấm, phẩy thành số thực."""
    return pd.to_numeric(
        series.astype(str)
        .str.replace(r"[^\d\.\-]", "", regex=True)
        .str.replace(r"\.(?=\d{3}(\D|$))", "", regex=True)
        .str.replace(",", ".", regex=True),
        errors="coerce"
    )

def _fig_to_base64(fig, dpi=150):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

def line_series(df_series, index_name='NDVI', title=None):
    df_series[index_name] = _clean_numeric(df_series[index_name])
    fig, ax = plt.subplots(figsize=(6,3))
    ax.plot(df_series['Date'], df_series[index_name], marker='o', linewidth=2)
    ax.set_xlabel('Date'); ax.set_ylabel(index_name)
    if title: ax.set_title(title)
    fig.autofmt_xdate(rotation=40)
    return _fig_to_base64(fig)

def bar_mean_by(df, by='TenPhuong', index_name='NDVI', top_n=20, title=None):
    df[index_name] = _clean_numeric(df[index_name])
    g = df.groupby(by)[index_name].mean().sort_values(ascending=False).head(top_n)
    fig, ax = plt.subplots(figsize=(7,4))
    g.plot(kind='bar', ax=ax)
    ax.set_ylabel(f"Mean {index_name}")
    if title: ax.set_title(title)
    plt.xticks(rotation=90)
    return _fig_to_base64(fig)

def scatter_ndvi_lst(df, x='NDVI', y='LST', c='TVDI', title=None):
    for col in [x, y, c]:
        df[col] = _clean_numeric(df[col])
    fig, ax = plt.subplots(figsize=(6,4))
    sc = ax.scatter(df[x], df[y], c=df[c], cmap='RdYlBu_r', s=50, alpha=0.8, edgecolor='none')
    ax.set_xlabel(x); ax.set_ylabel(y)
    if title: ax.set_title(title)
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label(c)
    return _fig_to_base64(fig)

def boxplot(df, by='TenPhuong', index_name='LST', title=None):
    df[index_name] = _clean_numeric(df[index_name])
    fig, ax = plt.subplots(figsize=(8,4))
    sns.boxplot(x=by, y=index_name, data=df, ax=ax)
    plt.xticks(rotation=90)
    if title: ax.set_title(title)
    return _fig_to_base64(fig)

def histogram(df, col='NDVI', title=None):
    df[col] = _clean_numeric(df[col])
    fig, ax = plt.subplots(figsize=(6,4))
    sns.histplot(df[col].dropna(), kde=True, ax=ax)
    if title: ax.set_title(title)
    return _fig_to_base64(fig)

def corr_matrix(df, cols=['NDVI','LST','TVDI'], title=None):
    df[cols] = df[cols].apply(_clean_numeric)
    cm = df[cols].corr()
    fig, ax = plt.subplots(figsize=(4,4))
    sns.heatmap(cm, annot=True, cmap='coolwarm', ax=ax, vmin=-1, vmax=1)
    if title: ax.set_title(title)
    return _fig_to_base64(fig)

def combination_bar_line(df_series, index_bar='NDVI', index_line='LST', title=None):
    df_series[index_bar] = _clean_numeric(df_series[index_bar])
    df_series[index_line] = _clean_numeric(df_series[index_line])
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
    df_agg[vars_list] = df_agg[vars_list].apply(_clean_numeric)
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
        d[col] = _clean_numeric(d[col])
    if sample_size and len(d) > sample_size:
        d = d.sample(sample_size)
    x, y, c = d[ndvi_col], d[lst_col], d['TVDI']
    fig, ax = plt.subplots(figsize=(6,6))
    sc = ax.scatter(x, y, c=c, cmap='plasma', s=40, edgecolor='none', linewidth=0.2)
    ax.set_xlabel('NDVI'); ax.set_ylabel('LST (°C)')
    if title: ax.set_title(title)
    cbar = fig.colorbar(sc, ax=ax); cbar.set_label('TVDI')
    tri = np.array([[0.0, y.min()], [0.8, y.min()], [0.2, y.max()]])
    poly = Polygon(tri, closed=True, fill=False, edgecolor='gray', linewidth=1.5, linestyle='--')
    ax.add_patch(poly)
    return _fig_to_base64(fig)
