# ui_main.py — bản hoàn thiện, hỗ trợ đầy đủ tất cả loại biểu đồ và giao diện đẹp
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWebEngineWidgets import QWebEngineView
import base64, os, pandas as pd

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, map_html_bytes, loader):
        super().__init__()
        self.loader = loader
        self.setWindowTitle("🌆 LST / NDVI / TVDI Explorer — TP. Hồ Chí Minh 2023")
        self.resize(1600, 900)
        self._current_chart_b64 = None

        # ===== HEADER =====
        header = QtWidgets.QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #0d47a1;
                padding: 12px;
            }
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
        """)
        hbox = QtWidgets.QHBoxLayout(header)
        hbox.addWidget(QtWidgets.QLabel("🌆 Urban Climate Dashboard — TP. Hồ Chí Minh 2023"))
        hbox.addStretch()

        # ===== BODY =====
        body = QtWidgets.QWidget()
        body_layout = QtWidgets.QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)

        # --- LEFT: MAP ---
        self.web = QWebEngineView()
        self.web.setHtml(map_html_bytes.decode())
        body_layout.addWidget(self.web, 3)

        # --- RIGHT: CONTROL PANEL ---
        right_panel = QtWidgets.QScrollArea()
        right_panel.setWidgetResizable(True)
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_panel.setWidget(right_widget)

        # === GROUP 1: Dataset ===
        group1 = QtWidgets.QGroupBox("⚙️ Cấu hình hiển thị")
        g1 = QtWidgets.QFormLayout(group1)
        g1.setLabelAlignment(QtCore.Qt.AlignLeft)

        self.combo_index = QtWidgets.QComboBox()
        self.combo_index.addItems(["NDVI", "LST", "TVDI"])
        g1.addRow("Chỉ số hiển thị:", self.combo_index)

        self.combo_chart = QtWidgets.QComboBox()
        self.combo_chart.addItems([
            "Line chart (diễn biến theo thời gian)",
            "Bar chart (trung bình theo phường)",
            "Scatter NDVI-LST (màu TVDI)",
            "Boxplot (phân bố theo phường)",
            "Histogram / Density",
            "Combination (Bar + Line)",
            "Radar chart (so sánh trung bình)",
            "Correlation matrix (NDVI-LST-TVDI)",
            "TVDI Triangle"
        ])
        g1.addRow("Loại biểu đồ:", self.combo_chart)

        self.combo_date = QtWidgets.QComboBox()
        for d in self.loader.get_timepoints():
            self.combo_date.addItem(str(d))
        g1.addRow("Thời điểm:", self.combo_date)

        self.combo_quan = QtWidgets.QComboBox()
        self.combo_quan.addItem("Tất cả")
        quans = sorted(self.loader.df_long['Quan'].dropna().unique())
        for q in quans:
            self.combo_quan.addItem(str(q))
        g1.addRow("Quận:", self.combo_quan)

        self.combo_phuong = QtWidgets.QComboBox()
        phuongs = sorted(self.loader.df_long['TenPhuong'].dropna().unique())
        self.combo_phuong.addItems(phuongs)
        g1.addRow("Phường:", self.combo_phuong)

              # === GROUP 2: Buttons ===
        group2 = QtWidgets.QGroupBox("📈 Thao tác biểu đồ")
        g2 = QtWidgets.QHBoxLayout(group2)
        self.btn_show = QtWidgets.QPushButton("Hiển thị")
        self.btn_export = QtWidgets.QPushButton("Lưu biểu đồ")
        self.btn_reload = QtWidgets.QPushButton("🔄 Làm mới dữ liệu")  # Nút reload mới
        g2.addWidget(self.btn_show)
        g2.addWidget(self.btn_export)
        g2.addWidget(self.btn_reload)

        # Gắn sự kiện
        self.btn_show.clicked.connect(self.update_chart)
        self.btn_export.clicked.connect(self.export_chart)
        self.btn_reload.clicked.connect(self.refresh_comboboxes)  # Gọi hàm reload

        # === GROUP 3: Chart display ===
        group3 = QtWidgets.QGroupBox("📊 Kết quả biểu đồ")
        g3 = QtWidgets.QVBoxLayout(group3)
        self.chart_label = QtWidgets.QLabel()
        self.chart_label.setFixedSize(540, 420)
        self.chart_label.setAlignment(QtCore.Qt.AlignCenter)
        self.chart_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 1px solid #cfd8dc;
                border-radius: 8px;
            }
        """)
        g3.addWidget(self.chart_label)

        # === Add all ===
        right_layout.addWidget(group1)
        right_layout.addWidget(group2)
        right_layout.addWidget(group3)
        right_layout.addStretch()

        body_layout.addWidget(right_panel, 2)

        # === COMBINE HEADER + BODY ===
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(header)
        layout.addWidget(body)
        self.setCentralWidget(container)

    # ====== HÀM LÀM MỚI DỮ LIỆU ======
    def refresh_comboboxes(self):
        """Reload toàn bộ dữ liệu và cập nhật combobox."""
        self.loader.load_all(force=True)

        # Cập nhật lại combobox thời gian
        self.combo_date.clear()
        for d in self.loader.get_timepoints():
            self.combo_date.addItem(str(d))

        # Cập nhật lại combobox quận
        self.combo_quan.clear()
        self.combo_quan.addItem("Tất cả")
        quans = sorted(self.loader.df_long['Quan'].dropna().unique())
        for q in quans:
            self.combo_quan.addItem(str(q))

        # Cập nhật lại combobox phường
        self.combo_phuong.clear()
        phuongs = sorted(self.loader.df_long['TenPhuong'].dropna().unique())
        self.combo_phuong.addItems(phuongs)

        QtWidgets.QMessageBox.information(self, "Cập nhật", "✅ Dữ liệu mới đã được nạp thành công.")

    # ====== LOGIC VẼ BIỂU ĐỒ ======
    def update_chart(self):
        import chart_view as charts
        self.loader.load_all(force=True)
        idx = self.combo_index.currentText()
        chart_type = self.combo_chart.currentText()
        phuong = self.combo_phuong.currentText()
        quan = self.combo_quan.currentText()
        date = self.combo_date.currentText()

        df = self.loader.df_long.copy()
        if quan != "Tất cả":
            df = df[df['Quan'] == quan]

        # Chuyển cột sang số an toàn
        for col in ['NDVI', 'LST', 'TVDI']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        b64 = None
        try:
            if "Line" in chart_type:
                series = self.loader.get_series_for_phuong(phuong)
                if series.empty:
                    raise ValueError("Không có dữ liệu cho phường đã chọn.")
                b64 = charts.line_series(series, index_name=idx, title=f"{phuong} — {idx}")

            elif "Bar" in chart_type:
                if df.empty:
                    raise ValueError("Không có dữ liệu hợp lệ.")
                b64 = charts.bar_mean_by(df, by="TenPhuong", index_name=idx, title="Trung bình theo phường")

            elif "Scatter" in chart_type:
                date_df = self.loader.get_values_for_date(date, index_name=idx).dropna(subset=['NDVI','LST','TVDI'])
                if date_df.empty:
                    raise ValueError("Không có dữ liệu cho ngày đã chọn.")
                b64 = charts.scatter_ndvi_lst(date_df, title=f"NDVI–LST–TVDI ({date})")

            elif "Boxplot" in chart_type:
                date_df = self.loader.get_values_for_date(date, index_name=idx)
                if date_df.empty:
                    raise ValueError("Không có dữ liệu boxplot.")
                b64 = charts.boxplot(date_df, index_name=idx, title=f"Phân bố {idx} theo phường")

            elif "Histogram" in chart_type:
                date_df = self.loader.get_values_for_date(date, index_name=idx)
                b64 = charts.histogram(date_df, col=idx, title=f"Phân bố {idx}")

            elif "Combination" in chart_type:
                series = self.loader.get_series_for_phuong(phuong)
                if series.empty:
                    raise ValueError("Không có dữ liệu để vẽ biểu đồ kết hợp.")
                b64 = charts.combination_bar_line(series, index_bar="NDVI", index_line="LST", title=f"{phuong} — NDVI/LST")

            elif "Radar" in chart_type:
                agg = df.groupby("Quan")[["NDVI", "LST", "TVDI"]].mean().dropna()
                if len(agg) < 2:
                    raise ValueError("Cần ít nhất 2 quận để vẽ radar chart.")
                b64 = charts.radar_chart(agg, title="So sánh trung bình NDVI/LST/TVDI giữa các quận")

            elif "Correlation" in chart_type:
                if df[['NDVI','LST','TVDI']].dropna().empty:
                    raise ValueError("Không đủ dữ liệu để tính tương quan.")
                b64 = charts.corr_matrix(df, title="Tương quan NDVI–LST–TVDI")

            elif "Triangle" in chart_type:
                date_df = self.loader.get_values_for_date(date, index_name=idx).dropna(subset=['NDVI','LST','TVDI'])
                if date_df.empty:
                    raise ValueError("Không đủ dữ liệu để vẽ TVDI Triangle.")
                b64 = charts.tvdi_triangle(date_df, title=f"TVDI Triangle ({date})")

            if b64:
                self._set_chart(b64)
            else:
                QtWidgets.QMessageBox.warning(self, "Thiếu dữ liệu", "Không thể vẽ biểu đồ cho lựa chọn này.")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Lỗi", str(e))

    def _set_chart(self, b64):
        pix = QtGui.QPixmap()
        pix.loadFromData(base64.b64decode(b64))
        self.chart_label.setPixmap(pix.scaled(self.chart_label.size(), QtCore.Qt.KeepAspectRatio))
        self._current_chart_b64 = b64

    def export_chart(self):
        if not self._current_chart_b64:
            QtWidgets.QMessageBox.warning(self, "Chưa có biểu đồ", "Hãy tạo biểu đồ trước khi lưu.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Lưu biểu đồ", "", "PNG Image (*.png);;PDF File (*.pdf)")
        if not path:
            return
        from export_util import save_b64_to_file
        if path.endswith(".pdf"):
            from matplotlib.backends.backend_pdf import PdfPages
            import io, base64, matplotlib.pyplot as plt, PIL.Image as Image
            data = base64.b64decode(self._current_chart_b64)
            image = Image.open(io.BytesIO(data))
            pdf = PdfPages(path)
            fig, ax = plt.subplots()
            ax.axis("off")
            ax.imshow(image)
            pdf.savefig(fig)
            pdf.close()
        else:
            save_b64_to_file(self._current_chart_b64, path)
        QtWidgets.QMessageBox.information(self, "Hoàn tất", f"Đã lưu biểu đồ tại:\n{path}")
