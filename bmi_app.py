#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BMI Body Mass Index Calculator
跨平台 BMI 身体质量指数计算器

依据《体重管理指导原则（2024年版）》及中国国家标准
严格遵循以下三个年龄段划分：
  1. 学龄前儿童 (0-6岁): WS/T 423-2022《7岁以下儿童生长标准》
  2. 学龄儿童青少年 (7-18岁): WS/T 586-2018《学龄儿童青少年超重与肥胖筛查》
  3. 成人 (18岁及以上): WS/T 428-2013《成人体重判定》
"""

__version__ = '0.0.1'

import sys
import os
import configparser
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox,
    QGroupBox, QDialog
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QPalette, QColor, QDoubleValidator, QCursor


# ============================================================
# 自定义输入框：光标始终在最左侧
# ============================================================
class LeftAlignLineEdit(QLineEdit):
    """重写 focusInEvent，确保每次点击输入框时光标都在最左侧"""

    def focusInEvent(self, event):
        QLineEdit.focusInEvent(self, event)
        self.setCursorPosition(0)


# ============================================================
# 多语言管理器 — 基于 .ini 文件
# ============================================================
class LanguageManager:
    """管理 .ini 格式的语言文件，支持运行时切换"""

    def __init__(self, translations_dir=None):
        # PyInstaller 单文件模式：sys._MEIPASS 是解压临时目录
        # 非 frozen 模式：使用源码目录
        if getattr(sys, 'frozen', False):
            self.app_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        else:
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.translations_dir = translations_dir or os.path.join(self.app_dir, 'translations')
        self.available_languages = ['en-US', 'zh-CN', 'ko-KR', 'ja-JP', 'de-DE', 'fr-FR']
        self.current_lang = 'zh-CN'
        self.strings = {}
        # 先加载 zh-CN 再设置，确保 strings 非空
        self._load_language_file('zh-CN')

    def set_language(self, lang_code):
        """设置当前语言并加载对应的 .ini 文件"""
        if lang_code not in self.available_languages:
            lang_code = 'zh-CN'
        self.current_lang = lang_code
        self._load_language_file(lang_code)

    def _load_language_file(self, lang_code):
        """从 .ini 文件加载所有翻译字符串"""
        filename = f"{lang_code}-bmi.ini"
        filepath = os.path.join(self.translations_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            import io
            config = configparser.RawConfigParser()
            config.optionxform = str
            config.read_file(io.StringIO(content))
            self.strings = {}
            for section in config.sections():
                for key, value in config.items(section):
                    full_key = f"{section}.{key}"
                    self.strings[full_key] = value
        except Exception as e:
            print(f"Error loading language file '{filepath}': {e}")
            if lang_code != 'zh-CN':
                self._load_language_file('zh-CN')

    def tr(self, key, default=""):
        """翻译键值，返回对应的字符串"""
        return self.strings.get(key, default)


# 全局语言管理器实例（延迟初始化）
lang_manager = None


def get_lang_manager():
    """获取全局语言管理器实例（延迟初始化，避免启动慢）"""
    global lang_manager
    if lang_manager is None:
        lang_manager = LanguageManager()
    return lang_manager


# ============================================================
# 样式常量
# ============================================================
PRIMARY_COLOR = '#4A90D9'
PRIMARY_HOVER = '#357ABD'
SUCCESS_COLOR = '#28A745'
WARNING_COLOR = '#FFC107'
DANGER_COLOR = '#DC3545'
BG_COLOR = '#F5F7FA'
CARD_BG = '#FFFFFF'
TEXT_PRIMARY = '#2C3E50'
TEXT_SECONDARY = '#7F8C8D'
BORDER_COLOR = '#E0E6ED'


def apply_theme(window):
    """应用主题"""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BG_COLOR))
    palette.setColor(QPalette.WindowText, QColor(TEXT_PRIMARY))
    window.setPalette(palette)
    window.setAutoFillBackground(True)


# ============================================================
# BMI 判断标准 — 严格遵循《体重管理指导原则（2024年版）》
# ============================================================
class BMICalculator:
    """
    依据《体重管理指导原则（2024年版）》的 BMI 计算器

    年龄段划分（3 档，严格按国家标准）:
    1. 学龄前儿童 (0-6岁): WS/T 423-2022《7岁以下儿童生长标准》
       使用成人标准近似（因 Z 评分法需年龄/性别精确值，此处简化）
    2. 学龄儿童青少年 (7-18岁): WS/T 586-2018《学龄儿童青少年超重与肥胖筛查》
       分年龄、性别百分位法 (P85=超重, P95=肥胖)
    3. 成人 (18岁及以上): WS/T 428-2013《成人体重判定》
       偏瘦<18.5, 正常18.5-23.9, 超重24-27.9, 肥胖≥28
    """

    # --- 7-18岁男童超重 (P85) 和肥胖 (P95) BMI 临界值 ---
    # 来源: WS/T 586-2018《学龄儿童青少年超重与肥胖筛查》
    CHILD_OVERWEIGHT_BOY = {
        6.0: (16.5, 18.7), 6.5: (16.3, 18.5),
        7.0: (16.1, 18.2), 7.5: (16.0, 18.1),
        8.0: (16.0, 18.1), 8.5: (16.1, 18.2),
        9.0: (16.2, 18.4), 9.5: (16.4, 18.6),
        10.0: (16.7, 19.0), 10.5: (17.1, 19.5),
        11.0: (17.5, 20.0), 11.5: (18.0, 20.6),
        12.0: (18.5, 21.2), 12.5: (19.0, 21.8),
        13.0: (19.4, 22.3), 13.5: (19.8, 22.7),
        14.0: (20.1, 23.0), 14.5: (20.3, 23.1),
        15.0: (20.4, 23.2), 15.5: (20.4, 23.1),
        16.0: (20.4, 23.1), 16.5: (20.3, 23.0),
        17.0: (20.3, 22.9), 17.5: (20.2, 22.8),
        18.0: (20.0, 22.7),
    }

    # --- 7-18岁女童超重 (P85) 和肥胖 (P95) BMI 临界值 ---
    CHILD_OVERWEIGHT_GIRL = {
        6.0: (16.4, 18.6), 6.5: (16.3, 18.5),
        7.0: (16.2, 18.4), 7.5: (16.1, 18.3),
        8.0: (16.1, 18.3), 8.5: (16.2, 18.4),
        9.0: (16.4, 18.6), 9.5: (16.7, 19.0),
        10.0: (17.0, 19.4), 10.5: (17.4, 19.9),
        11.0: (17.8, 20.3), 11.5: (18.3, 20.9),
        12.0: (18.7, 21.3), 12.5: (19.1, 21.7),
        13.0: (19.4, 22.0), 13.5: (19.6, 22.1),
        14.0: (19.7, 22.1), 14.5: (19.7, 22.1),
        15.0: (19.6, 22.0), 15.5: (19.5, 21.9),
        16.0: (19.4, 21.8), 16.5: (19.3, 21.7),
        17.0: (19.3, 21.7), 17.5: (19.2, 21.6),
        18.0: (19.1, 21.5),
    }

    # --- 成人 BMI 标准 (WS/T 428-2013) ---
    ADULT_UNDERWEIGHT = 18.5
    ADULT_NORMAL_MAX = 24.0
    ADULT_OVERWEIGHT_MAX = 28.0

    # --- 年龄段定义 (严格按《体重管理指导原则2024版》) ---
    # 注意：这里的 display_keys 对应翻译文件中的 key
    AGE_GROUPS = [
        ('preschool', 0, 6),     # 学龄前儿童 0-6岁
        ('school_age', 7, 18),   # 学龄儿童青少年 7-18岁
        ('adult', 18, 999),      # 成人 18岁及以上
    ]

    @staticmethod
    def classify_bmi(bmi, age, gender):
        """
        根据 BMI、年龄和性别判断体重状态

        返回: (分类标签, 分类文本, 颜色)
        """
        age = float(age)

        # 7-18 岁：使用 WS/T 586-2018 百分位法
        if 7 <= age <= 18:
            return BMICalculator._classify_child(bmi, age, gender)

        # 0-6 岁 和 18 岁以上：使用 WS/T 428-2013 成人标准
        return BMICalculator._classify_adult(bmi)

    @staticmethod
    def _classify_child(bmi, age, gender):
        """
        儿童青少年 BMI 判断 (WS/T 586-2018)
        P85 = 超重临界值，P95 = 肥胖临界值
        """
        if gender == 'male':
            cutoff_table = BMICalculator.CHILD_OVERWEIGHT_BOY
        else:
            cutoff_table = BMICalculator.CHILD_OVERWEIGHT_GIRL

        overweight_cutoff, obese_cutoff = BMICalculator._get_interpolated_cutoff(cutoff_table, age)

        if bmi < overweight_cutoff:
            mgr = get_lang_manager()
            cat_label = 'underweight' if bmi < 16 else 'normal'
            cat_text = mgr.tr(f'Category.{cat_label.capitalize()}', cat_label)
            return (cat_label, cat_text, SUCCESS_COLOR)
        elif bmi < obese_cutoff:
            mgr = get_lang_manager()
            return ('overweight', mgr.tr('Category.Overweight', 'Overweight'), WARNING_COLOR)
        else:
            mgr = get_lang_manager()
            return ('obese', mgr.tr('Category.Obese', 'Obese'), DANGER_COLOR)

    @staticmethod
    def _get_interpolated_cutoff(table, age):
        """根据年龄表，线性插值得到临界值"""
        ages = sorted(table.keys())

        if age <= ages[0]:
            return table[ages[0]]
        if age >= ages[-1]:
            return table[ages[-1]]

        for i in range(len(ages) - 1):
            if ages[i] <= age <= ages[i + 1]:
                if ages[i] == ages[i + 1]:
                    return table[ages[i]]
                ratio = (age - ages[i]) / (ages[i + 1] - ages[i])
                low_over = table[ages[i]][0]
                high_over = table[ages[i + 1]][0]
                low_obese = table[ages[i]][1]
                high_obese = table[ages[i + 1]][1]
                overweight = low_over + ratio * (high_over - low_over)
                obese = low_obese + ratio * (high_obese - low_obese)
                return (overweight, obese)

        return table[ages[-1]]

    @staticmethod
    def _classify_adult(bmi):
        """成人 BMI 判断 (WS/T 428-2013)"""
        mgr = get_lang_manager()
        if bmi < BMICalculator.ADULT_UNDERWEIGHT:
            return ('underweight', mgr.tr('Category.Underweight', 'Underweight'), '#3498DB')
        elif bmi < BMICalculator.ADULT_NORMAL_MAX:
            return ('normal', mgr.tr('Category.Normal', 'Normal'), SUCCESS_COLOR)
        elif bmi < BMICalculator.ADULT_OVERWEIGHT_MAX:
            return ('overweight', mgr.tr('Category.Overweight', 'Overweight'), WARNING_COLOR)
        else:
            return ('obese', mgr.tr('Category.Obese', 'Obese'), DANGER_COLOR)

    @staticmethod
    def get_age_group_info(age_code):
        """返回年龄段信息 (名称, 标准代码)"""
        mgr = get_lang_manager()
        info = {
            'preschool': (mgr.tr('AgeGroup.Preschool', '学龄前儿童'), 'WS/T 423-2022'),
            'school_age': (mgr.tr('AgeGroup.SchoolAge', '学龄儿童青少年'), 'WS/T 586-2018'),
            'adult': (mgr.tr('AgeGroup.Adult', '成人'), 'WS/T 428-2013'),
        }
        return info.get(age_code, ('', ''))

    @staticmethod
    def get_age_group_range(age_code):
        """返回年龄段的 (最低年龄, 最高年龄)"""
        for code, low, high in BMICalculator.AGE_GROUPS:
            if code == age_code:
                return (low, high)
        return (0, 0)

    @staticmethod
    def get_age_range_text(age_code):
        """返回年龄段的范围显示文本，从翻译文件获取"""
        mgr = get_lang_manager()
        range_key = {
            'preschool': 'AgeRange.Preschool',
            'school_age': 'AgeRange.SchoolAge',
            'adult': 'AgeRange.Adult',
        }.get(age_code, '')
        return mgr.tr(range_key, '')

    @staticmethod
    def get_center_age(age_code):
        """返回年龄段的中心年龄（用于儿童百分位插值）"""
        low, high = BMICalculator.get_age_group_range(age_code)
        if low == 0 and high == 6:
            return 3
        elif low == 7 and high == 18:
            return 12.5
        else:
            return 30

    @staticmethod
    def get_standard_text():
        """返回标准说明文本"""
        mgr = get_lang_manager()
        return mgr.tr('Result.StandardDesc', '依据《体重管理指导原则（2024年版）》及中国卫生行业标准')

    @staticmethod
    def get_age_options_display():
        """返回当前语言的年龄段显示文本列表"""
        mgr = get_lang_manager()
        # 从翻译文件获取年龄段名称，年龄范围也从翻译文件获取
        options = [
            mgr.tr('AgeGroup.Preschool', '学龄前儿童') + ' (' + mgr.tr('AgeRange.Preschool', '0-6岁') + ')',
            mgr.tr('AgeGroup.SchoolAge', '学龄儿童青少年') + ' (' + mgr.tr('AgeRange.SchoolAge', '7-18岁') + ')',
            mgr.tr('AgeGroup.Adult', '成人') + ' (' + mgr.tr('AgeRange.Adult', '18岁以上') + ')',
        ]
        return options


# ============================================================
# 关于对话框
# ============================================================
class AboutDialog(QDialog):
    """关于本软件对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedSize(360, 300)
        self._setup_ui()
        self._update_text()

    def _setup_ui(self):
        """构建关于对话框 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 30, 30, 30)

        self._title = QLabel()
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4A90D9;")
        layout.addWidget(self._title)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet(f"color: {BORDER_COLOR};")
        layout.addWidget(separator)

        # 信息行
        self._info_rows = []
        info_labels = ['SoftwareName', 'Version', 'Author', 'Contact']
        for label_key in info_labels:
            row_layout = QHBoxLayout()
            lbl = QLabel()
            lbl.setStyleSheet(f"font-size: 14px; color: {TEXT_PRIMARY}; font-weight: bold;")
            val = QLabel()
            val.setStyleSheet(f"font-size: 14px; color: {TEXT_PRIMARY};")
            row_layout.addWidget(lbl)
            row_layout.addWidget(val)
            row_layout.addStretch()
            layout.addLayout(row_layout)
            self._info_rows.append((lbl, val, label_key))

        layout.addStretch()

        self._close_btn = QPushButton()
        self._close_btn.setFixedHeight(40)
        self._close_btn.setFixedWidth(100)
        self._close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
        """)
        self._close_btn.clicked.connect(self.close)
        layout.addWidget(self._close_btn, alignment=Qt.AlignCenter)

    def _update_text(self):
        """更新所有文本"""
        mgr = get_lang_manager()
        self.setWindowTitle(mgr.tr('About.Title', '关于'))
        self._title.setText(mgr.tr('About.Title', '关于本软件'))

        info_values = {
            'SoftwareName': '身体质量指数（BMI）计算器',
            'Version': __version__,
            'Author': 'baijianpeng',
            'Contact': 'baijianpeng@qq.com',
        }

        for lbl, val, key in self._info_rows:
            lbl.setText(mgr.tr(f'About.{key}Label', f'{key}:'))
            val.setText(mgr.tr(f'About.{key}Value', info_values[key]))

        self._close_btn.setText(mgr.tr('Button.Close', '关闭'))


# ============================================================
# 选项对话框
# ============================================================
class OptionsDialog(QDialog):
    """选项对话框，用于设置界面语言"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedSize(400, 220)
        self._setup_ui()

    def _setup_ui(self):
        """构建选项对话框 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        self._children = []

        mgr = get_lang_manager()
        title = QLabel(mgr.tr('Message.OptionTitle', '选项'))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4A90D9;")
        layout.addWidget(title)
        self._children.append(title)

        lang_desc = QLabel(mgr.tr('Message.LanguageDesc', '选择界面显示语言，修改后立即生效。'))
        lang_desc.setStyleSheet("font-size: 13px; color: #7F8C8D;")
        lang_desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(lang_desc)
        self._children.append(lang_desc)

        # 语言下拉框 - 增大字号
        self.lang_combo = QComboBox()
        self.lang_combo.setFixedHeight(44)
        self.lang_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 0 10px;
                font-size: 16px;
                color: {TEXT_PRIMARY};
                background-color: {CARD_BG};
            }}
            QComboBox::drop-down {{ border: none; }}
        """)

        mgr = get_lang_manager()
        lang_display_names = {
            'zh-CN': '简体中文',
            'en-US': 'English',
            'ko-KR': '한국어',
            'ja-JP': '日本語',
            'de-DE': 'Deutsch',
            'fr-FR': 'Français',
        }
        for lang_code in mgr.available_languages:
            display_name = lang_display_names.get(lang_code, lang_code)
            self.lang_combo.addItem(display_name, lang_code)

        idx = self.lang_combo.findData(mgr.current_lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)

        layout.addWidget(self.lang_combo)

        btn_layout = QHBoxLayout()
        btn_layout.setStretch(0, 1)

        apply_btn = QPushButton()
        apply_btn.setFixedHeight(44)
        apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
        """)
        apply_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(apply_btn)

        self._btn_apply = apply_btn
        self._btn_close = QPushButton()
        self._btn_close.setFixedHeight(44)
        self._btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {CARD_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {BG_COLOR};
            }}
        """)
        self._btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self._btn_close)

        layout.addLayout(btn_layout)

    def update_ui_language(self):
        """更新选项对话框中所有文本"""
        mgr = get_lang_manager()
        self.setWindowTitle(mgr.tr('Message.OptionTitle', '选项'))
        self._children[0].setText(mgr.tr('Message.OptionTitle', '选项'))
        self._children[1].setText(mgr.tr('Message.LanguageDesc', '选择界面显示语言，修改后立即生效。'))
        self._btn_apply.setText(mgr.tr('Button.Apply', '应用'))
        self._btn_close.setText(mgr.tr('Button.Close', '关闭'))

    def _on_apply(self):
        """应用语言"""
        mgr = get_lang_manager()
        lang_code = self.lang_combo.currentData()
        if lang_code:
            mgr.set_language(lang_code)
            if self.parent_window:
                self.parent_window.update_language()
        self.close()


# ============================================================
# 主窗口
# ============================================================
class BMIWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        mgr = get_lang_manager()
        self.setWindowTitle('身体质量指数（BMI）计算器')
        self.setMinimumSize(480, 580)
        self.center_on_screen()
        apply_theme(self)
        self.setup_ui()
        self.update_language()
        # 关于链接鼠标样式
        self.about_link.setCursor(Qt.PointingHandCursor)

    def center_on_screen(self):
        """窗口居中显示"""
        frame_geometry = self.frameGeometry()
        screen_center = QApplication.primaryScreen().geometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())

    def setup_ui(self):
        """构建界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # --- 标题 ---
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignCenter)
        self.update_title()
        main_layout.addWidget(self.title_label)

        # --- 标准说明 ---
        self.standard_desc_label = QLabel()
        self.standard_desc_label.setAlignment(Qt.AlignCenter)
        self.standard_desc_label.setStyleSheet(f"color: #95A5A6; font-size: 12px; padding: 2px;")
        self.standard_desc_label.setOpenExternalLinks(True)
        self.standard_desc_label.setTextFormat(Qt.RichText)
        self.update_standard_desc()
        main_layout.addWidget(self.standard_desc_label)

        # --- 输入组 ---
        self.input_group = QGroupBox()
        self.input_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 15px;
                font-weight: bold;
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
            }}
        """)
        self.input_layout = QVBoxLayout(self.input_group)
        self.input_layout.setSpacing(10)
        self.input_layout.setContentsMargins(16, 20, 16, 16)

        # --- 年龄段 (3 档) ---
        age_row = QHBoxLayout()
        self.lbl_age = QLabel()
        self.lbl_age.setText(get_lang_manager().tr('Input.AgeLabel', '年龄段:'))
        self.age_combo = QComboBox()
        self.age_combo.setFixedHeight(40)
        self.age_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 0 10px;
                font-size: 16px;
                color: {TEXT_PRIMARY};
                background-color: {CARD_BG};
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        # 年龄段 key 列表，显示文本从翻译文件动态获取
        self.age_keys = ['preschool', 'school_age', 'adult']
        # 初始化年龄组合并的 items（默认中文）
        mgr_init = get_lang_manager()
        age_init_display = BMICalculator.get_age_options_display()
        for i, display in enumerate(age_init_display):
            self.age_combo.addItem(display, self.age_keys[i])
        age_row.addWidget(self.lbl_age)
        age_row.addWidget(self.age_combo)
        age_row.addStretch()
        self.input_layout.addLayout(age_row)

        # --- 性别 ---
        gender_row = QHBoxLayout()
        self.lbl_gender = QLabel()
        self.lbl_gender.setText(get_lang_manager().tr('Input.GenderLabel', '性别:'))
        self.gender_combo = QComboBox()
        self.gender_combo.setFixedHeight(40)
        self.gender_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 0 10px;
                font-size: 16px;
                color: {TEXT_PRIMARY};
                background-color: {CARD_BG};
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        self.gender_combo.addItem(get_lang_manager().tr('Status.Male', '男'), 'male')
        self.gender_combo.addItem(get_lang_manager().tr('Status.Female', '女'), 'female')
        self.gender_combo.setFixedWidth(140)
        gender_row.addWidget(self.lbl_gender)
        gender_row.addWidget(self.gender_combo)
        gender_row.addStretch()
        self.input_layout.addLayout(gender_row)

        # --- 身高 ---
        height_row = QHBoxLayout()
        self.lbl_height = QLabel()
        self.lbl_height.setText(get_lang_manager().tr('Input.HeightLabel', '身高 (厘米):'))
        self.height_input = LeftAlignLineEdit()
        self.height_input.setPlaceholderText(
            get_lang_manager().tr('Input.HeightPlaceholder', '请输入身高 (cm)')
        )
        self.height_input.setFixedHeight(40)
        self.height_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 16px;
                color: {TEXT_PRIMARY};
                background-color: {CARD_BG};
            }}
            QLineEdit:focus {{
                border: 2px solid {PRIMARY_COLOR};
            }}
        """)
        # 不用 input_mask（999 会产生占位符导致光标错位），改用正则验证
        self.height_input.setMaxLength(3)
        self.height_input.setAlignment(Qt.AlignLeft)
        self.height_input.returnPressed.connect(self.calculate_bmi)
        height_row.addWidget(self.lbl_height)
        height_row.addWidget(self.height_input)
        self.input_layout.addLayout(height_row)

        # --- 体重 ---
        weight_row = QHBoxLayout()
        self.lbl_weight = QLabel()
        self.lbl_weight.setText(get_lang_manager().tr('Input.WeightLabel', '体重 (公斤):'))
        self.weight_input = LeftAlignLineEdit()
        self.weight_input.setValidator(QDoubleValidator(0.1, 1000, 2))
        self.weight_input.setAlignment(Qt.AlignLeft)
        self.weight_input.setPlaceholderText(
            get_lang_manager().tr('Input.WeightPlaceholder', '请输入体重 (kg)')
        )
        self.weight_input.setFixedHeight(40)
        self.weight_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 16px;
                color: {TEXT_PRIMARY};
                background-color: {CARD_BG};
            }}
            QLineEdit:focus {{
                border: 2px solid {PRIMARY_COLOR};
            }}
        """)
        weight_row.addWidget(self.lbl_weight)
        weight_row.addWidget(self.weight_input)
        self.weight_input.returnPressed.connect(self.calculate_bmi)
        self.input_layout.addLayout(weight_row)

        main_layout.addWidget(self.input_group)

        # --- 按钮行 ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.calc_btn = QPushButton()
        self.calc_btn.setFixedHeight(44)
        self.calc_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
        """)
        self.calc_btn.clicked.connect(self.calculate_bmi)
        btn_layout.addWidget(self.calc_btn)

        self.reset_btn = QPushButton()
        self.reset_btn.setFixedHeight(44)
        self.reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CARD_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                font-size: 16px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {BG_COLOR};
                border-color: {PRIMARY_COLOR};
            }}
        """)
        self.reset_btn.clicked.connect(self.reset_form)
        btn_layout.addWidget(self.reset_btn)

        self.option_btn = QPushButton()
        self.option_btn.setFixedHeight(44)
        self.option_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CARD_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                font-size: 16px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {BG_COLOR};
                border-color: {PRIMARY_COLOR};
            }}
        """)
        self.option_btn.clicked.connect(self.open_options)
        btn_layout.addWidget(self.option_btn)

        main_layout.addLayout(btn_layout)

        # --- 结果区 ---
        self.result_group = QGroupBox()
        self.result_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 14px;
                color: {TEXT_PRIMARY};
                border: 2px solid {PRIMARY_COLOR};
                border-radius: 10px;
                background-color: {CARD_BG};
            }}
        """)
        self.result_layout = QVBoxLayout(self.result_group)
        self.result_layout.setSpacing(10)
        self.result_layout.setAlignment(Qt.AlignCenter)
        self.result_layout.setContentsMargins(15, 15, 15, 15)

        self.bmi_value_label = QLabel()
        self.bmi_value_label.setAlignment(Qt.AlignCenter)
        self.bmi_value_label.setStyleSheet(f"font-size: 36px; font-weight: bold;")
        self.result_layout.addWidget(self.bmi_value_label)

        self.category_label = QLabel()
        self.category_label.setAlignment(Qt.AlignCenter)
        self.category_label.setStyleSheet(f"font-size: 22px; font-weight: bold;")
        self.result_layout.addWidget(self.category_label)

        self.standard_label = QLabel()
        self.standard_label.setAlignment(Qt.AlignCenter)
        self.standard_label.setStyleSheet("font-size: 12px; color: #95A5A6;")
        self.result_layout.addWidget(self.standard_label)

        main_layout.addWidget(self.result_group)

        # --- 底部固定区域 ---
        footer_container = QWidget()
        footer_layout = QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(15, 8, 15, 8)

        self.footer_label = QLabel()
        self.footer_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.footer_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        self.update_footer()
        footer_layout.addWidget(self.footer_label)

        footer_layout.addStretch()

        # 关于链接
        self.about_link = QLabel()
        self.about_link.setText(' | 关于')
        self.about_link.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.about_link.setStyleSheet('color: #7F8C8D;')
        self.about_link.mousePressEvent = lambda e: self.show_about()  # noqa: E731
        footer_layout.addWidget(self.about_link)

        main_layout.addWidget(footer_container)
        main_layout.addStretch(1)

    # ---------- 语言更新 ----------
    def update_title(self):
        mgr = get_lang_manager()
        title_text = mgr.tr('App.Title', '身体质量指数（BMI）计算器')
        self.title_label.setText(f"<h2 style='color: {PRIMARY_COLOR}; margin: 0;'>{title_text}</h2>")

    def update_standard_desc(self):
        mgr = get_lang_manager()
        # 中文版使用超链接，英文版使用纯文本
        standard_text = BMICalculator.get_standard_text()
        if mgr.current_lang == 'zh-CN':
            standard_text = standard_text.replace(
                '《体重管理指导原则（2024年版）》',
                f'<a href="https://www.nhc.gov.cn/ylyjs/zcwj/202412/75cb79c171c94def9e768193e65484f7/files/1736390749000_59785.pdf" style="color: {PRIMARY_COLOR}; text-decoration: none;">《体重管理指导原则（2024年版）》</a>'
            )
        self.standard_desc_label.setText(standard_text)
        self.standard_desc_label.setOpenExternalLinks(True)
        self.standard_desc_label.setTextFormat(Qt.RichText)

    def update_footer(self):
        mgr = get_lang_manager()
        self.footer_label.setText(
            f"© {datetime.now().year} 身体质量指数（BMI）计算器 | v{__version__}"
        )

    def update_language(self):
        """根据当前语言更新所有文本"""
        mgr = get_lang_manager()

        # 窗口标题
        self.setWindowTitle(mgr.tr('App.Title', 'BMI Calculator'))
        self.input_group.setTitle(mgr.tr('Input.GroupTitle', '输入信息'))
        self.update_title()
        self.update_standard_desc()
        self.update_footer()

        # 标签文本
        self.lbl_age.setText(mgr.tr('Input.AgeLabel', '年龄段:'))
        self.lbl_gender.setText(mgr.tr('Input.GenderLabel', '性别:'))
        self.lbl_height.setText(mgr.tr('Input.HeightLabel', '身高 (厘米):'))
        self.lbl_weight.setText(mgr.tr('Input.WeightLabel', '体重 (公斤):'))

        # 按钮文本
        self.calc_btn.setText(mgr.tr('Button.Calculate', '计算 BMI'))
        self.reset_btn.setText(mgr.tr('Button.Reset', '清空'))
        self.option_btn.setText(mgr.tr('Button.Options', '选项'))

        # 语言更新后刷新关于链接样式
        self.about_link.setText(' | 关于')
        self.about_link.setStyleSheet('color: #7F8C8D;')

        # 占位符
        self.height_input.setPlaceholderText(mgr.tr('Input.HeightPlaceholder', '请输入身高 (cm)'))
        self.weight_input.setPlaceholderText(mgr.tr('Input.WeightPlaceholder', '请输入体重 (kg)'))

        # 性别下拉框
        self.gender_combo.setItemText(0, mgr.tr('Status.Male', '男'))
        self.gender_combo.setItemText(1, mgr.tr('Status.Female', '女'))

        # 年龄段下拉框 - 从翻译文件动态获取
        age_display = BMICalculator.get_age_options_display()
        for i, display in enumerate(age_display):
            self.age_combo.setItemText(i, display)

        # 如果结果区已显示，刷新结果区文本
        if self.result_group.isVisible():
            self._refresh_result_text()

    def _refresh_result_text(self):
        """刷新结果区的翻译（语言切换时调用）"""
        mgr = get_lang_manager()
        # 重新获取翻译后的分类文本
        if hasattr(self, '_last_label'):
            label_map = {
                'underweight': 'Category.Underweight',
                'normal': 'Category.Normal',
                'overweight': 'Category.Overweight',
                'obese': 'Category.Obese',
            }
            translated_category = mgr.tr(label_map.get(self._last_label, 'Category.Normal'), self._last_category)
            self.category_label.setText(translated_category)
            self.category_label.setStyleSheet(
                f"font-size: 22px; font-weight: bold; color: {self._last_color};"
            )
        # 刷新标准代码
        if hasattr(self, '_last_standard_code'):
            self.standard_label.setText(self._last_standard_code)

    def _store_result(self, category, color, age_group_name, age_range_text, standard_code):
        """缓存结果信息用于语言切换时刷新"""
        self._last_category = category
        self._last_color = color

    # ---------- 打开选项 ----------
    def open_options(self):
        """打开选项对话框"""
        self._options_dialog = OptionsDialog(self)
        self._options_dialog.show()
        self._options_dialog.update_ui_language()

    # ---------- 计算 BMI ----------
    def _do_calculate_bmi(self):
        age_code = self.age_combo.currentData()
        gender = self.gender_combo.currentData()
        height_str = self.height_input.text().strip()
        weight_str = self.weight_input.text().strip()

        if not height_str or not weight_str:
            self._show_error(get_lang_manager().tr('Message.InputRequired', '请填写所有字段。'))
            return

        if not age_code:
            self._show_error(get_lang_manager().tr('Message.InputRequired', '请选择年龄段。'))
            return

        try:
            height_cm = float(height_str)
            weight_kg = float(weight_str)
        except ValueError:
            self._show_error(get_lang_manager().tr('Message.InvalidInput', '请输入有效数字。'))
            return

        if not (1 <= height_cm <= 300):
            self._show_error(get_lang_manager().tr('Message.HeightError', '请输入有效的身高 (1-300 cm)。'))
            return

        if not (0.1 <= weight_kg <= 1000):
            self._show_error(get_lang_manager().tr('Message.WeightError', '请输入有效的体重 (0.1-1000 kg)。'))
            return

        # 获取中心年龄用于儿童 BMI 插值
        center_age = BMICalculator.get_center_age(age_code)

        height_m = height_cm / 100.0
        bmi = weight_kg / (height_m ** 2)
        bmi_rounded = round(bmi, 1)

        # 根据年龄段和性别进行判断
        label, category, color = BMICalculator.classify_bmi(bmi, center_age, gender)

        # 获取年龄段信息和标准代码
        mgr = get_lang_manager()
        age_group_name, standard_code = BMICalculator.get_age_group_info(age_code)

        self.result_group.setVisible(True)
        self.bmi_value_label.setText(f"{bmi_rounded}")
        self.bmi_value_label.setStyleSheet(f"font-size: 36px; font-weight: bold; color: {color};")
        self.category_label.setText(category)
        self.category_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")

        # 缓存结果用于语言切换刷新
        self._store_result(category, color, '', '', '')
        self._last_label = label
        self._last_bmi = bmi_rounded
        self._last_age_code = age_code
        self._last_standard_code = standard_code

    def calculate_bmi(self):
        """入口：包裹 try-except 防止崩溃"""
        try:
            self._do_calculate_bmi()
        except Exception as e:
            import traceback
            mgr = get_lang_manager()
            error_msg = f"计算过程中发生错误:\n\n{str(e)}\n\n{traceback.format_exc()}"
            self._show_error(error_msg)

    def _show_error(self, message):
        """显示错误对话框"""
        msg = QMessageBox()
        msg.setWindowTitle(get_lang_manager().tr('Message.Error', '错误'))
        msg.setText(message)
        ok_btn = msg.addButton(get_lang_manager().tr('Button.Ok', '确定'), QMessageBox.AcceptRole)
        msg.setDefaultButton(ok_btn)
        ok_btn.setText(get_lang_manager().tr('Button.Ok', '确定'))
        msg.exec_()

    # ---------- 重置 ----------
    def reset_form(self):
        msg = QMessageBox()
        msg.setWindowTitle(get_lang_manager().tr('Button.Reset', '清空'))
        msg.setText(get_lang_manager().tr('Message.ResetConfirm', '确定要清空所有输入吗？'))
        yes_btn = msg.addButton(get_lang_manager().tr('Button.Yes', '是'), QMessageBox.AcceptRole)
        no_btn = msg.addButton(get_lang_manager().tr('Button.No', '否'), QMessageBox.RejectRole)
        msg.setDefaultButton(no_btn)
        yes_btn.setText(get_lang_manager().tr('Button.Yes', '是'))
        no_btn.setText(get_lang_manager().tr('Button.No', '否'))
        result = msg.exec_()
        if result == QMessageBox.AcceptRole:
            self.age_combo.setCurrentIndex(0)
            self.gender_combo.setCurrentIndex(0)
            self.height_input.clear()
            self.weight_input.clear()
            self.result_group.setVisible(False)
            self.height_input.setFocus()

    def show_about(self):
        """显示关于对话框"""
        from PyQt5.QtGui import QFont
        msg = QMessageBox(self)
        msg.setWindowTitle('关于')
        msg.setText('关于本软件')
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        msg.setFont(font)
        msg.setInformativeText(
            f'软件名称：身体质量指数（BMI）计算器\n'
            f'版本号：{__version__}\n'
            f'作者：baijianpeng\n'
            f'联系方式：baijianpeng@qq.com'
        )
        msg.setIcon(QMessageBox.Information)
        msg.exec_()


# ============================================================
# 入口
# ============================================================
def main():
    # 禁止弹出 DOS 控制台窗口（必须在 QApplication 之前）
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = BMIWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
