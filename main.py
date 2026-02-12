# main.py
# VibeCoding SDD Phase 2.5: Bingo UI Support
# 修正重點：
# 1. 在 Top N 區塊新增 "星數 (Star)" 下拉選單 (僅賓果顯示)
# 2. 調整選號邏輯，支援動態改變 select_count

import sys
import random
import threading
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QTabWidget, QLabel, QPushButton, 
                               QTableWidget, QTableWidgetItem, QHeaderView, 
                               QGroupBox, QSpinBox, QFrame, QFileDialog, 
                               QAbstractItemView, QMessageBox, QTextEdit, QComboBox) # 新增 QComboBox
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QFont, QColor

from config import LOTTERY_CONFIG
from data_manager import DataManager

# ... (HelpWindow, UpdateWorker, InteractiveTable 保持不變，為節省篇幅省略，請保留原程式碼) ...
# 請將 HelpWindow, UpdateWorker, InteractiveTable 的程式碼從上一個版本複製過來，這裡不重複貼上以免混亂

class HelpWindow(QWidget):
    # ... (同前版)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("使用說明文件")
        self.resize(700, 600)
        self.setWindowFlags(Qt.Window)
        layout = QVBoxLayout()
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("font-size: 16px; line-height: 1.6; padding: 15px; background-color: #fff;")
        default_content = """
        <h2 style='color: #0078D7;'>🎲 台彩戰情室 - 操作指南</h2>
        <hr>
        <h3>1. 賓果賓果 (新功能)</h3>
        <ul>
            <li><b>星數玩法</b>：在右側選單選擇「1星」~「10星」，系統會自動調整選號數量。</li>
            <li><b>近期策略</b>：賓果只抓取「最近 5 天」資料，確保分析的是最新趨勢。</li>
        </ul>
        <h3>2. 智慧選號模式</h3>
        <p><b>模式 A：熱門前 N 名篩選</b></p>
        <ul><li>適合想從「最熱門」的一群號碼中隨機挑選的人。</li></ul>
        <p><b>模式 B：排名範圍篩選</b></p>
        <ul><li>適合想避開太熱門的冠軍號，或專挑冷門號的人。</li></ul>
        """
        self.text_area.setHtml(default_content)
        layout.addWidget(self.text_area)
        btn_close = QPushButton("關閉視窗")
        btn_close.setFixedHeight(40)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)
        self.setLayout(layout)

class UpdateWorker(QObject):
    finished = Signal()
    progress = Signal(str)

class InteractiveTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setFocusPolicy(Qt.NoFocus) 
        self.setStyleSheet("""
            QTableWidget { background-color: #ffffff; alternate-background-color: #f9f9f9; border: none; font-size: 14px; outline: 0; }
            QTableWidget::item { padding: 5px; border: none; outline: none; }
            QTableWidget::item:selected { background-color: #0078D7; color: white; }
            QHeaderView::section { background-color: #f1f1f1; border: none; border-bottom: 2px solid #ddd; height: 35px; font-weight: bold; color: #555; }
        """)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.clearSelection()
        else: super().keyPressEvent(event)
    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid() and self.selectionModel().isSelected(index):
            self.clearSelection()
            return 
        super().mousePressEvent(event)

class UniversalLotteryTab(QWidget):
    def __init__(self, lottery_key, config):
        super().__init__()
        self.lottery_key = lottery_key
        self.config = config
        self.dm = DataManager(lottery_key)
        self.help_window = HelpWindow()
        self.init_ui()
        if self.dm.data:
            self.refresh_table_from_dm()
            last_period = self.dm.data[0]['period']
            self.status_label.setText(f"🟢 資料就緒 (最新: {last_period})")

    def init_ui(self):
        self.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 6px; margin-top: 6px; padding-top: 10px; background-color: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #333; }
            QLabel { font-size: 14px; }
            QSpinBox { border: 1px solid #ccc; border-radius: 4px; background-color: #ffffff; color: #333; padding: 5px; font-weight: bold; font-size: 16px; selection-background-color: transparent; selection-color: #333; }
            QSpinBox:hover { border: 1px solid #0078D7; }
            /* ComboBox 美化 */
            QComboBox { border: 1px solid #ccc; border-radius: 4px; padding: 5px; font-size: 14px; background: white; }
            QComboBox::drop-down { border: none; }
        """)

        layout = QVBoxLayout()
        
        # Top Bar
        top_bar = QHBoxLayout()
        self.status_label = QLabel(f"🔴 資料狀態: 尚未載入")
        self.status_label.setStyleSheet("color: #333; font-weight: bold; font-size: 14px;")
        
        btn_layout = QHBoxLayout()
        self.btn_help = QPushButton("📖 使用說明")
        self.btn_help.setFixedSize(110, 36)
        self.btn_help.clicked.connect(self.toggle_help_window)
        self.btn_load = QPushButton("📂 匯入舊資料")
        self.btn_load.setFixedSize(120, 36)
        self.btn_load.clicked.connect(self.load_file)
        self.btn_update = QPushButton(f"🔄 更新連線")
        self.btn_update.setFixedSize(120, 36)
        self.btn_update.setStyleSheet(f"QPushButton {{ background-color: {self.config.get('theme_color', '#ddd')}; color: black; font-weight: bold; border-radius: 4px; border: 1px solid #999; }} QPushButton:hover {{ filter: brightness(110%); }}")
        self.btn_update.clicked.connect(self.start_update_thread)

        btn_layout.addWidget(self.btn_help)
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_update)
        top_bar.addWidget(self.status_label)
        top_bar.addStretch()
        top_bar.addLayout(btn_layout)
        layout.addLayout(top_bar)

        # Content
        content_layout = QHBoxLayout()
        
        # Left Stats
        stats_group = QGroupBox("📊 號碼冷熱排行")
        stats_inner = QHBoxLayout()
        stats_inner.setSpacing(0)
        
        self.table_primary = InteractiveTable()
        self.setup_table(self.table_primary, ["排名", "獎號", "次數"])
        stats_inner.addWidget(self.table_primary, 6)

        if self.config['has_special']:
            line = QFrame()
            line.setFrameShape(QFrame.VLine)
            line.setFrameShadow(QFrame.Sunken)
            line.setStyleSheet("border: none; background-color: #ddd; width: 2px;")
            stats_inner.addWidget(line)
            
            self.table_special = InteractiveTable()
            self.setup_table(self.table_special, ["排名", f"{self.config['special_label']}", "次數"])
            stats_inner.addWidget(self.table_special, 4)
            
        stats_group.setLayout(stats_inner)

        # Right Generator
        gen_group = QGroupBox("🎲 智慧選號模擬")
        gen_group.setMinimumWidth(380)
        gen_layout = QVBoxLayout()
        gen_layout.setSpacing(20)
        
        # --- 區塊 A: Top N ---
        frame_top = QFrame()
        frame_top.setStyleSheet("background-color: #f8f9fa; border-radius: 6px;")
        layout_top = QVBoxLayout(frame_top)
        
        lbl_top_title = QLabel("🅰️ 模式一：熱門前 N 名篩選")
        lbl_top_title.setStyleSheet("font-weight: bold; color: #555; font-size: 15px;")
        layout_top.addWidget(lbl_top_title)

        param_layout_top = QVBoxLayout()
        
        # [NEW] 賓果專用：星數選擇器
        if self.config.get('play_mode') == 'star_selection':
            row_star = QHBoxLayout()
            row_star.addWidget(QLabel("⭐ 選擇玩法:"))
            self.combo_star = QComboBox()
            for i in range(1, 11):
                self.combo_star.addItem(f"{i} 星 (選 {i} 號)", i)
            self.combo_star.setCurrentIndex(4) # 預設5星
            row_star.addWidget(self.combo_star)
            param_layout_top.addLayout(row_star)
        
        row_n = QHBoxLayout()
        row_n.addWidget(QLabel("1. 獎號 Top N:"))
        row_n.addStretch()
        self.spin_top_n = QSpinBox()
        self.spin_top_n.setRange(1, self.config['primary_range'][1]) # 範圍放寬
        self.spin_top_n.setValue(20) # 賓果預設看前20名
        self.spin_top_n.setFixedWidth(70)
        row_n.addWidget(self.spin_top_n)
        param_layout_top.addLayout(row_n)

        # 賓果也有超級獎號，所以保留這個
        if self.config['has_special']:
            row_m = QHBoxLayout()
            row_m.addWidget(QLabel(f"2. {self.config['special_label']} Top M:"))
            row_m.addStretch()
            self.spin_top_m = QSpinBox()
            self.spin_top_m.setRange(1, self.config['special_range'][1])
            self.spin_top_m.setValue(3)
            self.spin_top_m.setFixedWidth(70)
            row_m.addWidget(self.spin_top_m)
            param_layout_top.addLayout(row_m)

        layout_top.addLayout(param_layout_top)
        
        self.btn_gen_top = QPushButton("✨ 立即模擬選號 (Top N)")
        self.btn_gen_top.setFixedHeight(40)
        self.btn_gen_top.setStyleSheet("QPushButton { background-color: #0078D7; color: white; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #0063b1; }")
        self.btn_gen_top.clicked.connect(self.generate_top_n)
        layout_top.addWidget(self.btn_gen_top)
        
        self.res_lbl_top = QLabel("等待運算...")
        self.res_lbl_top.setAlignment(Qt.AlignCenter)
        self.res_lbl_top.setStyleSheet("border: 2px dashed #ccc; border-radius: 4px; padding: 10px; color: #aaa; background: white;")
        layout_top.addWidget(self.res_lbl_top)
        
        gen_layout.addWidget(frame_top)

        # 分隔線
        line_sep = QFrame()
        line_sep.setFrameShape(QFrame.HLine)
        line_sep.setFrameShadow(QFrame.Sunken)
        line_sep.setStyleSheet("border: none; background-color: #ddd; height: 2px;")
        gen_layout.addWidget(line_sep)

        # --- 區塊 B: Range ---
        frame_range = QFrame()
        frame_range.setStyleSheet("background-color: #fff0f0; border-radius: 6px;")
        layout_range = QVBoxLayout(frame_range)
        
        lbl_range_title = QLabel("🅱️ 模式二：排名範圍篩選")
        lbl_range_title.setStyleSheet("font-weight: bold; color: #D9534F; font-size: 15px;")
        layout_range.addWidget(lbl_range_title)
        
        param_layout_range = QVBoxLayout()
        
        def create_tilde():
            lbl = QLabel("～")
            lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #888; margin: 0 5px;")
            return lbl

        row_r1 = QHBoxLayout()
        row_r1.addWidget(QLabel("1. 獎號排名:"))
        row_r1.addStretch()
        self.spin_p_start = QSpinBox()
        self.spin_p_start.setRange(1, self.config['primary_range'][1])
        self.spin_p_start.setValue(5)
        self.spin_p_start.setFixedWidth(60)
        self.spin_p_end = QSpinBox()
        self.spin_p_end.setRange(1, self.config['primary_range'][1])
        self.spin_p_end.setValue(25) # 賓果範圍設大一點
        self.spin_p_end.setFixedWidth(60)
        
        row_r1.addWidget(self.spin_p_start)
        row_r1.addWidget(create_tilde())
        row_r1.addWidget(self.spin_p_end)
        param_layout_range.addLayout(row_r1)

        if self.config['has_special']:
            row_r2 = QHBoxLayout()
            row_r2.addWidget(QLabel(f"2. {self.config['special_label']}排名:"))
            row_r2.addStretch()
            self.spin_s_start = QSpinBox()
            self.spin_s_start.setRange(1, self.config['special_range'][1])
            self.spin_s_start.setValue(2)
            self.spin_s_start.setFixedWidth(60)
            self.spin_s_end = QSpinBox()
            self.spin_s_end.setRange(1, self.config['special_range'][1])
            self.spin_s_end.setValue(5)
            self.spin_s_end.setFixedWidth(60)
            row_r2.addWidget(self.spin_s_start)
            row_r2.addWidget(create_tilde())
            row_r2.addWidget(self.spin_s_end)
            param_layout_range.addLayout(row_r2)
            
        layout_range.addLayout(param_layout_range)
        
        self.btn_gen_range = QPushButton("✨ 依範圍模擬選號")
        self.btn_gen_range.setFixedHeight(40)
        self.btn_gen_range.setStyleSheet("QPushButton { background-color: #D9534F; color: white; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #c9302c; }")
        self.btn_gen_range.clicked.connect(self.generate_range_selection)
        layout_range.addWidget(self.btn_gen_range)
        
        self.res_lbl_range = QLabel("等待運算...")
        self.res_lbl_range.setAlignment(Qt.AlignCenter)
        self.res_lbl_range.setStyleSheet("border: 2px dashed #D9534F; border-radius: 4px; padding: 10px; color: #aaa; background: white;")
        layout_range.addWidget(self.res_lbl_range)

        gen_layout.addWidget(frame_range)
        gen_layout.addStretch() 
        gen_group.setLayout(gen_layout)
        
        content_layout.addWidget(stats_group, 6)
        content_layout.addWidget(gen_group, 4)
        layout.addLayout(content_layout)
        self.setLayout(layout)

    def setup_table(self, table, headers):
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)

    # ... (Update methods 同前版) ...
    def toggle_help_window(self):
        if self.help_window.isVisible(): self.help_window.close()
        else: self.help_window.show(); self.help_window.raise_()

    def start_update_thread(self):
        self.btn_update.setEnabled(False)
        self.status_label.setText("🟠 正在下載資料...")
        self.worker = UpdateWorker()
        self.worker.progress.connect(self.update_progress_label)
        self.worker.finished.connect(self.on_update_finished)
        t = threading.Thread(target=self._thread_task)
        t.start()

    def _thread_task(self):
        self.dm.fetch_all_history(progress_callback=self.worker.progress.emit)
        self.worker.finished.emit()

    def update_progress_label(self, msg):
        self.status_label.setText(f"🟠 {msg}")

    def on_update_finished(self):
        self.btn_update.setEnabled(True)
        self.refresh_table_from_dm()
        last_period = self.dm.data[0]['period'] if self.dm.data else "無"
        self.status_label.setText(f"🟢 更新完成 (最新: {last_period})")
        QMessageBox.information(self, "完成", f"{self.config['name']} 資料更新完畢！")

    def refresh_table_from_dm(self):
        stats = self.dm.get_sorted_stats()
        self.fill_table(self.table_primary, stats.get('primary', []))
        if self.config['has_special']:
            self.fill_table(self.table_special, stats.get('special', []), is_red=True)

    def fill_table(self, table, data_list, is_red=False):
        table.setRowCount(0)
        table.setRowCount(len(data_list))
        for i, (num, count) in enumerate(data_list):
            rank = i + 1
            def make_item(text, bold=False, color=None):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignCenter)
                if bold: f = QFont(); f.setBold(True); item.setFont(f)
                if color: item.setForeground(QColor(color))
                return item
            table.setItem(i, 0, make_item(rank))
            num_str = f"{num:02d}"
            table.setItem(i, 1, make_item(num_str, bold=True, color="#D9534F" if is_red else None))
            table.setItem(i, 2, make_item(count))

    def load_file(self):
        QMessageBox.information(self, "提示", "請使用 [更新連線] 功能。")

    # --- 選號邏輯修正：動態取得要選幾個號 ---
    def get_select_count(self):
        # 如果有星數選單，就用選單的值；否則用 config 的預設值
        if hasattr(self, 'combo_star') and self.combo_star.isVisible():
            return self.combo_star.currentData() # 回傳 1~10
        return self.config['select_count']

    def generate_top_n(self):
        if not self.dm.stats:
            self.res_lbl_top.setText("無資料")
            return
            
        top_n = self.spin_top_n.value()
        primary_stats = self.dm.get_sorted_stats().get('primary', [])
        pool_primary = [x[0] for x in primary_stats[:top_n]]
        
        count = self.get_select_count() # 動態取得
        
        if len(pool_primary) < count:
            self.res_lbl_top.setText(f"資料不足 (需 {count} 個)")
            return
            
        picked_primary = sorted(random.sample(pool_primary, count))
        nums_str = " ".join([f"{n:02d}" for n in picked_primary])
        
        sp_text = ""
        if self.config['has_special']:
            top_m = self.spin_top_m.value()
            special_stats = self.dm.get_sorted_stats().get('special', [])
            pool_special = [x[0] for x in special_stats[:top_m]]
            if pool_special:
                picked_special = random.choice(pool_special)
                sp_text = f" + <font color='red'>{picked_special:02d}</font>"
        
        html = f"<div style='font-size: 24px; font-weight: bold; color: #333;'>{nums_str} {sp_text}</div>"
        self.res_lbl_top.setText(html)
        self.res_lbl_top.setStyleSheet("border: 2px solid #0078D7; border-radius: 4px; padding: 10px; background: #eef6ff;")

    def generate_range_selection(self):
        if not self.dm.stats:
            self.res_lbl_range.setText("無資料")
            return

        p_start = self.spin_p_start.value()
        p_end = self.spin_p_end.value()
        
        if p_start > p_end:
            QMessageBox.warning(self, "設定錯誤", "排名範圍錯誤")
            return

        primary_stats = self.dm.get_sorted_stats().get('primary', [])
        pool_primary = [x[0] for x in primary_stats[p_start-1 : p_end]]
        
        count = self.get_select_count() # 動態取得
        
        if len(pool_primary) < count:
             QMessageBox.warning(self, "範圍太小", f"範圍內只有 {len(pool_primary)} 個號碼，不足以選出 {count} 個。")
             return

        picked_primary = sorted(random.sample(pool_primary, count))
        nums_str = " ".join([f"{n:02d}" for n in picked_primary])

        sp_text = ""
        if self.config['has_special']:
            s_start = self.spin_s_start.value()
            s_end = self.spin_s_end.value()
            if s_start > s_end: return
                
            special_stats = self.dm.get_sorted_stats().get('special', [])
            pool_special = [x[0] for x in special_stats[s_start-1 : s_end]]
            if not pool_special: return
            
            picked_special = random.choice(pool_special)
            sp_text = f" + <font color='red'>{picked_special:02d}</font>"

        html = f"<div style='font-size: 24px; font-weight: bold; color: #333;'>{nums_str} {sp_text}</div>"
        self.res_lbl_range.setText(html)
        self.res_lbl_range.setStyleSheet("border: 2px solid #D9534F; border-radius: 4px; padding: 10px; background: #fff0f0;")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("台彩全方位分析戰情室 (Vibe-Suite v9.0 Bingo)")
        self.resize(1300, 850)
        self.setStyleSheet("QMainWindow { background-color: #f2f2f2; }")
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ccc; background: white; }
            QTabBar::tab { padding: 10px 24px; font-size: 14px; background: #e0e0e0; margin-right: 2px; }
            QTabBar::tab:selected { background: white; border-bottom: 2px solid #0078D7; font-weight: bold; color: #0078D7; }
        """)
        self.setCentralWidget(self.tabs)
        from config import LOTTERY_CONFIG
        for key, conf in LOTTERY_CONFIG.items():
            self.tabs.addTab(UniversalLotteryTab(key, conf), conf['name'])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft JhengHei UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())