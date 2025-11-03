import os
import re
import sys
import pandas as pd
from datetime import datetime

class DataLoader:
    def __init__(self, data_folder="data"):
        if getattr(sys, 'frozen', False):  # nếu chạy từ file .exe (PyInstaller)
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(os.path.dirname(__file__))
        self.data_folder = os.path.join(base_path, data_folder)
        self.df_long = None  # final long-format dataframe
        self.last_loaded_time = 0  # lưu thời gian tải dữ liệu gần nhất

    def _parse_date_from_filename(self, fname):
        s = re.sub(r'\.csv$', '', fname, flags=re.I)
        m = re.search(r'(\d{1,2})[^\d](\d{1,2})[^\d](\d{4})', s)
        if m:
            day, month, year = m.groups()
            try:
                return datetime(int(year), int(month), int(day)).date()
            except:
                pass
        return None

    def _find_index_cols(self, df):
        cols = df.columns.str.upper()
        col_map = {}
        for idx in ['LST', 'NDVI', 'TVDI']:
            matches = [c for c in df.columns if idx in c.upper()]
            if matches:
                exact = [c for c in matches if c.upper() == idx]
                col_map[idx] = exact[0] if exact else matches[0]
            else:
                col_map[idx] = None
        return col_map

    def _get_latest_mtime(self):
        """Lấy thời gian chỉnh sửa mới nhất trong thư mục data."""
        try:
            mtimes = [
                os.path.getmtime(os.path.join(self.data_folder, f))
                for f in os.listdir(self.data_folder)
                if f.lower().endswith('.csv')
            ]
            return max(mtimes) if mtimes else 0
        except Exception:
            return 0

    def load_all(self, force=False):
        latest_mtime = self._get_latest_mtime()

        # 🔁 Nếu chưa có dữ liệu hoặc thư mục data thay đổi → load lại
        if force or self.df_long is None or latest_mtime != self.last_loaded_time:
            print(f"📂 Đang tải dữ liệu từ: {self.data_folder}")
            frames = []
            for fname in sorted(os.listdir(self.data_folder)):
                if not fname.lower().endswith('.csv'):
                    continue

                path = os.path.join(self.data_folder, fname)
                try:
                    df = pd.read_csv(path, encoding='utf-8-sig')
                except Exception:
                    df = pd.read_csv(path, encoding='latin1')

                date = self._parse_date_from_filename(fname)
                if date is None:
                    date = pd.to_datetime(os.path.getmtime(path), unit='s').date()

                col_map = self._find_index_cols(df)

                lon_col, lat_col = None, None
                for cand in ['toa_do_x', 'lon', 'longitude', 'x']:
                    if cand in df.columns:
                        lon_col = cand
                        break
                for cand in ['toa_do_y', 'lat', 'latitude', 'y']:
                    if cand in df.columns:
                        lat_col = cand
                        break

                rows = []
                for _, r in df.iterrows():
                    ndvi = r.get(col_map['NDVI'])
                    lst = r.get(col_map['LST'])
                    tvdi = r.get(col_map['TVDI'])

                    lon = r.get(lon_col)
                    lat = r.get(lat_col)
                    try:
                        lon, lat = float(lon), float(lat)
                        if lat < 8 or lat > 12 or lon < 105 or lon > 108:
                            lon, lat = lat, lon
                        if not (10 <= lat <= 11.1 and 106 <= lon <= 107.2):
                            continue
                    except:
                        continue

                    row = {
                        'MaPhuong': r.get('ma_xa') or r.get('MaPhuong') or None,
                        'TenPhuong': r.get('ten_xa') or r.get('TenPhuong') or r.get('ten_phuong') or None,
                        'Lon': lon,
                        'Lat': lat,
                        'Date': pd.to_datetime(date),
                        'NDVI': ndvi,
                        'LST': lst,
                        'TVDI': tvdi,
                        'Quan': r.get('ma_tinh') or r.get('ten_tinh') or r.get('Quan') or None,
                        'Landuse': r.get('loai') or None
                    }
                    rows.append(row)

                if rows:
                    frames.append(pd.DataFrame(rows))

            if frames:
                self.df_long = pd.concat(frames, ignore_index=True)
                self.df_long = self.df_long.sort_values(['TenPhuong', 'Date']).reset_index(drop=True)
                print(f"✅ Đã load {len(self.df_long)} dòng dữ liệu.")
            else:
                self.df_long = pd.DataFrame()
                print("⚠️ Không tìm thấy dữ liệu hợp lệ.")

            self.last_loaded_time = latest_mtime

        return self.df_long

    # === Các hàm hỗ trợ ===
    def get_timepoints(self):
        self.load_all()
        return sorted(self.df_long['Date'].dropna().unique())

    def get_values_for_date(self, date, index_name='NDVI'):
        self.load_all()
        date = pd.to_datetime(date)
        return self.df_long[self.df_long['Date'] == date][
            ['MaPhuong', 'TenPhuong', 'Lon', 'Lat', index_name, 'Quan', 'Landuse']
        ].copy()

    def get_series_for_phuong(self, ten_phuong):
        self.load_all()
        return self.df_long[self.df_long['TenPhuong'] == ten_phuong].sort_values('Date')
