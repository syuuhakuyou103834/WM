from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QGridLayout, QFileDialog, QCheckBox, QMessageBox, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView, QApplication, QDialog, QVBoxLayout, QHBoxLayout, QDateTimeEdit, QDialogButtonBox, QSpinBox, QMenu
)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QSettings
from PyQt5.QtGui import QKeySequence
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import shutil
import csv
import os
from datetime import datetime
from core.wedgeTestResult_analyzer import WedgeTestAnalyzer
from utils.file_io import get_latest_files, get_resource_path

class MaintenanceTimeDialog(QDialog):
    """离子化室保养时间设定对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设定离子化室保养完成时间")
        self.setModal(True)
        self.setFixedSize(350, 250)

        layout = QVBoxLayout()

        # 标签
        label = QLabel("请选择最近一次离子化室保养完成时间：")
        layout.addWidget(label)

        # 日期时间选择区域
        datetime_layout = QHBoxLayout()

        # 年选择
        year_layout = QVBoxLayout()
        year_layout.addWidget(QLabel("年:"))
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(QDateTime.currentDateTime().date().year())
        self.year_spin.setFixedWidth(80)
        year_layout.addWidget(self.year_spin)
        datetime_layout.addLayout(year_layout)

        # 月选择
        month_layout = QVBoxLayout()
        month_layout.addWidget(QLabel("月:"))
        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(QDateTime.currentDateTime().date().month())
        self.month_spin.setFixedWidth(60)
        month_layout.addWidget(self.month_spin)
        datetime_layout.addLayout(month_layout)

        # 日选择
        day_layout = QVBoxLayout()
        day_layout.addWidget(QLabel("日:"))
        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 31)
        self.day_spin.setValue(QDateTime.currentDateTime().date().day())
        self.day_spin.setFixedWidth(60)
        day_layout.addWidget(self.day_spin)
        datetime_layout.addLayout(day_layout)

        # 小时选择
        hour_layout = QVBoxLayout()
        hour_layout.addWidget(QLabel("时:"))
        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 23)
        self.hour_spin.setValue(QDateTime.currentDateTime().time().hour())
        self.hour_spin.setFixedWidth(60)
        hour_layout.addWidget(self.hour_spin)
        datetime_layout.addLayout(hour_layout)

        layout.addLayout(datetime_layout)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Ok).setText("完成")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        layout.addWidget(button_box)

        self.setLayout(layout)

        # 连接月份和日期变化时的验证
        self.month_spin.valueChanged.connect(self._update_day_range)
        self.year_spin.valueChanged.connect(self._update_day_range)

    def _update_day_range(self):
        """根据年份和月份更新日期的最大值"""
        year = self.year_spin.value()
        month = self.month_spin.value()

        # 简单的闰年判断
        if month == 2:
            if (year % 400 == 0) or (year % 100 != 0 and year % 4 == 0):
                max_day = 29
            else:
                max_day = 28
        elif month in [4, 6, 9, 11]:
            max_day = 30
        else:
            max_day = 31

        self.day_spin.setRange(1, max_day)

    def get_datetime(self):
        """获取选择的日期时间"""
        return QDateTime(
            self.year_spin.value(),
            self.month_spin.value(),
            self.day_spin.value(),
            self.hour_spin.value(),
            0, 0
        )

class RegressionPlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=6, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(RegressionPlotCanvas, self).__init__(self.fig)
        self.setParent(parent)

        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    def plot_regression(self, x_data, y_data, slope, title="线性回归分析"):
        """绘制线性回归图"""
        self.axes.clear()

        # 绘制散点
        self.axes.scatter(x_data, y_data, alpha=0.6, color='blue', label='数据点')

        # 计算并绘制趋势线
        if len(x_data) > 0:
            x_line = np.linspace(min(x_data), max(x_data), 100)
            y_line = slope * x_line  # y = kx, 因为通过原点
            self.axes.plot(x_line, y_line, 'r-', linewidth=2, label=f'趋势线 (斜率 = {slope:.6f})')

        # 设置图表属性
        self.axes.set_xlabel('1/vy')
        self.axes.set_ylabel('Trimming Amount')
        self.axes.set_title(title)
        self.axes.legend()
        self.axes.grid(True, alpha=0.3)

        self.draw()

class BeamProfilePlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=6, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(BeamProfilePlotCanvas, self).__init__(self.fig)
        self.setParent(parent)

        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    def plot_beam_integration(self, x_coords, y_values, title="Beam Profile-沿y轴积分"):
        """绘制Beam Profile沿y轴积分曲线"""
        self.axes.clear()

        # 绘制曲线
        self.axes.plot(x_coords, y_values, 'b-', linewidth=2, marker='o', markersize=4)

        # 设置图表属性
        self.axes.set_xlabel('X坐标 (mm)')
        self.axes.set_ylabel('Y轴积分值')
        self.axes.set_title(title)
        self.axes.grid(True, alpha=0.3)

        # 设置x轴范围
        self.axes.set_xlim(-15, 15)

        self.draw()

class AnalyzerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.analyzer = WedgeTestAnalyzer()

        # 设置默认Recipe文件路径
        self.default_recipe_file = get_resource_path("Data/inputs/WedgeTestRecipe/For Calculation WedgeTestRecipe0819.csv")

        self.recipe_file = None
        self.initial_file = None
        self.after_file = None
        self.beam_profile_file = None  # 新增：存储Beam Profile文件路径

        # 添加图表组件
        self.regression_plot = RegressionPlotCanvas(self, width=6, height=4, dpi=100)
        self.beam_profile_plot = BeamProfilePlotCanvas(self, width=6, height=4, dpi=100)

        # 离子化室保养相关变量 - 强制使用配置文件
        import sys
        from pathlib import Path

        # 确定配置文件存储路径
        if getattr(sys, 'frozen', False):  # 打包后的exe环境
            # exe同目录下的config文件夹
            app_dir = Path(sys.executable).parent
            config_dir = app_dir / 'config'
        else:  # 开发环境
            # 脚本同目录下的config文件夹
            app_dir = Path(__file__).parent.parent
            config_dir = app_dir / 'config'

        # 确保config目录存在
        config_dir.mkdir(exist_ok=True)

        # 使用配置文件存储设置
        config_file = config_dir / 'maintenance.ini'
        self.settings = QSettings(str(config_file), QSettings.IniFormat)
        self.settings.setIniCodec("UTF-8")  # 支持中文

        # 调试信息（可选，发布时可注释掉）
        print(f"配置文件路径: {config_file}")
        print(f"设置格式: {'Ini文件' if self.settings.format() == QSettings.IniFormat else '注册表'}")

        self.maintenance_timer = QTimer()
        self.maintenance_timer.timeout.connect(self._update_usage_time)

        self._setup_ui()

        # 初始化默认Recipe文件
        self._initialize_default_recipe()

        # 加载机台参数数据
        self._load_machine_params()

        # 初始化保养时间显示
        self._load_maintenance_time()
        self.maintenance_timer.start(3600000)  # 每小时触发一次（3600000毫秒）

    def _initialize_default_recipe(self):
        """初始化默认Recipe文件"""
        try:
            # 检查默认Recipe文件是否存在
            if Path(self.default_recipe_file).exists():
                self.recipe_file = self.default_recipe_file
                self.recipe_label.setText("已选择默认Recipe文件")
            else:
                # 如果默认文件不存在，保持原状
                self.recipe_label.setText("默认Recipe文件不存在")
                self.recipe_file = None
        except Exception as e:
            print(f"初始化默认Recipe文件失败: {e}")
            self.recipe_file = None

    def _load_machine_params(self):
        """加载机台参数数据"""
        # 尝试从本地文件加载参数名称
        try:
            log_file = Path("2025110920.csv")
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)

                    # 读取表头（第一行）
                    headers = next(reader)
                    # 读取单位（第二行）
                    units = next(reader)

                    # 读取所有数据行以获取最后一行数据
                    data_rows = []
                    for row in reader:
                        if row:  # 跳过空行
                            data_rows.append(row)

                    if data_rows:
                        # 获取最后一行数据（包括时间列）
                        last_row = data_rows[-1]  # 包含时间列

                        # 创建参数名称到数值的映射
                        param_value_map = {}
                        for header, unit, value in zip(headers, units, last_row):
                            param_key = header.strip()

                            # 处理时间显示格式 - 去掉毫秒部分
                            if header == "Time" and ":" in value:
                                # 格式如 "20:36:16:756" -> "20:36:16"
                                time_parts = value.split(":")
                                if len(time_parts) >= 3:
                                    value = ":".join(time_parts[:3])  # 只取前3部分：时:分:秒

                            param_value_map[param_key] = value

                        # 按照1114.csv的固定顺序创建参数名称列表
                        fixed_param_names = [
                            "Time",
                            "PEG21", "PEG11",
                            "CCG01(GCIB)", "PIG01(GCIB)",
                            "Beam Current(Fixing)", "Beam Current(Moving)",
                            "Accelerator Current", "Accelerator Voltage",
                            "Lens1 Current", "Lens1 Voltage",
                            "Lens2 Current", "Lens2 Voltage",
                            "Suppressor Current", "Suppressor Voltage",  # 新顺序
                            "Bias Current", "Bias Voltage",  # 新顺序
                            "Arc Current", "Arc Voltage",
                            "Filament Current", "Filament Voltage",
                            "Neutralizer extracation Current", "Neutralizer extracation Voltage",
                            "Neutralizer filament Current", "Neutralizer filament Voltage",
                            "APC Pressure", "MFC111 Flow", "MFC112 Flow", "MFC113 Flow"
                        ]

                        # 创建表格数据（使用固定顺序）
                        table_data = []
                        for param in fixed_param_names:
                            if param in param_value_map:
                                table_data.append((param, param_value_map[param]))
                            else:
                                table_data.append((param, "等待读取..."))

                        # 添加Lifetime行
                        table_data.append(("Lifetime", "未设定"))

                        # 设置表格行数
                        self.machine_params_table.setRowCount(len(table_data))

                        # 填充表格数据
                        for row, (param_name, value) in enumerate(table_data):
                            # 参数名称
                            item_name = QTableWidgetItem(param_name)
                            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
                            self.machine_params_table.setItem(row, 0, item_name)

                            # 数值
                            item_value = QTableWidgetItem(value)
                            item_value.setFlags(item_value.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
                            self.machine_params_table.setItem(row, 1, item_value)

                        # 设置表格自适应内容
                        self.machine_params_table.resizeColumnsToContents()
                        self.machine_params_table.resizeRowsToContents()

                        print(f"成功加载 {len(table_data)} 个机台参数（按固定顺序）")
                        return

            # 如果本地文件不存在或加载失败，设置默认的参数名称（按照1114.csv排序）
            default_params = [
                "Time (HH:MM:SS)",
                "PEG21 ([Pa])",
                "PEG11 ([Pa])",
                "CCG01(GCIB) ([Pa])",
                "PIG01(GCIB) ([Pa])",
                "Beam Current(Fixing) ([uA])",
                "Beam Current(Moving) ([uA])",
                "Accelerator Current ([mA])",
                "Accelerator Voltage ([kV])",
                "Lens1 Current ([mA])",
                "Lens1 Voltage ([kV])",
                "Lens2 Current ([mA])",
                "Lens2 Voltage ([kV])",
                "Suppressor Current ([mA])",  # 移动到前面
                "Suppressor Voltage ([V])",   # 移动到前面
                "Bias Current ([mA])",        # 移动到后面
                "Bias Voltage ([kV])",        # 移动到后面
                "Arc Current ([mA])",
                "Arc Voltage ([V])",
                "Filament Current ([A])",
                "Filament Voltage ([V])",
                "Neutralizer extracation Current ([mA])",
                "Neutralizer extracation Voltage ([V])",
                "Neutralizer filament Current ([A])",
                "Neutralizer filament Voltage ([V])",
                "APC Pressure ([MPa])",
                "MFC111 Flow ([sccm])",
                "MFC112 Flow ([sccm])",
                "MFC113 Flow ([sccm])",
                "Lifetime (h)"  # 新增：离子化室使用时长
            ]

            # 设置表格行数
            self.machine_params_table.setRowCount(len(default_params))

            # 填充参数名称
            for row, param_name in enumerate(default_params):
                item_name = QTableWidgetItem(param_name)
                item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
                self.machine_params_table.setItem(row, 0, item_name)

                # 数值列设为空
                item_value = QTableWidgetItem("等待读取...")
                item_value.setFlags(item_value.flags() & ~Qt.ItemIsEditable)
                self.machine_params_table.setItem(row, 1, item_value)

            print(f"设置了默认参数名称，共 {len(default_params)} 个参数")

        except Exception as e:
            print(f"初始化机台参数失败: {e}")
            # 如果完全失败，至少设置基本结构
            self.machine_params_table.setRowCount(1)
            error_item = QTableWidgetItem("请点击\"读取当前机台参数\"按钮获取数据")
            error_item.setFlags(error_item.flags() & ~Qt.ItemIsEditable)
            self.machine_params_table.setItem(0, 0, error_item)
            self.machine_params_table.setItem(0, 1, QTableWidgetItem(""))

    def keyPressEvent(self, event):
        """处理键盘事件"""
        # Ctrl+C 复制选中的表格内容
        if event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
            self._copy_selected_data()
        else:
            super().keyPressEvent(event)

    def _show_context_menu(self, position):
        """显示表格区域右键菜单（增强版）"""
        # 创建新的右键菜单
        menu = QMenu(self)

        # 添加复制选中内容选项
        copy_action = menu.addAction("复制选中表格内容")
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self._copy_selected_data)

        # 添加全选选项
        select_all_action = menu.addAction("全选")
        select_all_action.setShortcut(QKeySequence.SelectAll)
        select_all_action.triggered.connect(self.machine_params_table.selectAll)

        # 显示菜单 - position是QPoint对象，直接转换坐标
        global_pos = self.machine_params_table.viewport().mapToGlobal(position)
        menu.exec_(global_pos)

    def _show_header_context_menu(self, position):
        """显示表头右键菜单"""
        # 创建新的右键菜单
        menu = QMenu(self)

        # 添加复制选中内容选项
        copy_action = menu.addAction("复制选中表格内容")
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self._copy_selected_data)

        # 添加全选选项
        select_all_action = menu.addAction("全选")
        select_all_action.setShortcut(QKeySequence.SelectAll)
        select_all_action.triggered.connect(self.machine_params_table.selectAll)

        # 显示菜单 - 从表头转换坐标
        header = self.machine_params_table.horizontalHeader()
        global_pos = header.mapToGlobal(position)
        menu.exec_(global_pos)

    def _copy_selected_data(self):
        """复制选中的表格数据到剪贴板（增强版）"""
        selected_items = self.machine_params_table.selectedItems()
        if not selected_items:
            return

        # 准备复制的数据
        copied_data = []

        # 获取选中的行和列
        selected_rows = sorted(set(item.row() for item in selected_items))
        selected_cols = sorted(set(item.column() for item in selected_items))

        # 按行组织数据
        for row in selected_rows:
            row_data = []
            for col in selected_cols:
                # 查找该行该列是否有选中的项目
                found = False
                for item in selected_items:
                    if item.row() == row and item.column() == col:
                        row_data.append(item.text())
                        found = True
                        break
                if not found:
                    row_data.append("")

            # 只添加非空行（除非只选择了一列）
            if any(row_data) or len(selected_cols) == 1:
                copied_data.append("\t".join(row_data))

        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(copied_data))

        # 输出复制信息
        if len(selected_rows) == 1 and len(selected_cols) == 1:
            print(f"已复制 1 个单元格数据到剪贴板")
        elif len(selected_cols) == 1:
            print(f"已复制 {len(selected_rows)} 个单元格数据到剪贴板（单列）")
        elif len(selected_rows) == 1:
            print(f"已复制 {len(selected_cols)} 个单元格数据到剪贴板（单行）")
        else:
            print(f"已复制 {len(selected_rows)} 行 × {len(selected_cols)} 列数据到剪贴板")

    def read_current_machine_params(self, silent=False):
        """读取当前机台参数

        Args:
            silent: 是否静默模式（不显示消息框）
        """
        try:
            # 获取状态栏的引用
            if hasattr(self, "parent") and hasattr(self.parent(), "window") and hasattr(self.parent().window(), "status_bar"):
                status_bar = self.parent().window().status_bar
            else:
                status_bar = None

            # 机台log文件路径
            machine_log_path = Path(r"C:\D2216\Bin\Log\SamplingLog\ScanData")

            if not machine_log_path.exists():
                error_msg = f"机台log路径不存在: {machine_log_path}"
                if not silent:
                    if status_bar:
                        status_bar.showMessage(error_msg)
                    else:
                        QMessageBox.warning(self, "警告", error_msg)
                return

            # 搜索最新的CSV文件
            latest_file = None
            latest_time = None

            for file_path in machine_log_path.glob("*.csv"):
                try:
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if latest_time is None or file_time > latest_time:
                        latest_time = file_time
                        latest_file = file_path
                except Exception as e:
                    print(f"检查文件时间失败 {file_path}: {e}")
                    continue

            if latest_file is None:
                error_msg = "未找到机台log文件"
                if not silent:
                    if status_bar:
                        status_bar.showMessage(error_msg)
                    else:
                        QMessageBox.warning(self, "警告", error_msg)
                return

            # 读取最新文件的最后一行数据
            scan_data = {}
            with open(latest_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)

                # 读取表头和单位
                headers = next(reader)
                units = next(reader)

                # 读取所有数据行
                data_rows = []
                for row in reader:
                    if row:  # 跳过空行
                        data_rows.append(row)

                if not data_rows:
                    error_msg = "机台log文件没有数据"
                    if not silent:
                        if status_bar:
                            status_bar.showMessage(error_msg)
                        else:
                            QMessageBox.warning(self, "警告", error_msg)
                    return

                # 获取最后一行数据并存储到字典中
                last_row = data_rows[-1]
                for header, value in zip(headers, last_row):
                    scan_data[header] = value

            # 读取PM文件夹中的PIG01数据
            pig01_value = "N/A"
            try:
                pm_log_path = Path(r"C:\D2216\Bin\Log\SamplingLog\PM")
                if pm_log_path.exists():
                    # 搜索最新的CSV文件
                    latest_pm_file = None
                    latest_pm_time = None

                    for file_path in pm_log_path.glob("*.csv"):
                        try:
                            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if latest_pm_time is None or file_time > latest_pm_time:
                                latest_pm_time = file_time
                                latest_pm_file = file_path
                        except Exception as e:
                            continue

                    if latest_pm_file:
                        with open(latest_pm_file, 'r', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            pm_headers = next(reader)
                            pm_units = next(reader)
                            pm_data_rows = []
                            for row in reader:
                                if row:
                                    pm_data_rows.append(row)

                            if pm_data_rows:
                                pm_last_row = pm_data_rows[-1]
                                # 查找PIG01(GCIB)列
                                for i, header in enumerate(pm_headers):
                                    if header == "PIG01(GCIB)" and i < len(pm_last_row):
                                        pig01_value = pm_last_row[i]
                                        break
            except Exception as e:
                print(f"读取PIG01数据失败: {e}")

            # 定义新的参数顺序和对应的键名（按照1114.csv排序）
            param_mapping = [
                ("Time", "Time"),
                ("PEG21", "PEG21"),
                ("PEG11", "PEG11"),
                ("CCG01(GCIB)", "CCG01(GCIB)"),
                ("PIG01(GCIB)", "PIG01(GCIB)"),  # 来自PM文件
                ("Beam Current(Fixing)", "Beam Current(Fixing)"),
                ("Beam Current(Moving)", "Beam Current(Moving)"),
                ("Accelerator Current", "Accelerator Current"),
                ("Accelerator Voltage", "Accelerator Voltage"),
                ("Lens1 Current", "Lens1 Current"),
                ("Lens1 Voltage", "Lens1 Voltage"),
                ("Lens2 Current", "Lens2 Current"),
                ("Lens2 Voltage", "Lens2 Voltage"),
                ("Suppressor Current", "Suppressor Current"),  # 移动到前面
                ("Suppressor Voltage", "Suppressor Voltage"),   # 移动到前面
                ("Bias Current", "Bias Current"),  # 移动到后面
                ("Bias Voltage", "Bias Voltage"),  # 移动到后面
                ("Arc Current", "Arc Current"),
                ("Arc Voltage", "Arc Voltage"),
                ("Filament Current", "Filament Current"),
                ("Filament Voltage", "Filament Voltage"),
                ("Neutralizer extracation Current", "Neutralizer extracation Current"),
                ("Neutralizer extracation Voltage", "Neutralizer extracation Voltage"),
                ("Neutralizer filament Current", "Neutralizer filament Current"),
                ("Neutralizer filament Voltage", "Neutralizer filament Voltage"),
                ("APC Pressure", "APC Pressure"),
                ("MFC111 Flow", "MFC111 Flow"),
                ("MFC112 Flow", "MFC112 Flow"),
                ("MFC113 Flow", "MFC113 Flow"),
                ("Lifetime", "Lifetime")  # 新增：离子化室使用时长
            ]

            # 确保表格有足够的行数
            if self.machine_params_table.rowCount() < len(param_mapping):
                self.machine_params_table.setRowCount(len(param_mapping))

            # 更新表格数据（按新的顺序）
            for row, (display_name, key_name) in enumerate(param_mapping):
                # 更新表格第一列的参数名称
                param_name_item = QTableWidgetItem(display_name)
                param_name_item.setFlags(param_name_item.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
                self.machine_params_table.setItem(row, 0, param_name_item)

                # 获取对应的值
                if key_name == "PIG01(GCIB)":
                    value = pig01_value
                elif key_name == "Lifetime":
                    # 获取离子化室使用时长
                    value = self._get_lifetime_hours()
                else:
                    value = scan_data.get(key_name, "N/A")

                # 处理时间显示格式
                if key_name == "Time" and ":" in value:
                    time_parts = value.split(":")
                    if len(time_parts) >= 3:
                        value = ":".join(time_parts[:3])

                # 更新表格第二列的数值
                value_item = QTableWidgetItem(str(value))
                value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
                self.machine_params_table.setItem(row, 1, value_item)

            print(f"更新了 {len(param_mapping)} 个参数值")

            # 自动复制第二列数值到剪贴板
            self._copy_params_to_clipboard()

            if not silent:
                success_msg = f"成功更新机台参数 (来源: {latest_file.name}) - 数值已复制到剪贴板"
                if status_bar:
                    status_bar.showMessage(success_msg)
                else:
                    QMessageBox.information(self, "成功", success_msg)

        except Exception as e:
            error_msg = f"读取机台参数失败: {str(e)}"
            if not silent:
                if status_bar:
                    status_bar.showMessage(error_msg)
                else:
                    QMessageBox.critical(self, "错误", error_msg)

    def _setup_ui(self):
        main_layout = QGridLayout()

        # 创建水平分隔栏
        splitter = QSplitter(Qt.Horizontal)

        # 左侧栏：当前机台参数
        machine_params_group = QGroupBox("当前机台参数")
        machine_params_layout = QGridLayout()

        # 创建机台参数表格
        self.machine_params_table = QTableWidget()
        self.machine_params_table.setColumnCount(2)
        self.machine_params_table.setHorizontalHeaderLabels(["参数名称", "数值"])

        # 设置表格属性
        header = self.machine_params_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 第一列自适应宽度
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 第二列自适应宽度
        self.machine_params_table.setAlternatingRowColors(True)  # 交替行颜色
        self.machine_params_table.setSelectionBehavior(QTableWidget.SelectItems)  # 改为项目选择模式，可以单独选中单元格
        self.machine_params_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 禁止编辑
        # 移除排序功能：self.machine_params_table.setSortingEnabled(True)  # 禁止排序

        # 启用复制功能
        self.machine_params_table.setSelectionMode(QTableWidget.ExtendedSelection)  # 允许多选
        self.machine_params_table.setContextMenuPolicy(Qt.CustomContextMenu)  # 启用右键菜单
        self.machine_params_table.customContextMenuRequested.connect(self._show_context_menu)

        # 设置表格头部也可以右键
        header = self.machine_params_table.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_header_context_menu)

        machine_params_layout.addWidget(self.machine_params_table, 0, 0)

        machine_params_group.setLayout(machine_params_layout)

        # 右侧栏容器
        right_container = QWidget()
        right_layout = QGridLayout(right_container)

        # 右上侧容器（分为左右两部分）
        top_right_container = QWidget()
        top_right_layout = QGridLayout(top_right_container)

        # 右上的左侧：文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QFormLayout()

        self.recipe_label = QLabel("已选择默认Recipe文件")
        self.select_recipe_button = QPushButton("选择非默认Recipe的其他的Recipe")
        self.select_recipe_button.clicked.connect(self.select_recipe)

        file_layout.addRow("Recipe文件:", self.recipe_label)
        file_layout.addRow(self.select_recipe_button)

        self.initial_label = QLabel("未选择初始厚度文件")
        self.select_initial_button = QPushButton("选择初始厚度")
        self.select_initial_button.clicked.connect(self.select_initial)

        file_layout.addRow("初始厚度文件:", self.initial_label)
        file_layout.addRow(self.select_initial_button)

        self.after_label = QLabel("未选择刻蚀后厚度文件")
        self.select_after_button = QPushButton("选择刻蚀后厚度")
        self.select_after_button.clicked.connect(self.select_after)

        file_layout.addRow("刻蚀后厚度文件:", self.after_label)
        file_layout.addRow(self.select_after_button)

        # === Beam Profile选择 ===
        self.beam_profile_label = QLabel("未选择Beam Profile文件")
        self.select_beam_button = QPushButton("选择Beam Profile")
        self.select_beam_button.clicked.connect(self.select_beam_profile)

        self.process_beam_check = QCheckBox("处理Beam Profile")
        self.process_beam_check.setChecked(True)
        self.process_beam_check.setToolTip("勾选后将根据计算得到的Beam peak值调整Beam Profile")

        file_layout.addRow("Beam Profile文件:", self.beam_profile_label)
        file_layout.addRow(self.select_beam_button)
        file_layout.addRow(self.process_beam_check)
        # ============================

        file_group.setLayout(file_layout)

        # 右上的右侧：分析设置区域
        analysis_group = QGroupBox("分析设置")
        analysis_layout = QFormLayout()

        self.k_factor = QLineEdit("1.0")
        self.k_factor.setPlaceholderText("输入系数k")

        # 创建按钮容器
        button_container = QWidget()
        button_layout = QGridLayout(button_container)

        self.execute_analysis_button = QPushButton("执行分析")
        self.execute_analysis_button.clicked.connect(self.execute_analysis)
        self.execute_analysis_button.setFixedSize(180, 60)  # 宽度变为1/3，高度变为2倍

        self.read_machine_params_button = QPushButton("读取当前机台参数")
        self.read_machine_params_button.clicked.connect(self.read_current_machine_params)
        self.read_machine_params_button.setFixedSize(210, 60)  # 设置合适的尺寸

        # 将两个按钮添加到按钮容器
        button_layout.addWidget(self.execute_analysis_button, 0, 0)
        button_layout.addWidget(self.read_machine_params_button, 0, 1)

        analysis_layout.addRow("系数 k:", self.k_factor)
        analysis_layout.addRow(button_container)

        self.beam_peak_label = QLineEdit()
        self.beam_peak_label.setReadOnly(True)
        self.beam_peak_label.setPlaceholderText("分析后显示结果")
        analysis_layout.addRow("Beam Peak:", self.beam_peak_label)

        self.beam_integration_label = QLineEdit()
        self.beam_integration_label.setReadOnly(True)
        self.beam_integration_label.setPlaceholderText("分析后显示结果")
        analysis_layout.addRow("Beam integration:", self.beam_integration_label)

        self.export_check = QCheckBox("导出回归分析数据")
        self.export_check.setChecked(True)
        analysis_layout.addRow(self.export_check)

        # 新增：设定保养时间按钮（移动到这里）
        self.set_maintenance_time_button = QPushButton()
        self.set_maintenance_time_button.clicked.connect(self._set_maintenance_time)
        self.set_maintenance_time_button.setFixedSize(300, 80)  # 调整按钮大小适应布局

        # 使用换行符 \n 实现文字换行
        button_text = "设定最近一次\n离子化室保养完成时间"
        self.set_maintenance_time_button.setText(button_text)

        # 设置按钮样式，确保文字居中且字体合适
        self.set_maintenance_time_button.setStyleSheet("""
            QPushButton {
                text-align: center;
                font-size: 18px;
                padding: 8px;
                font-family: Microsoft YaHei, SimHei, Arial;
                font-weight: bold;
            }
        """)
        analysis_layout.addRow(self.set_maintenance_time_button)

        # 新增：离子化室使用时长显示框（移动到这里）
        self.usage_time_label = QLineEdit()
        self.usage_time_label.setReadOnly(True)
        self.usage_time_label.setPlaceholderText("未设定保养时间")
        analysis_layout.addRow(self.usage_time_label)

        analysis_group.setLayout(analysis_layout)

        # 将文件选择和分析设置添加到右上侧容器
        top_right_layout.addWidget(file_group, 0, 0)      # 右上的左侧
        top_right_layout.addWidget(analysis_group, 0, 1)   # 右上的右侧

        # 设置右上侧左右两部分的列伸缩比例
        top_right_layout.setColumnStretch(0, 1)  # 文件选择区域
        top_right_layout.setColumnStretch(1, 1)  # 分析设置区域

        # 右下侧：绘图区域（分为左右两部分）
        plot_container = QWidget()
        plot_layout = QGridLayout(plot_container)

        # 左侧：线性回归分析图表
        regression_group = QGroupBox("线性回归分析")
        regression_plot_layout = QGridLayout()
        regression_plot_layout.addWidget(self.regression_plot, 0, 0)
        regression_group.setLayout(regression_plot_layout)

        # 右侧：Beam Profile图表
        beam_profile_group = QGroupBox("Beam Profile-沿y轴积分")
        beam_profile_plot_layout = QGridLayout()
        beam_profile_plot_layout.addWidget(self.beam_profile_plot, 0, 0)
        beam_profile_group.setLayout(beam_profile_plot_layout)

        # 将左右两个图表添加到绘图容器
        plot_layout.addWidget(regression_group, 0, 0)  # 左侧
        plot_layout.addWidget(beam_profile_group, 0, 1)  # 右侧

        # 设置左右两部分的列伸缩比例
        plot_layout.setColumnStretch(0, 1)  # 左侧
        plot_layout.setColumnStretch(1, 1)  # 右侧

        # 将右上侧容器和右下侧图表添加到右侧栏布局
        right_layout.addWidget(top_right_container, 0, 0)   # 右上侧
        right_layout.addWidget(plot_container, 1, 0)        # 右下侧

        # 设置右侧栏上下部分的行伸缩比例（25% : 75%）
        right_layout.setRowStretch(0, 1)   # 右上侧占25%
        right_layout.setRowStretch(1, 3)   # 右下侧占75%

        # 将左右两侧添加到分隔栏
        splitter.addWidget(machine_params_group)     # 左侧栏
        splitter.addWidget(right_container)          # 右侧栏

        # 设置分隔栏的初始比例（40% : 60%）
        splitter.setSizes([400, 600])  # 初始宽度比例
        splitter.setStretchFactor(0, 4)  # 左侧拉伸因子
        splitter.setStretchFactor(1, 6)  # 右侧拉伸因子

        # 将分隔栏添加到主布局
        main_layout.addWidget(splitter, 0, 0)

        self.setLayout(main_layout)
    
    def set_files(self, recipe_file, initial_file, after_file):
        """设置所有文件"""
        self.set_recipe_file(recipe_file)
        self.set_initial_file(initial_file)
        self.set_after_file(after_file)
    
    def set_recipe_file(self, file_path):
        """设置Recipe文件"""
        self.recipe_file = file_path
        if file_path == self.default_recipe_file:
            self.recipe_label.setText("已选择默认Recipe文件")
        else:
            self.recipe_label.setText(file_path)
    
    def set_initial_file(self, file_path):
        """设置初始厚度文件"""
        self.initial_file = file_path
        self.initial_label.setText(file_path)
    
    def set_after_file(self, file_path):
        """设置刻蚀后文件"""
        self.after_file = file_path
        self.after_label.setText(file_path)
    
    def select_recipe(self):
        """选择非默认的Recipe文件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择非默认Recipe的其他的Recipe", "", "CSV Files (*.csv)", options=options)

        if file_path:
            self.set_recipe_file(file_path)
    
    def select_initial(self):
        """选择初始厚度文件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择初始厚度文件", "", "CSV Files (*.csv)", options=options)
        
        if file_path:
            self.set_initial_file(file_path)
    
    def select_after(self):
        """选择刻蚀后厚度文件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择刻蚀后厚度文件", "", "CSV Files (*.csv)", options=options)
        
        if file_path:
            self.set_after_file(file_path)
    
    def select_beam_profile(self):
        """新增：选择Beam Profile文件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Beam Profile文件", "", "CSV Files (*.csv)", options=options)
        
        if file_path:
            self.beam_profile_file = file_path
            self.beam_profile_label.setText(file_path)
    
    def execute_analysis(self):
        """执行分析过程"""
        # 获取状态栏的引用
        if hasattr(self, "parent") and hasattr(self.parent(), "window") and hasattr(self.parent().window(), "status_bar"):
            status_bar = self.parent().window().status_bar
        else:
            # 如果无法直接获取，使用简单的消息框替代
            status_bar = None
        
        # 自动读取机台参数以确保日志中有实际数据（静默模式）
        try:
            self.read_current_machine_params(silent=True)
        except Exception as e:
            print(f"自动读取机台参数失败: {e}")
            # 即使自动读取失败，也继续执行分析流程

        # 检查必要文件
        if not all([self.recipe_file, self.initial_file, self.after_file]):
            # 使用状态栏或消息框
            if status_bar:
                status_bar.showMessage("请选择所有必要的文件")
            else:
                QMessageBox.warning(self, "警告", "请选择Recipe文件和厚度文件")
            return

        # 检查Recipe文件是否存在
        if not Path(self.recipe_file).exists():
            error_msg = f"Recipe文件不存在: {self.recipe_file}"
            if status_bar:
                status_bar.showMessage(error_msg)
            else:
                QMessageBox.warning(self, "警告", error_msg)
            return
        
        try:
            # 获取系数k
            k = float(self.k_factor.text())
            
            # 执行分析
            self.analyzer.load_recipe(self.recipe_file)
            self.analyzer.load_thickness(self.initial_file, self.after_file)
            self.analyzer.transfer_trimming_amount()

            # 计算斜率（用于日志记录和图表显示）
            slope = self.analyzer.calculate_slope()

            # 导出回归数据（如果需要）
            if self.export_check.isChecked():
                export_path = self.analyzer.export_regression_data()
                if status_bar:
                    status_bar.showMessage(f"已导出回归数据: {export_path}")
                else:
                    QMessageBox.information(self, "信息", f"已导出回归数据到: {export_path}")

            # 计算并显示Beam Peak
            beam_peak = self.analyzer.calculate_beam_peak(k)
            self.beam_peak_label.setText(f"{beam_peak:.6f}")

            # 更新回归图表
            try:
                x_data, y_data = self.analyzer.get_regression_data()
                # 使用已经计算好的slope
                self.regression_plot.plot_regression(x_data, y_data, slope, f"线性回归分析 (斜率: {slope:.6f})")
            except Exception as plot_e:
                print(f"图表更新失败: {plot_e}")

            # 初始化Beam相关变量
            beam_integration = None
            process_beam_success = False

            # 新增：处理Beam Profile文件
            if self.process_beam_check.isChecked() and self.beam_profile_file:
                try:
                    # 验证Beam Profile文件是否存在
                    beam_path = Path(self.beam_profile_file)
                    if not beam_path.exists():
                        raise FileNotFoundError(f"找不到Beam Profile文件: {self.beam_profile_file}")

                    # 询问用户是否需要重命名并保存到其他地址
                    reply = QMessageBox.question(
                        self,
                        "保存Beam Profile文件",
                        "是否需要重命名并保存到其他地址？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )

                    # 处理Beam Profile
                    new_profile = self.analyzer.process_beam_profile(beam_path)

                    # 计算Beam Profile沿y轴积分
                    x_coords, y_integration, total_integration = self.analyzer.calculate_beam_y_integration(new_profile)

                    # 更新Beam integration显示
                    self.beam_integration_label.setText(f"{total_integration:.6f}")
                    beam_integration = total_integration

                    # 绘制Beam Profile沿y轴积分曲线
                    self.beam_profile_plot.plot_beam_integration(x_coords, y_integration)

                    # 设置Beam处理成功标志
                    process_beam_success = True

                    if reply == QMessageBox.Yes:
                        # 用户选择自定义保存位置
                        options = QFileDialog.Options()
                        suggested_name = f"Processed_{beam_path.stem}.csv"
                        save_path, _ = QFileDialog.getSaveFileName(
                            self,
                            "保存新的Beam Profile文件",
                            suggested_name,
                            "CSV Files (*.csv)",
                            options=options
                        )

                        if save_path:
                            # 复制文件到用户指定的位置
                            shutil.copy2(new_profile, save_path)
                            final_path = Path(save_path)
                            success_msg = f"分析完成! Beam Peak = {beam_peak:.6f}\n已生成新的Beam Profile: {final_path.name} (已保存到指定位置)\nBeam integration = {total_integration:.6f}"
                        else:
                            # 用户取消了保存对话框，使用默认保存位置
                            success_msg = f"分析完成! Beam Peak = {beam_peak:.6f}\n已生成新的Beam Profile: {new_profile.name} (保存到默认位置)\nBeam integration = {total_integration:.6f}"
                    else:
                        # 用户选择默认保存位置
                        success_msg = f"分析完成! Beam Peak = {beam_peak:.6f}\n已生成新的Beam Profile: {new_profile.name} (保存到默认位置)\nBeam integration = {total_integration:.6f}"

                    # 更新UI显示
                    if status_bar:
                        status_bar.showMessage(success_msg)
                    else:
                        QMessageBox.information(self, "成功", success_msg)

                except Exception as beam_e:
                    error_msg = f"Beam Profile处理失败: {str(beam_e)}"
                    if status_bar:
                        status_bar.showMessage(error_msg)
                    else:
                        QMessageBox.warning(self, "警告", error_msg)
            else:
                # 显示成功消息（未处理Beam）
                success_msg = f"分析完成! Beam Peak = {beam_peak:.6f}"
                if status_bar:
                    status_bar.showMessage(success_msg)
                else:
                    QMessageBox.information(self, "成功", success_msg)

            # 在所有分析完成后保存日志（始终使用新格式）
            self._save_analysis_log(slope, beam_peak, beam_integration, k)
                
        except Exception as e:
            error_msg = f"分析失败: {str(e)}"
            self.beam_peak_label.setText("错误")
            # 清空图表
            try:
                self.regression_plot.axes.clear()
                self.regression_plot.axes.text(0.5, 0.5, '分析失败',
                                               horizontalalignment='center',
                                               verticalalignment='center',
                                               transform=self.regression_plot.axes.transAxes)
                self.regression_plot.draw()
            except:
                pass

            if status_bar:
                status_bar.showMessage(error_msg)
            else:
                QMessageBox.critical(self, "错误", error_msg)

    def _set_maintenance_time(self):
        """设定离子化室保养时间"""
        dialog = MaintenanceTimeDialog(self)

        # 如果之前有设定过时间，显示之前的时间
        saved_time = self.settings.value("maintenance_time")
        if saved_time:
            saved_datetime = QDateTime.fromString(saved_time, Qt.ISODate)
            if saved_datetime.isValid():
                dialog.year_spin.setValue(saved_datetime.date().year())
                dialog.month_spin.setValue(saved_datetime.date().month())
                dialog.day_spin.setValue(saved_datetime.date().day())
                dialog.hour_spin.setValue(saved_datetime.time().hour())

        if dialog.exec_() == QDialog.Accepted:
            selected_datetime = dialog.get_datetime()

            # 保存到设置文件
            self.settings.setValue("maintenance_time", selected_datetime.toString(Qt.ISODate))
            self.settings.sync()

            # 立即更新显示
            self._update_usage_time()

            QMessageBox.information(self, "成功", "保养时间设定完成！")

    def _load_maintenance_time(self):
        """加载保存的保养时间并更新显示"""
        saved_time = self.settings.value("maintenance_time")
        if saved_time:
            self._update_usage_time()

    def _update_usage_time(self):
        """更新离子化室使用时长显示"""
        saved_time = self.settings.value("maintenance_time")
        if not saved_time:
            self.usage_time_label.setText("未设定保养时间")
            return

        maintenance_datetime = QDateTime.fromString(saved_time, Qt.ISODate)
        if not maintenance_datetime.isValid():
            self.usage_time_label.setText("保养时间数据无效")
            return

        current_datetime = QDateTime.currentDateTime()

        # 计算时间差（以小时为单位）
        time_diff_seconds = maintenance_datetime.secsTo(current_datetime)
        usage_hours = time_diff_seconds / 3600.0

        # 格式化显示 - 统一显示为小时
        self.usage_time_label.setText(f"离子化室使用时长：{usage_hours:.1f} 小时")

        # 如果使用时长超过一定时间，可以改变颜色提醒
        if usage_hours > 1000:  # 超过1000小时
            self.usage_time_label.setStyleSheet("color: red; font-weight: bold;")
        elif usage_hours > 720:  # 超过30天
            self.usage_time_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.usage_time_label.setStyleSheet("color: black;")

    def _get_lifetime_hours(self):
        """获取离子化室使用时长（用于机台参数表格显示）"""
        saved_time = self.settings.value("maintenance_time")
        if not saved_time:
            return "未设定"

        maintenance_datetime = QDateTime.fromString(saved_time, Qt.ISODate)
        if not maintenance_datetime.isValid():
            return "数据无效"

        current_datetime = QDateTime.currentDateTime()
        time_diff_seconds = maintenance_datetime.secsTo(current_datetime)
        usage_hours = time_diff_seconds / 3600.0

        # 返回一位小数的格式
        return f"{usage_hours:.1f}h"

    def _copy_params_to_clipboard(self):
        """自动复制机台参数表格的第二列数值到剪贴板"""
        try:
            # 获取表格行数
            row_count = self.machine_params_table.rowCount()

            if row_count == 0:
                print("表格为空，无法复制数据")
                return

            # 收集第二列的所有数值
            param_values = []
            for row in range(row_count):
                item = self.machine_params_table.item(row, 1)  # 第二列（索引为1）
                if item:
                    param_values.append(item.text())
                else:
                    param_values.append("")  # 空值处理

            # 将数值用换行符连接
            clipboard_text = "\n".join(param_values)

            # 复制到剪贴板
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_text)

            print(f"已自动复制 {len(param_values)} 个机台参数数值到剪贴板")

        except Exception as e:
            print(f"自动复制到剪贴板失败: {str(e)}")

    def _save_analysis_log(self, slope, beam_peak=None, beam_integration=None, k_factor=None):
        """保存分析日志到WedgeTest_Log文件夹 - 始终生成36行新格式"""
        try:
            # 获取当前时间戳
            current_time = QDateTime.currentDateTime()
            timestamp_str = current_time.toString("yyyyMMdd_hhmmss")

            # 统一生成新格式的日志文件名
            log_filename = f"{timestamp_str}_Wedge_beam_Log.csv"

            # 确保WedgeTest_Log目录存在
            log_dir = get_resource_path("Data/outputs/WedgeTest_Log")
            Path(log_dir).mkdir(parents=True, exist_ok=True)

            log_file_path = Path(log_dir) / log_filename

            # 准备日志内容
            log_content = []

            # 添加日期行（第一行）
            date_str = current_time.toString("yyyy-MM-dd")
            log_content.append(date_str)

            # 添加斜率行（第二行）
            log_content.append(f"斜率,{slope:.8f}")  # 保留8位小数，提高精度

            # 始终添加4行新内容（在斜率行之后）
            if beam_peak is not None and beam_integration is not None and k_factor is not None:
                # 有Beam Profile数据时的处理
                # 计算coefficient_integration
                if slope != 0:
                    coefficient_integration = beam_integration / slope
                else:
                    coefficient_integration = 0  # 避免除零错误

                # 添加新的4行数据（有值）
                log_content.append(f"coefficient_peak,{k_factor:.8f}")
                log_content.append(f"Beam_peak,{beam_peak:.8f}")
                log_content.append(f"Beam_integration,{beam_integration:.8f}")
                log_content.append(f"coefficient_integration,{coefficient_integration:.8f}")
            else:
                # 没有Beam Profile数据时的处理（留空）
                log_content.append("coefficient_peak,")
                log_content.append("Beam_peak,")
                log_content.append("Beam_integration,")
                log_content.append("coefficient_integration,")

            # 添加当前机台参数表格内容
            row_count = self.machine_params_table.rowCount()
            col_count = self.machine_params_table.columnCount()

            for row in range(row_count):
                row_data = []
                for col in range(col_count):
                    item = self.machine_params_table.item(row, col)
                    if item:
                        row_data.append(item.text())
                    else:
                        row_data.append("")

                # 添加行数据
                log_content.append(",".join(row_data))

            # 写入日志文件
            with open(log_file_path, 'w', encoding='utf-8') as file:
                for line in log_content:
                    file.write(line + '\n')

            print(f"分析日志已保存: {log_file_path}")

        except Exception as e:
            print(f"保存分析日志失败: {str(e)}")
