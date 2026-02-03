import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QFileDialog, QLabel, QTabWidget, QProgressBar, QGroupBox, 
    QSizePolicy, QFrame, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path

from utils.file_io import get_resource_path
from core.beamshape_Moulding import reconstruct_beam_profile
from core.rawData_processor import process_and_save_outputs

class RawDataThread(QThread):
    """用于后台处理原始数据的线程"""
    finished = pyqtSignal(tuple)  # 返回三个文件路径
    log = pyqtSignal(str)

    def __init__(self, initial_file, after_file, output_dir):
        super().__init__()
        self.initial_file = initial_file
        self.after_file = after_file
        self.output_dir = output_dir

    def run(self):
        try:
            self.log.emit("开始处理原始数据...")
            results = process_and_save_outputs(
                self.initial_file, 
                self.after_file, 
                self.output_dir
            )
            self.finished.emit(results)
            self.log.emit(f"原始数据处理完成! 文件保存至:{Path(results[0]).parent}")
        except Exception as e:
            self.log.emit(f"数据处理失败: {str(e)}")

class ReconstructionThread(QThread):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    update_progress = pyqtSignal(int)

    def __init__(self, x_file, y_file, output_dir):
        super().__init__()
        self.x_file = x_file
        self.y_file = y_file
        self.output_dir = output_dir

    def run(self):
        try:
            self.log.emit("开始重构离子束形状...")
            result = reconstruct_beam_profile(
                self.x_file, self.y_file, self.output_dir)
            self.finished.emit(result)
            self.log.emit("重构完成!")
        except Exception as e:
            self.log.emit(f"重构失败: {str(e)}")

class ShapeMouldingUI(QWidget):
    def __init__(self):
        super().__init__()
        self.x_file = None
        self.y_file = None
        self.result = None
        self.initial_file = None
        self.after_file = None
        
        # 输出目录设置
        self.output_dir = get_resource_path("Data/outputs/new_BeamShapeProfile")
        self.data_processor_dir = get_resource_path("Data/outputs")
        
        self.init_ui()
        self.reconstruction_thread = None
        self.raw_data_thread = None

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 主垂直分割器 (上下两部分)
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setChildrenCollapsible(False)

        # 设置初始比例 (4:2)
        main_splitter.setSizes([250, 750])
        
        # ============= 上部区域 (水平分割为左右两部分) =============
        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.setChildrenCollapsible(False)
        
        # 左：重构控制区
        recon_container = QFrame()
        recon_layout = QVBoxLayout(recon_container)
        
        # 重构控制台区域
        recon_control = self.create_recon_control_container()
        recon_layout.addWidget(recon_control)
        
        # 右：原始数据处理区
        data_processor_panel = self.create_data_processor_panel()
        
        # 添加到上部分割器
        top_splitter.addWidget(recon_container)
        top_splitter.addWidget(data_processor_panel)
        
        # 设置初始比例 (4:2)
        top_splitter.setSizes([600, 400])
        
        # ============= 下部区域 =============
        result_container = self.create_result_container()
        
        # 添加到主分割器
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(result_container)
        
        # 设置主分割器比例 (1:4)
        main_splitter.setSizes([200, 600])
        
        main_layout.addWidget(main_splitter)
        
    def create_recon_control_container(self):
        """创建重构控制区容器"""
        container = QFrame()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        
        # 控制台区域
        control_container = self.create_control_container()
        layout.addWidget(control_container)
        
        return container
        
    def create_data_processor_panel(self):
        """创建原始数据处理面板"""
        panel = QGroupBox("原始数据处理")
        panel.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 10pt;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QGroupBox::title { 
                background-color: transparent; 
                padding: 4px;
                subcontrol-origin: margin;
                left: 10px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 20, 15, 15)  # 顶部增加内边距
        
        # 初始文件选择
        self.create_file_selector(
            "initial", "选择初始膜厚文件 (Initial)", 
            "未选择初始文件", layout
        )
        
        # 扫描后文件选择
        self.create_file_selector(
            "after", "选择扫描后膜厚文件 (After)", 
            "未选择扫描后文件", layout
        )
        
        # 处理按钮
        process_btn = QPushButton("处理原始数据")
        process_btn.setFixedHeight(40)
        process_btn.setStyleSheet("""
            QPushButton {
                background-color: #8e44ad;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #9b59b6;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        process_btn.clicked.connect(self.process_raw_data)
        layout.addWidget(process_btn)

        # 添加间距
        #layout.addSpacing(20)

        # 结果显示区域
        results_group = QGroupBox("输出文件路径")
        results_group.setStyleSheet("""
            QGroupBox {
                border: none;
                font-weight: bold;
                font-size: 10pt;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        results_layout = QVBoxLayout(results_group)
        results_layout.setContentsMargins(5, 10, 5, 10)  # 增加上下内边距
        
        # 刻蚀量文件标签
        self.trimming_file_label = QLabel("刻蚀量文件: 未生成")
        self.trimming_file_label.setWordWrap(True)
        self.trimming_file_label.setStyleSheet("background-color: #f8f9fa; padding: 8px; border-radius: 4px;")
        results_layout.addWidget(self.trimming_file_label)
        
        # x截面文件标签
        self.x_section_label = QLabel("X截面文件: 未生成")
        self.x_section_label.setStyleSheet("background-color: #f8f9fa; padding: 8px; border-radius: 4px;")
        self.x_section_label.setWordWrap(True)
        results_layout.addWidget(self.x_section_label)
        
        # y截面文件标签
        self.y_section_label = QLabel("Y截面文件: 未生成")
        self.y_section_label.setStyleSheet("background-color: #f8f9fa; padding: 8px; border-radius: 4px;")
        self.y_section_label.setWordWrap(True)
        results_layout.addWidget(self.y_section_label)
        
        # 状态标签
        self.data_process_status = QLabel("准备就绪")
        self.data_process_status.setStyleSheet("color: #555; font-style: italic; padding: 5px;")
        self.data_process_status.setAlignment(Qt.AlignCenter)
        results_layout.addWidget(self.data_process_status)
        
        layout.addWidget(results_group)
        
        # 添加弹性空间
        layout.addStretch(1)
        
        return panel
    
    def create_file_selector(self, file_type, button_text, placeholder, layout):
        """创建文件选择部件"""
        container = QFrame()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(8)
        container_layout.setContentsMargins(0, 0, 0, 0)  # 无内边距
        
        # 标签
        title = QLabel(f"<b>{button_text.split(' ')[1]}文件</b>")
        title.setStyleSheet("font-size: 9.5pt; padding-bottom: 5px;")
        container_layout.addWidget(title)
        
        # 文件选择按钮
        select_btn = QPushButton(button_text)
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        select_btn.clicked.connect(lambda: self.select_raw_file(file_type))
        container_layout.addWidget(select_btn)
        
        # 文件路径显示
        if file_type == "initial":
            self.initial_label = QLabel(placeholder)
        else:
            self.after_label = QLabel(placeholder)
            
        file_label = self.initial_label if file_type == "initial" else self.after_label
        file_label.setStyleSheet("""
            QLabel {
                background-color: #f8f8f8;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px;
                font-size: 9pt;
                min-height: 50px;
            }
        """)
        file_label.setAutoFillBackground(True)
        file_label.setWordWrap(True)
        container_layout.addWidget(file_label)
        
        layout.addWidget(container)
    
    def select_raw_file(self, file_type):
        """选择crosstest的initial或after文件"""
        default_dir = get_resource_path("Data/inputs/CrossTrim_initial")
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"选择 {file_type.upper()} 文件", 
            str(default_dir), "CSV Files (*.csv)"
        )
        
        if file_path:
            if file_type == "initial":
                self.initial_file = file_path
                self.initial_label.setText(f"{Path(file_path).name}")
                self.data_process_status.setText("已选择初始文件")
            else:
                self.after_file = file_path
                self.after_label.setText(f"{Path(file_path).name}")
                self.data_process_status.setText("已选择扫描后文件")
    
    def process_raw_data(self):
        """处理原始数据"""
        if not self.initial_file:
            self.data_process_status.setText("请先选择初始膜厚文件")
            return
        if not self.after_file:
            self.data_process_status.setText("请先选择扫描后膜厚文件")
            return
            
        self.data_process_status.setText("正在处理数据...")
        
        # 创建并启动后台线程
        self.raw_data_thread = RawDataThread(
            self.initial_file, 
            self.after_file,
            self.data_processor_dir
        )
        
        # 连接信号
        self.raw_data_thread.finished.connect(self.on_raw_data_processed)
        self.raw_data_thread.log.connect(self.data_process_status.setText)
        
        self.raw_data_thread.start()
    
    def on_raw_data_processed(self, result):
        """原始数据处理完成后的回调"""
        trimming_path, x_section_path, y_section_path = result
        
        self.trimming_file_label.setText(f"刻蚀量文件: {Path(trimming_path).name}")
        self.x_section_label.setText(f"X截面文件: {Path(x_section_path).name}")
        self.y_section_label.setText(f"Y截面文件: {Path(y_section_path).name}")
        self.data_process_status.setText("原始数据处理成功完成!")
    
    # ============= 重构功能组件 (保持不变) =============
    def create_control_container(self):
        """创建重构控制台容器"""
        container = QFrame()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(12)
        
        # 创建控制面板
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel, 1)
        
        # 创建进度指示区域
        progress_frame = QFrame()
        progress_frame.setFrameShape(QFrame.StyledPanel)
        progress_frame.setStyleSheet("background-color: #ffffff; border-radius: 8px; padding: 10px;")
        
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(10, 10, 10, 10)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3498db;
                border-radius: 5px;
                text-align: center;
                height: 20px;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪。请选择X和Y轴截面文件")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 10))
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_frame, 1)
        
        return container
    
    def create_control_panel(self):
        """创建控制面板"""
        control_panel = QFrame()
        control_panel.setFrameShape(QFrame.StyledPanel)
        control_panel.setStyleSheet("background-color: #ffffff; border-radius: 8px;")
        
        panel_layout = QHBoxLayout(control_panel)
        panel_layout.setContentsMargins(15, 15, 15, 15)
        panel_layout.setSpacing(20)
        
        # ========= 左侧区域：文件选择 =========
        file_group = QGroupBox("数据输入")
        file_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        file_layout = QVBoxLayout(file_group)
        file_layout.setSpacing(10)
        
        # X轴文件选择
        x_layout = QHBoxLayout()
        self.x_btn = self.create_styled_button("选择 X 轴截面文件", "#4a86e8")
        self.x_btn.clicked.connect(lambda: self.select_file("x"))
        x_layout.addWidget(self.x_btn)
        
        self.x_label = QLabel("未选择文件")
        self.x_label.setStyleSheet("color: #555; font-style: italic; background-color: white; padding: 5px; border-radius: 4px;")
        self.x_label.setMinimumWidth(200)
        x_layout.addWidget(self.x_label)
        
        file_layout.addLayout(x_layout)
        
        # 添加间距
        file_layout.addSpacing(5)
        
        # Y轴文件选择
        y_layout = QHBoxLayout()
        self.y_btn = self.create_styled_button("选择 Y 轴截面文件", "#4a86e8")
        self.y_btn.clicked.connect(lambda: self.select_file("y"))
        y_layout.addWidget(self.y_btn)
        
        self.y_label = QLabel("未选择文件")
        self.y_label.setStyleSheet("color: #555; font-style: italic; background-color: white; padding: 5px; border-radius: 4px;")
        self.y_label.setMinimumWidth(200)
        y_layout.addWidget(self.y_label)
        
        file_layout.addLayout(y_layout)
        
        panel_layout.addWidget(file_group, 1)
        
        # ========= 右侧区域：操作按钮 =========
        action_group = QGroupBox("操作")
        action_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        action_layout = QVBoxLayout(action_group)
        action_layout.setSpacing(15)
        
        # 开始重构按钮
        self.run_btn = self.create_styled_button("开始重构", "#27ae60")
        self.run_btn.setFixedHeight(45)
        self.run_btn.clicked.connect(self.start_reconstruction)
        action_layout.addWidget(self.run_btn)
        
        # 导出结果按钮
        self.export_btn = self.create_styled_button("导出结果", "#3498db")
        self.export_btn.setFixedHeight(45)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_results)
        action_layout.addWidget(self.export_btn)
        
        panel_layout.addWidget(action_group, 1)
        
        return control_panel

    def create_styled_button(self, text, color):
        """创建带样式的按钮"""
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 6px;
                border: none;
                min-width: 120px;
            }}
            QPushButton:hover {{
                background-color: {self.darken_color(color)};
            }}
            QPushButton:disabled {{
                background-color: #bdc3c7;
                color: #7f8c8d;
            }}
        """)
        btn.setCursor(Qt.PointingHandCursor)
        return btn
        
    def darken_color(self, hex_color, factor=0.8):
        """使颜色变暗，用于悬停效果"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"
    
    def create_result_container(self):
        """创建结果展示容器"""
        container = QFrame()
        container.setStyleSheet("background-color: #ffffff; border-radius: 8px;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建选项卡区域
        self.create_tab_widget(layout)
        
        return container
        
    def create_tab_widget(self, layout):
        """创建选项卡区域"""
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { 
                border-top: 2px solid #3498db; 
                border-radius: 0 0 6px 6px; 
                background: white; 
            }
            QTabBar::tab {
                background: #f1f2f6; 
                padding: 8px 15px; 
                border: 1px solid #d8dde6; 
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px; 
                margin-right: 2px;
                color: #555;
                font-weight: bold;
            }
            QTabBar::tab:selected { 
                background: #3498db; 
                color: white; 
                border-bottom-color: #3498db;
            }
        """)
        
        # 创建标签页
        self.create_3d_profile_tab()
        self.create_error_analysis_tab()
        self.create_details_tab()
        
        layout.addWidget(self.tab_widget, 1)

    def create_3d_profile_tab(self):
        """创建3D光束轮廓标签页"""
        self.tab_3d = QWidget()
        layout = QVBoxLayout(self.tab_3d)
        layout.setSpacing(0)
        
        # 3D 光束轮廓图
        self.figure_3d = Figure(figsize=(6, 5))
        self.canvas_3d = FigureCanvas(self.figure_3d)
        self.ax_3d = self.figure_3d.add_subplot(111, projection='3d')
        
        # 添加占位提示
        self.ax_3d.text(0.5, 0.5, 0.5, "等待数据...", 
                         fontsize=12, ha='center', va='center',
                         bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        
        self.canvas_3d.setMinimumHeight(400)
        layout.addWidget(self.canvas_3d)
        
        self.tab_widget.addTab(self.tab_3d, "3D 光束轮廓")
    
    # 其他创建标签页的方法保持不变（create_error_analysis_tab, create_details_tab等）
    def create_error_analysis_tab(self):
        """创建误差分析标签页"""
        self.tab_error = QWidget()
        layout = QVBoxLayout(self.tab_error)
        layout.setSpacing(5)
        
        # 创建图表区域 (水平分割)
        error_layout = QHBoxLayout()
        error_layout.setSpacing(10)
        
        # X方向误差图容器
        x_container = QFrame()
        x_layout = QVBoxLayout(x_container)
        x_layout.setSpacing(5)
        x_layout.addWidget(QLabel("X方向误差分析", 
                                 alignment=Qt.AlignCenter | Qt.AlignVCenter,
                                 styleSheet="font-weight: bold; font-size: 10pt;"))
        
        self.figure_x_error = Figure(figsize=(6, 4))
        self.canvas_x_error = FigureCanvas(self.figure_x_error)
        self.canvas_x_error.setMinimumHeight(300)
        self.ax_x_error = self.figure_x_error.add_subplot(111)
        
        # 添加占位提示
        self.ax_x_error.text(0.5, 0.5, "等待分析数据...", 
                             fontsize=10, ha='center', va='center',
                             bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        
        x_layout.addWidget(self.canvas_x_error)
        error_layout.addWidget(x_container, 1)
        
        # Y方向误差图容器
        y_container = QFrame()
        y_layout = QVBoxLayout(y_container)
        y_layout.setSpacing(5)
        y_layout.addWidget(QLabel("Y方向误差分析", 
                                 alignment=Qt.AlignCenter | Qt.AlignVCenter,
                                 styleSheet="font-weight: bold; font-size: 10pt;"))
        
        self.figure_y_error = Figure(figsize=(6, 4))
        self.canvas_y_error = FigureCanvas(self.figure_y_error)
        self.canvas_y_error.setMinimumHeight(300)
        self.ax_y_error = self.figure_y_error.add_subplot(111)
        
        # 添加占位提示
        self.ax_y_error.text(0.5, 0.5, "等待分析数据...", 
                             fontsize=10, ha='center', va='center',
                             bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        
        y_layout.addWidget(self.canvas_y_error)
        error_layout.addWidget(y_container, 1)
        
        layout.addLayout(error_layout, 1)
        
        self.tab_widget.addTab(self.tab_error, "误差分析")
    
    def create_details_tab(self):
        """创建详细数据标签页"""
        self.tab_details = QWidget()
        layout = QVBoxLayout(self.tab_details)
        layout.setSpacing(10)
        
        # 上部区域：文件路径和统计信息
        top_layout = QHBoxLayout()
        
        # 左侧：文件路径信息
        file_container = QGroupBox("输出信息")
        file_layout = QVBoxLayout(file_container)
        file_layout.addWidget(QLabel("最终输出文件位置:", 
                                   styleSheet="font-weight: bold;"))
        self.final_file_label = QLabel("未生成")
        self.final_file_label.setWordWrap(True)
        self.final_file_label.setStyleSheet("color: #333; padding: 5px;")
        file_layout.addWidget(self.final_file_label)
        top_layout.addWidget(file_container, 2)
        
        # 右侧：统计信息
        stats_container = QGroupBox("误差统计")
        stats_layout = QVBoxLayout(stats_container)
        
        # 最大误差标签
        self.max_error_x = QLabel("X方向最大误差: ---")
        self.max_error_x.setStyleSheet("color: #C62828; font-weight: bold; padding: 3px;")
        stats_layout.addWidget(self.max_error_x)
        
        self.max_error_y = QLabel("Y方向最大误差: ---")
        self.max_error_y.setStyleSheet("color: #C62828; font-weight: bold; padding: 3px;")
        stats_layout.addWidget(self.max_error_y)
        
        # 平均误差标签
        self.avg_error_x = QLabel("X方向平均误差: ---")
        self.avg_error_x.setStyleSheet("padding: 3px;")
        stats_layout.addWidget(self.avg_error_x)
        
        self.avg_error_y = QLabel("Y方向平均误差: ---")
        self.avg_error_y.setStyleSheet("padding: 3px;")
        stats_layout.addWidget(self.avg_error_y)
        
        top_layout.addWidget(stats_container, 1)
        
        layout.addLayout(top_layout)
        
        # 目标剖面与实际剖面图表
        profile_container = QGroupBox("剖面对比")
        profile_layout = QVBoxLayout(profile_container)
        charts_layout = QHBoxLayout()
        
        # 目标剖面图
        figure_label_container = QVBoxLayout()
        figure_label_container.addWidget(QLabel("目标剖面", alignment=Qt.AlignCenter | Qt.AlignBottom))
        self.figure_target = Figure(figsize=(5, 4))
        self.canvas_target = FigureCanvas(self.figure_target)
        self.canvas_target.setMinimumHeight(250)
        self.ax_target = self.figure_target.add_subplot(111)
        
        # 添加占位提示
        self.ax_target.text(0.5, 0.5, "等待数据...", 
                            fontsize=10, ha='center', va='center',
                            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        
        figure_label_container.addWidget(self.canvas_target)
        charts_layout.addLayout(figure_label_container, 1)
        
        # 重建剖面图
        figure_label_container = QVBoxLayout()
        figure_label_container.addWidget(QLabel("重建剖面", alignment=Qt.AlignCenter | Qt.AlignBottom))
        self.figure_reconstructed = Figure(figsize=(5, 4))
        self.canvas_reconstructed = FigureCanvas(self.figure_reconstructed)
        self.canvas_reconstructed.setMinimumHeight(250)
        self.ax_reconstructed = self.figure_reconstructed.add_subplot(111)
        
        # 添加占位提示
        self.ax_reconstructed.text(0.5, 0.5, "等待数据...", 
                                   fontsize=10, ha='center', va='center',
                                   bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        
        figure_label_container.addWidget(self.canvas_reconstructed)
        charts_layout.addLayout(figure_label_container, 1)
        
        profile_layout.addLayout(charts_layout)
        layout.addWidget(profile_container, 1)
        
        self.tab_widget.addTab(self.tab_details, "详细数据")

    def clear_all_charts(self):
        """清除所有图表上的数据"""
        # 3D图表
        self.figure_3d.clear()
        self.ax_3d = self.figure_3d.add_subplot(111, projection='3d')
        self.ax_3d.text(0.5, 0.5, 0.5, "重构中...", 
                         fontsize=12, ha='center', va='center',
                         bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        
        # 误差图表
        self.figure_x_error.clear()
        self.ax_x_error = self.figure_x_error.add_subplot(111)
        self.ax_x_error.text(0.5, 0.5, "等待分析数据...", 
                             fontsize=10, ha='center', va='center',
                             bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
                             
        self.figure_y_error.clear()
        self.ax_y_error = self.figure_y_error.add_subplot(111)
        self.ax_y_error.text(0.5, 0.5, "等待分析数据...", 
                             fontsize=10, ha='center', va='center',
                             bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        
        # 详细数据图表
        self.figure_target.clear()
        self.ax_target = self.figure_target.add_subplot(111)
        self.ax_target.text(0.5, 0.5, "等待数据...", 
                             fontsize=10, ha='center', va='center',
                             bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        
        self.figure_reconstructed.clear()
        self.ax_reconstructed = self.figure_reconstructed.add_subplot(111)
        self.ax_reconstructed.text(0.5, 0.5, "等待数据...", 
                             fontsize=10, ha='center', va='center',
                             bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        
        # 更新画布
        self.canvas_3d.draw()
        self.canvas_x_error.draw()
        self.canvas_y_error.draw()
        self.canvas_target.draw()
        self.canvas_reconstructed.draw()

    def select_file(self, axis):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"选择 {axis.upper()} 轴截面文件", 
            "", "CSV Files (*.csv)"
        )
        
        if file_path:
            if axis == "x":
                self.x_file = file_path
                self.x_label.setText(f"已选: {Path(file_path).name}")
            else:
                self.y_file = file_path
                self.y_label.setText(f"已选: {Path(file_path).name}")
            
            # 如果两个文件都已选择，更新状态
            if self.x_file and self.y_file:
                self.status_label.setText("已选择X和Y轴文件，点击'开始重构'按钮启动计算")

    def start_reconstruction(self):
        if not self.x_file:
            self.status_label.setText("请先选择X轴截面文件")
            return
        if not self.y_file:
            self.status_label.setText("请选择Y轴截面文件")
            return
            
        self.progress_bar.setValue(0)
        self.status_label.setText("重构进行中...")
        self.run_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        
        # 清理现有图表
        self.clear_all_charts()
        
        # 创建并启动后台线程
        self.reconstruction_thread = ReconstructionThread(
            self.x_file, self.y_file, self.output_dir
        )
        
        # 连接信号
        self.reconstruction_thread.finished.connect(self.on_reconstruction_finished)
        self.reconstruction_thread.log.connect(self.status_label.setText)
        self.reconstruction_thread.update_progress.connect(self.progress_bar.setValue)
        
        self.reconstruction_thread.start()
    
    def on_reconstruction_finished(self, result):
        self.result = result
        self.run_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_label.setText("重构完成! 结果可在各标签页查看")
        self.plot_results()
        self.update_details()

    def export_results(self):
        if not self.result:
            return
            
        # 提示用户导出位置
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出结果", 
            str(Path(self.result["final_file"]).with_suffix('')), 
            "PNG Files (*.png)"
        )
        
        if file_path:
            # 保存3D轮廓图
            self.figure_3d.savefig(file_path, dpi=300)
            
            # 保存误差图
            error_file_path = file_path.replace('.png', '_errors.png')
            
            # 创建组合误差图
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 10), dpi=100)
            self.plot_x_error(ax1)
            self.plot_y_error(ax2)
            fig.tight_layout()
            fig.savefig(error_file_path)
            
            self.status_label.setText(f"结果已导出到: {Path(file_path).name} 和 {Path(error_file_path).name}")
            plt.close(fig)

    # 以下绘图方法保持不变...
    def plot_results(self):
        if not self.result:
            return
            
        self.plot_3d_profile()
        self.plot_x_error()
        self.plot_y_error()
        self.plot_profile_comparison()
        
        # 更新所有画布
        self.canvas_3d.draw()
        self.canvas_x_error.draw()
        self.canvas_y_error.draw()
        self.canvas_target.draw()
        self.canvas_reconstructed.draw()

    def update_details(self):
        if not self.result:
            return
        
        # 更新文件路径
        self.final_file_label.setText(str(Path(self.result['final_file'])))
        
        # 计算误差统计
        diff_x = self.result['diff_x']
        diff_y = self.result['diff_y']
        
        max_err_x = np.max(np.abs(diff_x))
        max_err_y = np.max(np.abs(diff_y))
        
        avg_err_x = np.mean(np.abs(diff_x))
        avg_err_y = np.mean(np.abs(diff_y))
        
        # 更新标签
        self.max_error_x.setText(f"X方向最大误差: {max_err_x:.5f}")
        self.max_error_y.setText(f"Y方向最大误差: {max_err_y:.5f}")
        
        self.avg_error_x.setText(f"X方向平均误差: {avg_err_x:.5f}")
        self.avg_error_y.setText(f"Y方向平均误差: {avg_err_y:.5f}")

    def plot_3d_profile(self):
        self.figure_3d.clear()
        beam_profile = self.result['beam_profile']
        
        # 创建3D子图
        ax = self.figure_3d.add_subplot(111, projection='3d')
        
        # 创建X和Y坐标网格
        x = np.arange(beam_profile.shape[1])
        y = np.arange(beam_profile.shape[0])
        X, Y = np.meshgrid(x, y)
        
        # 绘制表面图
        surf = ax.plot_surface(
            X, Y, beam_profile, 
            cmap='viridis', 
            edgecolor='none',
            alpha=0.85,
            rstride=1, 
            cstride=1
        )
        
        # 添加颜色条
        self.figure_3d.colorbar(surf, ax=ax, shrink=0.5, aspect=10, pad=0.1)
        
        # 设置标签和标题
        ax.set_title('重构离子束3D强度分布', fontsize=12)
        ax.set_xlabel('X 位置', fontsize=10)
        ax.set_ylabel('Y 位置', fontsize=10)
        ax.set_zlabel('强度 (a.u.)', fontsize=10)
        
        # 设置视角
        ax.view_init(elev=30, azim=45)
        
        # 移除背景线
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor('white')
        ax.yaxis.pane.set_edgecolor('white')
        ax.zaxis.pane.set_edgecolor('white')
        
        self.figure_3d.tight_layout()

    def plot_x_error(self, ax=None):
        """绘制X方向的误差分析"""
        if not ax:
            ax = self.figure_x_error.add_subplot(111) if not hasattr(self, 'ax_x_error') else self.ax_x_error
            self.figure_x_error.clear()
            ax = self.figure_x_error.add_subplot(111)
        
        # 获取结果数据
        x_calculated = self.result['conv_y']  # X方向的计算值
        x_experimental = self.result['x_profile']  # X方向的实验值
        x_error = self.result['diff_x']  # X方向误差
        
        # 计算最大误差绝对值和位置
        max_error_idx = np.argmax(np.abs(x_error))
        max_error_value = x_error[max_error_idx]
        
        # 绘制实验值和计算值
        positions = np.arange(len(x_experimental))
        marker_size = 5 if len(x_experimental) >= 15 else 8
        
        # 绘制实际值
        ax.plot(positions, x_experimental, 'b-', label='X实际值', linewidth=2, alpha=0.7)
        # 绘制计算值
        ax.plot(positions, x_calculated, 'r--', label='X计算值', linewidth=2, alpha=0.8)
        
        # 填充误差区域
        ax.fill_between(
            positions, 
            x_calculated - np.abs(x_error), 
            x_calculated + np.abs(x_error), 
            color='g', 
            alpha=0.2, 
            label='误差范围'
        )
        
        # 标记最大误差点
        ax.plot(
            positions[max_error_idx], 
            x_experimental[max_error_idx], 
            'yo', 
            markersize=8,
            markeredgecolor='k',
            label=f'最大误差点 ({max_error_value:.4f})'
        )
        
        # 设置标题和标签
        ax.set_title('X方向误差分析', fontsize=10)
        ax.set_xlabel('位置索引', fontsize=9)
        ax.set_ylabel('强度 (a.u.)', fontsize=9)
        
        # 添加网格和图例
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend(fontsize=8, loc='best')
        
        self.figure_x_error.tight_layout()

    def plot_y_error(self, ax=None):
        """绘制Y方向的误差分析"""
        if not ax:
            ax = self.figure_y_error.add_subplot(111) if not hasattr(self, 'ax_y_error') else self.ax_y_error
            self.figure_y_error.clear()
            ax = self.figure_y_error.add_subplot(111)
        
        # 获取结果数据
        y_calculated = self.result['row_sums']  # Y方向的计算值
        y_experimental = self.result['y_profile']  # Y方向的实验值
        y_error = self.result['diff_y']  # Y方向误差
        
        # 计算最大误差绝对值和位置
        max_error_idx = np.argmax(np.abs(y_error))
        max_error_value = y_error[max_error_idx]
        
        # 绘制实验值和计算值
        positions = np.arange(len(y_experimental))
        marker_size = 5 if len(y_experimental) >= 15 else 8
        
        # 绘制实际值
        ax.plot(positions, y_experimental, 'b-', label='Y实际值', linewidth=2, alpha=0.7)
        # 绘制计算值
        ax.plot(positions, y_calculated, 'r--', label='Y计算值', linewidth=2, alpha=0.8)
        
        # 填充误差区域
        ax.fill_between(
            positions, 
            y_calculated - np.abs(y_error), 
            y_calculated + np.abs(y_error), 
            color='g', 
            alpha=0.2, 
            label='误差范围'
        )
        
        # 标记最大误差点
        ax.plot(
            positions[max_error_idx], 
            y_experimental[max_error_idx], 
            'yo', 
            markersize=8,
            markeredgecolor='k',
            label=f'最大误差点 ({max_error_value:.4f})'
        )
        
        # 设置标题和标签
        ax.set_title('Y方向误差分析', fontsize=10)
        ax.set_xlabel('位置索引', fontsize=9)
        ax.set_ylabel('强度 (a.u.)', fontsize=9)
        
        # 添加网格和图例
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend(fontsize=8, loc='best')
        
        self.figure_y_error.tight_layout()
    
    def plot_profile_comparison(self):
        """绘制目标剖面与实际剖面的对比图"""
        if not self.result:
            return
        
        # 绘制目标剖面图
        self.figure_target.clear()
        ax = self.figure_target.add_subplot(111)
        ax.clear()
        
        # X方向
        positions_x = np.linspace(-15, 15, len(self.result['x_profile']))
        ax.plot(positions_x, self.result['x_profile'], 'b-', label='X实际值', linewidth=2)
        
        # Y方向
        positions_y = np.linspace(-15, 15, len(self.result['y_profile']))
        ax.plot(positions_y, self.result['y_profile'], 'g-', label='Y实际值', linewidth=2)
        
        ax.set_title('目标剖面图', fontsize=10)
        ax.set_xlabel('位置 (mm)', fontsize=9)
        ax.set_ylabel('强度 (a.u.)', fontsize=9)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend(fontsize=8)
        self.figure_target.tight_layout()
        
        # 绘制重建剖面图
        self.figure_reconstructed.clear()
        ax = self.figure_reconstructed.add_subplot(111)
        ax.clear()
        
        # 取中间行和中间列
        center_y = self.result['beam_profile'][15, :]
        center_x = self.result['beam_profile'][:, 15]
        
        # X重建剖面
        ax.plot(positions_x, center_x, 'r--', label='X重建剖面', linewidth=2)
        
        # Y重建剖面
        ax.plot(positions_y, center_y, 'm--', label='Y重建剖面', linewidth=2)
        
        ax.set_title('重建剖面图', fontsize=10)
        ax.set_xlabel('位置 (mm)', fontsize=9)
        ax.set_ylabel('强度 (a.u.)', fontsize=9)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend(fontsize=8)
        self.figure_reconstructed.tight_layout()
