import os
import sys
import winreg
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QIcon, QFont, QColor, QPixmap, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QLabel, QComboBox, QFrame, QLineEdit,
    QStatusBar, QGraphicsDropShadowEffect
)

REG_PATH = r"SOFTWARE\Microsoft\Direct3D"
MODE_DISABLED = "⚪ 未开启 (Disabled)"
MODE_8BIT = "💎 强制 Auto HDR (8-bit)"
MODE_10BIT = "✨ 强制 Auto HDR (10-bit)"

VAL_8BIT = "BufferUpgradeOverride=1"
VAL_10BIT = "BufferUpgradeOverride=1;BufferUpgradeEnable10Bit=1"


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


class AutoHDRManager:
    @staticmethod
    def ensure_root_key():
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as _:
                pass
            return True
        except Exception:
            return False

    @staticmethod
    def list_applications():
        apps = []
        AutoHDRManager.ensure_root_key()
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as root:
                idx = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(root, idx)
                        idx += 1
                        if subkey_name == "MostRecentApplication":
                            continue
                        
                        sub_path = f"{REG_PATH}\\{subkey_name}"
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_path, 0, winreg.KEY_READ) as subkey:
                            try:
                                name_val, _ = winreg.QueryValueEx(subkey, "Name")
                            except FileNotFoundError:
                                name_val = ""
                            
                            try:
                                behav_val, _ = winreg.QueryValueEx(subkey, "D3DBehaviors")
                            except FileNotFoundError:
                                behav_val = ""
                            
                            apps.append({
                                "key_name": subkey_name,
                                "path": name_val,
                                "behavior": behav_val
                            })
                    except OSError:
                        break
        except Exception:
            pass
        return apps

    @staticmethod
    def find_free_subkey():
        AutoHDRManager.ensure_root_key()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as root:
            idx = 0
            while True:
                name = f"Application{idx}"
                try:
                    with winreg.OpenKey(root, name, 0, winreg.KEY_READ):
                        idx += 1
                except FileNotFoundError:
                    return name

    @staticmethod
    def save_app(key_name, path, mode_str):
        AutoHDRManager.ensure_root_key()
        sub_path = f"{REG_PATH}\\{key_name}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_path) as key:
            winreg.SetValueEx(key, "Name", 0, winreg.REG_SZ, path)
            if MODE_10BIT in mode_str:
                winreg.SetValueEx(key, "D3DBehaviors", 0, winreg.REG_SZ, VAL_10BIT)
            elif MODE_8BIT in mode_str:
                winreg.SetValueEx(key, "D3DBehaviors", 0, winreg.REG_SZ, VAL_8BIT)
            else:
                try:
                    winreg.DeleteValue(key, "D3DBehaviors")
                except FileNotFoundError:
                    pass

    @staticmethod
    def delete_app(key_name):
        try:
            sub_path = f"{REG_PATH}\\{key_name}"
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub_path)
            return True
        except Exception:
            return False


class TitleBarButton(QPushButton):
    """自绘矢量的液态玻璃控制按钮（最小化、最大化、关闭）"""
    def __init__(self, btn_type, parent=None):
        super().__init__(parent)
        self.btn_type = btn_type  # 'min', 'max', 'close'
        self.setFixedSize(34, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.is_maximized = False
        
        if self.btn_type == 'close':
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.10);
                    border-radius: 7px;
                }
                QPushButton:hover {
                    background: #EF4444;
                    border: 1px solid #F87171;
                }
                QPushButton:pressed {
                    background: #DC2626;
                }
            """)
        elif self.btn_type == 'max':
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.10);
                    border-radius: 7px;
                }
                QPushButton:hover {
                    background: rgba(56, 189, 248, 0.22);
                    border: 1px solid #38BDF8;
                }
                QPushButton:pressed {
                    background: rgba(56, 189, 248, 0.35);
                }
            """)
        else: # min
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.10);
                    border-radius: 7px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.18);
                    border: 1px solid rgba(255, 255, 255, 0.35);
                }
                QPushButton:pressed {
                    background: rgba(255, 255, 255, 0.25);
                }
            """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen()
        pen.setWidthF(1.7)
        pen.setColor(QColor("#FFFFFF") if self.underMouse() else QColor("#CBD5E1"))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        
        if self.btn_type == 'min':
            painter.drawLine(int(cx - 5), int(cy), int(cx + 5), int(cy))
        elif self.btn_type == 'max':
            if not self.is_maximized:
                painter.drawRoundedRect(int(cx - 4.5), int(cy - 4.5), 9, 9, 1.8, 1.8)
            else:
                painter.drawRoundedRect(int(cx - 3.0), int(cy - 5.5), 8, 8, 1.5, 1.5)
                painter.drawRoundedRect(int(cx - 5.5), int(cy - 3.0), 8, 8, 1.5, 1.5)
        elif self.btn_type == 'close':
            d = 4.2
            painter.drawLine(int(cx - d), int(cy - d), int(cx + d), int(cy + d))
            painter.drawLine(int(cx + d), int(cy - d), int(cx - d), int(cy + d))


class CustomTitleBar(QWidget):
    """自定义液态玻璃无边框标题栏"""
    def __init__(self, parent):
        super().__init__(parent)
        self.win = parent
        self._drag_pos = None
        self.setFixedHeight(44)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(10)

        # 软件图标 (纯彩虹圆环)
        self.icon_label = QLabel()
        icon_path = get_resource_path("icon.png")
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(pix)
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.icon_label)

        # 纯净标题文字
        self.title_label = QLabel("Auto HDR Force")
        self.title_label.setStyleSheet("""
            color: #F8FAFC;
            font-size: 10.5pt;
            font-weight: 800;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self.title_label)

        layout.addStretch()

        # 矢量自绘控制按钮
        self.btn_min = TitleBarButton('min', self)
        self.btn_min.clicked.connect(self.win.showMinimized)
        layout.addWidget(self.btn_min)

        self.btn_max = TitleBarButton('max', self)
        self.btn_max.clicked.connect(self.toggle_max)
        layout.addWidget(self.btn_max)

        self.btn_close = TitleBarButton('close', self)
        self.btn_close.clicked.connect(self.win.close)
        layout.addWidget(self.btn_close)

    def toggle_max(self):
        if self.win.isMaximized():
            self.win.showNormal()
            self.btn_max.is_maximized = False
        else:
            self.win.showMaximized()
            self.btn_max.is_maximized = True
        self.btn_max.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.win.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            if not self.win.isMaximized():
                self.win.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_max()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto HDR Force")
        self.resize(980, 650)
        self.setMinimumSize(840, 520)
        self.setAcceptDrops(True)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)

        icon_path = get_resource_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.all_apps = []
        self.init_ui()
        self.load_data()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(10, 10, 10, 10)

        # 核心液态玻璃卡片容器
        self.root_frame = QFrame()
        self.root_frame.setObjectName("RootFrame")
        self.root_frame.setStyleSheet("""
            QFrame#RootFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0B0F19, stop:0.45 #0F172A, stop:1 #1E1B4B);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 16px;
            }
            QWidget {
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            QToolTip {
                background-color: #1E293B;
                color: #FFFFFF;
                border: 1px solid #38BDF8;
                padding: 6px;
                border-radius: 6px;
                font-size: 9.5pt;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 229, 255, 45))
        shadow.setOffset(0, 4)
        self.root_frame.setGraphicsEffect(shadow)

        frame_layout = QVBoxLayout(self.root_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        # 1. 顶部自定义无边框标题栏
        self.title_bar = CustomTitleBar(self)
        frame_layout.addWidget(self.title_bar)

        # 2. 主体内容布局
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 12, 20, 18)
        content_layout.setSpacing(16)

        # Header 介绍卡片
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background: rgba(30, 41, 59, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
            }
        """)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(18, 14, 18, 14)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(5)
        
        title_row = QHBoxLayout()
        
        title_icon_label = QLabel()
        icon_path = get_resource_path("icon.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            title_icon_label.setPixmap(pixmap)
        title_icon_label.setStyleSheet("background: transparent; border: none; margin-right: 4px;")
        title_row.addWidget(title_icon_label)

        title_label = QLabel("Windows Auto HDR 强制开启管理器")
        title_label.setStyleSheet("""
            font-size: 16.5pt; 
            font-weight: 800; 
            color: #FFFFFF;
            background: transparent;
            border: none;
        """)
        title_row.addWidget(title_label)
        
        self.badge_count = QLabel("已配置 0 款")
        self.badge_count.setStyleSheet("""
            background: rgba(56, 189, 248, 0.25);
            color: #38BDF8;
            border: 1px solid #38BDF8;
            font-size: 9.5pt;
            font-weight: bold;
            padding: 3px 12px;
            border-radius: 12px;
        """)
        title_row.addWidget(self.badge_count)
        title_row.addStretch()
        title_box.addLayout(title_row)

        desc_label = QLabel("为未认证或未自动触发的 Direct3D 游戏强制开启 Win11 高动态范围 (Auto HDR) 渲染与 10-Bit 色深缓冲")
        desc_label.setStyleSheet("color: #CBD5E1; font-size: 10pt; background: transparent; border: none;")
        title_box.addWidget(desc_label)
        h_layout.addLayout(title_box)

        content_layout.addWidget(header_card)

        # 控制操作栏
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(12)

        self.btn_add = QPushButton("➕ 添加游戏 / 程序")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00E5FF, stop:1 #0284C7);
                color: #031424;
                font-size: 10pt;
                font-weight: 800;
                padding: 9px 20px;
                border-radius: 9px;
                border: 1px solid rgba(255, 255, 255, 0.4);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #38BDF8, stop:1 #0EA5E9);
                border: 1px solid #FFFFFF;
            }
            QPushButton:pressed {
                background: #0284C7;
            }
        """)
        self.btn_add.clicked.connect(self.on_add_game)
        ctrl_layout.addWidget(self.btn_add)

        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #F8FAFC;
                font-size: 10pt;
                font-weight: 600;
                padding: 9px 16px;
                border-radius: 9px;
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
                border-color: #38BDF8;
            }
        """)
        self.btn_refresh.clicked.connect(self.load_data)
        ctrl_layout.addWidget(self.btn_refresh)

        # 搜索过滤框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索已添加的游戏名称或路径...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(15, 23, 42, 0.7);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 9px;
                padding: 8px 14px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 1px solid #00E5FF;
                background: rgba(15, 23, 42, 0.95);
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        ctrl_layout.addWidget(self.search_input)

        content_layout.addLayout(ctrl_layout)

        # 游戏列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)

        labels = ["游戏 / 程序名称", "完整路径", "HDR 强制状态", "操作"]
        self.table.setHorizontalHeaderLabels(labels)
        
        for col in range(3):
            item = QTableWidgetItem(labels[col])
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setHorizontalHeaderItem(col, item)
            
        op_item = QTableWidgetItem(labels[3])
        op_item.setTextAlignment(Qt.AlignCenter)
        self.table.setHorizontalHeaderItem(3, op_item)

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 290)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 110)  # 宽度由95扩充为110，彻底根除删除按钮被右侧边缘裁切的问题
        
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(58)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setShowGrid(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 表格 QSS：去除了 item 的水平 padding 截断，消除了多余白线
        self.table.setStyleSheet("""
            QTableWidget {
                background: rgba(15, 23, 42, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                padding: 0px;
                color: #FFFFFF;
                outline: none;
            }
            QTableWidget::item {
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                padding: 0px;
                color: #FFFFFF;
                outline: none;
            }
            QTableWidget::item:selected {
                background: rgba(56, 189, 248, 0.15);
            }
            QHeaderView::section {
                background: rgba(30, 41, 59, 0.95);
                color: #00E5FF;
                font-weight: 800;
                font-size: 10pt;
                padding: 10px 16px;
                border: none;
                border-bottom: 2px solid rgba(0, 229, 255, 0.6);
            }
            QScrollBar:vertical {
                background: rgba(15, 23, 42, 0.5);
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.25);
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00E5FF;
            }
        """)
        content_layout.addWidget(self.table)

        # 底部提示条
        status_bar = QStatusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                color: #94A3B8;
                font-size: 9.5pt;
                background: transparent;
                border: none;
            }
        """)
        content_layout.addWidget(status_bar)
        self.status_bar = status_bar
        self.status_bar.showMessage("💡 提示：可直接拖拽游戏快捷方式或 .exe 进窗口添加；可拖动顶部标题栏移动窗口")

        frame_layout.addWidget(content_widget)
        root_layout.addWidget(self.root_frame)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.exe', '.lnk')):
                self.add_app_entry(file_path)

    def load_data(self):
        self.all_apps = AutoHDRManager.list_applications()
        self.render_table(self.all_apps)
        self.badge_count.setText(f"已配置 {len(self.all_apps)} 款")

    def render_table(self, app_list):
        self.table.setRowCount(0)
        for app in app_list:
            self._insert_table_row(app["key_name"], app["path"], app["behavior"])

    def on_search_changed(self, text):
        query = text.strip().lower()
        if not query:
            self.render_table(self.all_apps)
            return
        
        filtered = [
            app for app in self.all_apps
            if query in os.path.basename(app["path"]).lower() or query in app["path"].lower()
        ]
        self.render_table(filtered)

    def _insert_table_row(self, key_name, path, behavior):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 58)

        file_name = os.path.basename(path) if path else "未命名程序"
        # 游戏名称 (带前置呼吸间距)
        item_name = QTableWidgetItem(f"   🎮  {file_name}")
        item_name.setFont(QFont("Segoe UI", 10, QFont.Bold))
        item_name.setForeground(QColor("#FFFFFF"))
        item_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, item_name)

        # 完整路径
        item_path = QTableWidgetItem(f"   {path}")
        item_path.setToolTip(path)
        item_path.setForeground(QColor("#CBD5E1"))
        item_path.setFont(QFont("Segoe UI", 9))
        item_path.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        item_path.setFlags(item_path.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 1, item_path)

        # 状态下拉框：柔和的半透明液态玻璃边框，去除了刺眼的白线
        combo_container = QWidget()
        combo_layout = QHBoxLayout(combo_container)
        combo_layout.setContentsMargins(16, 0, 16, 0)
        combo_layout.setAlignment(Qt.AlignVCenter)
        
        combo = QComboBox()
        combo.setFixedHeight(34)
        combo.setFocusPolicy(Qt.NoFocus)
        combo.addItems([MODE_10BIT, MODE_8BIT, MODE_DISABLED])
        combo.setStyleSheet("""
            QComboBox {
                background: rgba(30, 41, 59, 0.75);
                color: #FFFFFF;
                font-weight: 600;
                font-size: 9.5pt;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 8px;
                padding-left: 12px;
                outline: none;
            }
            QComboBox:hover {
                background: rgba(30, 41, 59, 0.95);
                border: 1px solid rgba(56, 189, 248, 0.5);
            }
            QComboBox::drop-down {
                border: none;
                width: 26px;
            }
            QComboBox QAbstractItemView {
                background-color: #0F172A;
                color: #FFFFFF;
                selection-background-color: #0284C7;
                selection-color: #FFFFFF;
                border: 1px solid rgba(56, 189, 248, 0.5);
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }
        """)
        
        if VAL_10BIT in behavior:
            combo.setCurrentText(MODE_10BIT)
        elif VAL_8BIT in behavior:
            combo.setCurrentText(MODE_8BIT)
        else:
            combo.setCurrentText(MODE_DISABLED)

        combo.currentTextChanged.connect(
            lambda text, k=key_name, p=path: self.on_mode_changed(k, p, text)
        )
        combo_layout.addWidget(combo)
        self.table.setCellWidget(row, 2, combo_container)

        # 移除按钮：居中放置在 110px 的单元格中，左右预留 21px 充裕呼吸区，彻底杜绝右侧边缘被裁切
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setAlignment(Qt.AlignCenter)
        
        btn_del = QPushButton("移除")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setFixedSize(68, 30)
        btn_del.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.85);
                color: #FFFFFF;
                font-size: 9.5pt;
                font-weight: bold;
                border: 1px solid #F87171;
                border-radius: 7px;
                outline: none;
            }
            QPushButton:hover {
                background: #DC2626;
                border-color: #FFA4A4;
            }
            QPushButton:pressed {
                background: #991B1B;
            }
        """)
        btn_del.clicked.connect(lambda _, k=key_name, p=path: self.on_delete(k, p))
        btn_layout.addWidget(btn_del)
        self.table.setCellWidget(row, 3, btn_container)

    def on_mode_changed(self, key_name, path, mode_str):
        AutoHDRManager.save_app(key_name, path, mode_str)
        self.status_bar.showMessage(f"✨ 成功更新 [{os.path.basename(path)}] -> {mode_str}", 4000)

    def on_delete(self, key_name, path):
        reply = QMessageBox.question(
            self, "确认移除配置",
            f"确定要从注册表中移除游戏：\n\n【{path}】\n\n的 Auto HDR 强制配置吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if AutoHDRManager.delete_app(key_name):
                self.load_data()
                self.status_bar.showMessage(f"🗑️ 已成功移除配置: {os.path.basename(path)}", 4000)
            else:
                QMessageBox.warning(self, "错误", "未能成功移除注册表项。")

    def on_add_game(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择游戏执行文件或快捷方式", "", "游戏可执行程序与快捷方式 (*.exe *.lnk);;所有文件 (*.*)"
        )
        if file_path:
            self.add_app_entry(file_path.replace("/", "\\"))

    def add_app_entry(self, full_path):
        for app in self.all_apps:
            if app["path"].lower() == full_path.lower():
                QMessageBox.information(self, "提示", f"该游戏已在列表中，无需重复添加：\n\n{full_path}")
                return

        new_key = AutoHDRManager.find_free_subkey()
        AutoHDRManager.save_app(new_key, full_path, MODE_10BIT)
        self.load_data()
        self.status_bar.showMessage(f"🎉 成功添加新游戏: {os.path.basename(full_path)} (默认启用 10-bit Auto HDR)", 5000)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    
    icon_path = get_resource_path("icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
