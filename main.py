# main.py
import io, sys
from PyQt5 import QtWidgets
from data_loader import DataLoader
from map_view import make_map
from ui_main import MainWindow

def build_app():
    loader = DataLoader(data_folder="data")
    df_long = loader.load_all()
    # default use first date and NDVI
    dates = loader.get_timepoints()
    first = dates[0]
    df_pts = loader.get_values_for_date(first, index_name='NDVI')
    m = make_map(df_pts, index_name='NDVI')
    html = io.BytesIO()
    m.save(html, close_file=False)
    return html.getvalue(), loader

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    map_html, loader = build_app()
    win = MainWindow(map_html, loader)
    win.show()
    sys.exit(app.exec_())
