from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
    QGroupBox, QPushButton, QLabel, QFileDialog, 
    QFormLayout, QMessageBox, QSizePolicy, QLineEdit,
    QDoubleSpinBox, QCheckBox
)
from PyQt5.QtCore import Qt
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Qt5Agg')
import numpy as np
import os
import csv

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)
from mpl_toolkits.mplot3d import Axes3D
import logging

from core.beam_spot_test import BeamSpotTestProcessor
from utils.file_io import get_resource_path

logger = logging.getLogger('UI.BeamSpot')

class BeamSpotTestUI(QWidget):
    def __init__(self):
        super().__init__()
        self.processor = BeamSpotTestProcessor()
        self.file_path = ""
        self.contour_figure = None
        self.cross_section_figure = None
        self.model_figure = None
        self.grid_data = None
        self.thk_min = 0.0
        self.thk_max = 0.0
        self._setup_ui()
        self._create_plots()
    
    def _setup_ui(self):
        """设置UI布局 - 上部画布，下部工具栏"""
        # 主垂直布局
        main_layout = QVBoxLayout()
        
        # === 上部区域 - 结果可视化 ===
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(5, 5, 5, 5)
        
        # 使用水平分割器分隔三个画布区域
        canvas_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧 - 等高线图 (35%)
        contour_group = QGroupBox("蚀刻能力等高线图")
        contour_layout = QVBoxLayout()
        contour_layout.setContentsMargins(5, 5, 5, 5)
        
        self.contour_figure = Figure(figsize=(6, 4.5), tight_layout=True)
        self.contour_canvas = FigureCanvas(self.contour_figure)
        self.contour_toolbar = NavigationToolbar(self.contour_canvas, self)
        
        contour_layout.addWidget(self.contour_toolbar)
        contour_layout.addWidget(self.contour_canvas)
        contour_group.setLayout(contour_layout)
        
        # 中间 - X/Y轴截面图 (30%)
        cross_section_group = QGroupBox("蚀刻能力截面分析")
        cross_section_layout = QVBoxLayout()
        cross_section_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建新的图形用于显示截面曲线
        self.cross_section_figure = Figure(figsize=(5, 6), tight_layout=True)
        self.cross_section_canvas = FigureCanvas(self.cross_section_figure)
        
        # 不需要导航工具栏，因为这部分只是展示
        cross_section_layout.addWidget(self.cross_section_canvas)
        cross_section_group.setLayout(cross_section_layout)
        
        # 右侧 - 3D模型 (35%)
        model_group = QGroupBox("蚀刻能力3D模型")
        model_layout = QVBoxLayout()
        model_layout.setContentsMargins(5, 5, 5, 5)
        
        self.model_figure = Figure(figsize=(6, 4.5), tight_layout=True)
        self.model_figure.add_subplot(111, projection='3d')
        self.model_canvas = FigureCanvas(self.model_figure)
        self.model_toolbar = NavigationToolbar(self.model_canvas, self)
        
        model_layout.addWidget(self.model_toolbar)
        model_layout.addWidget(self.model_canvas)
        model_group.setLayout(model_layout)
        
        # 添加到分割器，设置比例 35:30:35
        canvas_splitter.addWidget(contour_group)
        canvas_splitter.addWidget(cross_section_group)
        canvas_splitter.addWidget(model_group)
        canvas_splitter.setSizes([350, 300, 350])  # 设置初始宽度比例
        
        top_layout.addWidget(canvas_splitter)
        
        # === 下部区域 - 控制面板 ===
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(5, 5, 5, 5)
        
        # 文件操作部分 (左侧)
        file_group = QGroupBox("膜厚数据选择")
        file_layout = QFormLayout()
        file_group.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        
        self.file_label = QLabel("未选择文件")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("min-width: 300px;")
        select_button = QPushButton("选择CSV文件")
        select_button.clicked.connect(self._select_file)
        
        file_layout.addRow("文件位置:", self.file_label)
        file_layout.addRow("", select_button)
        
        process_button = QPushButton("处理数据")
        process_button.setObjectName("processButton")
        process_button.setStyleSheet(
            "QPushButton#processButton {"
            "   background-color: #4CAF50;"
            "   color: white;"
            "   font-weight: bold;"
            "   padding: 10px;"
            "   border-radius: 5px;"
            "}"
        )
        process_button.clicked.connect(self._process_data)
        file_layout.addRow("", process_button)
        
        file_group.setLayout(file_layout)
        
        # 工具部分 (中间)
        export_group = QGroupBox("插值结果控制")
        export_layout = QVBoxLayout()
        
        # 创建目标有效半径控制区域
        radius_control_layout = QHBoxLayout()
        
        # 添加勾选框 - 启用编辑
        self.enable_radius_edit = QCheckBox("启用编辑")
        self.enable_radius_edit.setChecked(False)  # 初始不勾选
        self.enable_radius_edit.stateChanged.connect(self._toggle_radius_edit)
        
        # 目标有效半径标签
        radius_label = QLabel("目标有效半径 (mm):")
        
        # 将勾选框和标签添加到水平布局
        radius_control_layout.addWidget(self.enable_radius_edit)
        radius_control_layout.addWidget(radius_label)
        
        # 添加到垂直布局
        export_layout.addLayout(radius_control_layout)
        
        # 有效半径输入框
        self.radius_input = QDoubleSpinBox()
        self.radius_input.setDecimals(2)  # 设置两位小数
        self.radius_input.setMinimum(0)  # 最小值为0
        self.radius_input.setMaximum(100)  # 设置一个合理的最大值
        self.radius_input.setValue(10.00)  # 设置默认值为10.00mm
        self.radius_input.setEnabled(False)  # 初始不可编辑
        
        export_layout.addWidget(self.radius_input)
        
        # 导出按钮
        self.export_btn = QPushButton("导出CSV文件")
        self.export_btn.setObjectName("exportButton")
        self.export_btn.setStyleSheet(
            "QPushButton#exportButton {"
            "   background-color: #2196F3;"
            "   color: white;"
            "   font-weight: bold;"
            "   padding: 10px;"
            "   border-radius: 5px;"
            "}"
        )
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export_interpolated_data)
        
        self.export_status = QLabel("数据未处理")
        self.export_status.setAlignment(Qt.AlignCenter)
        
        export_layout.addWidget(self.export_btn)
        export_layout.addWidget(self.export_status)
        export_layout.addStretch()
        export_group.setLayout(export_layout)
        
        # 结果显示部分 (右侧)
        result_group = QGroupBox("蚀刻能力分析结果")
        result_layout = QFormLayout()
        
        # 中心点信息
        center_label = QLabel("中心点信息:")
        center_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        result_layout.addRow(center_label)
        
        self.center_org_label = QLabel("未计算")
        result_layout.addRow("原始中心:", self.center_org_label)
        
        self.center_max_label = QLabel("未计算")
        result_layout.addRow("最大值位置:", self.center_max_label)
        
        self.center_offset_label = QLabel("未计算")
        result_layout.addRow("偏移量:", self.center_offset_label)
        
        # 分隔线
        separator = QLabel("")
        separator.setFrameStyle(QLabel.HLine)
        result_layout.addRow(separator)
        
        # 测量结果
        result_label = QLabel("测量结果:")
        result_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        result_layout.addRow(result_label)
        
        self.bg_thickness_label = QLabel("未计算")
        result_layout.addRow("背景厚度 (nm):", self.bg_thickness_label)
        
        self.peak_label = QLabel("未计算")
        result_layout.addRow("峰值强度 (nm):", self.peak_label)
        
        self.actual_radius_label = QLabel("未计算")  # 新增：实际有效半径
        result_layout.addRow("实际有效半径 (mm):", self.actual_radius_label)
        
        result_group.setLayout(result_layout)
        result_group.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        
        # 添加到下方布局
        bottom_layout.addWidget(file_group, 20)  # 20%空间
        bottom_layout.addWidget(export_group, 40)  # 40%空间
        bottom_layout.addWidget(result_group, 40)  # 40%空间
        
        # 添加到主布局
        main_layout.addWidget(top_widget, 80)  # 80%空间给画布
        main_layout.addWidget(bottom_widget, 20)  # 20%空间给控制面板
        
        self.setLayout(main_layout)
    
    def _toggle_radius_edit(self, state):
        """勾选框状态改变时的回调"""
        if state == 2:  # Qt.Checked 值为 2
            self.radius_input.setEnabled(True)
            logger.info("启用目标半径编辑")
        else:
            self.radius_input.setEnabled(False)
            logger.info("禁用目标半径编辑")
    
    def _create_plots(self):
        """创建空图表"""
        # 等高线图
        self.contour_figure.clear()
        ax1 = self.contour_figure.add_subplot(111)
        ax1.set_title("蚀刻能力等高线图")
        ax1.set_xlabel("X (mm)")
        ax1.set_ylabel("Y (mm)")
        ax1.text(0.5, 0.5, "请加载数据后点击'处理数据'", 
                ha='center', va='center', fontsize=12)
        ax1.set_axis_off()
        self.contour_figure.tight_layout()
        self.contour_canvas.draw()
        
        # 3D模型
        self.model_figure.clear()
        self.model_figure.add_subplot(111, projection='3d')
        ax2 = self.model_figure.get_axes()[0]
        ax2.set_title("蚀刻能力3D模型")
        ax2.set_xlabel("X (mm)")
        ax2.set_ylabel("Y (mm)")
        ax2.set_zlabel("蚀刻能力 (nm)")
        self.model_figure.tight_layout()
        self.model_canvas.draw()
        
        # 截面曲线图
        self.cross_section_figure.clear()
        self._create_empty_cross_section_plots()
        self.cross_section_canvas.draw()
    
    def _create_empty_cross_section_plots(self):
        """为截面图创建空图表"""
        # 清除之前的图形
        self.cross_section_figure.clear()
        
        # 创建上下两个子图
        ax_x = self.cross_section_figure.add_subplot(211)  # 上部分为X截面
        ax_y = self.cross_section_figure.add_subplot(212)  # 下部分为Y截面
        
        # X截面
        ax_x.set_title("X轴截面曲线 (Y=0)")
        ax_x.set_xlabel("X位置 (mm)")
        ax_x.set_ylabel("蚀刻能力 (nm)")
        ax_x.text(0.5, 0.5, "无数据", 
                 ha='center', va='center', fontsize=12)
        ax_x.set_xlim(-15, 15)
        ax_x.set_ylim(0, 1)
        ax_x.grid(True)
        
        # Y截面
        ax_y.set_title("Y轴截面曲线 (X=0)")
        ax_y.set_xlabel("Y位置 (mm)")
        ax_y.set_ylabel("蚀刻能力 (nm)")
        ax_y.text(0.5, 0.5, "无数据", 
                 ha='center', va='center', fontsize=12)
        ax_y.set_xlim(-15, 15)
        ax_y.set_ylim(0, 1)
        ax_y.grid(True)
        
        self.cross_section_figure.tight_layout()
    
    def _select_file(self):
        """选择CSV文件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择膜厚数据文件", 
            str(get_resource_path("Data/inputs")),
            "CSV Files (*.csv)",
            options=options
        )
        
        if file_path:
            try:
                # 简短显示路径，保留文件名
                path_parts = file_path.split('/')
                display_path = file_path if len(path_parts) <= 2 else f".../{path_parts[-2]}/{path_parts[-1]}"
                self.file_label.setText(display_path)
                self.file_path = file_path
                self.file_label.setToolTip(file_path)
                
                # 禁用导出按钮
                self.export_btn.setEnabled(False)
                
                # 重置目标半径相关控件
                self.enable_radius_edit.setChecked(False)  # 关闭勾选
                self.radius_input.setEnabled(False)        # 禁用输入
                self.radius_input.setValue(10.00)          # 重置为10.00mm
                
                # 重置状态文本
                self.export_status.setText("数据未处理")
                
                # 创建空图表
                self._create_plots()
                
            except:
                self.file_label.setText(file_path)
                self.file_path = file_path
                self.file_label.setToolTip(file_path)
    
    def _process_data(self):
        """处理选择的膜厚数据"""
        if not self.file_path:
            QMessageBox.warning(self, "警告", "请先选择CSV文件")
            return
        
        try:
            # 显示加载中状态
            self.contour_figure.clear()
            self.contour_figure.text(0.5, 0.5, "数据处理中...", 
                                    ha='center', va='center', fontsize=16)
            self.contour_canvas.draw()
            
            # 读取目标有效半径值
            target_radius = self.radius_input.value()  # 总是使用当前值
            logger.info(f"使用目标有效半径: {target_radius:.2f} mm")
            
            # 处理数据
            contour_data, surface_data = self.processor.load_and_process(
                self.file_path, target_radius
            )
            
            # 保存网格数据用于导出
            self.grid_data = contour_data['grid_z']
            
            # 获取厚度范围
            max_thk = self.processor.thk_max
            min_thk = self.processor.thk_min
            
            # 设置有效半径输入范围 [0, 初始半径*1.5]
            radius_max = self.processor.radius * 1.5
            if radius_max < 1:
                radius_max = 15.0
            self.radius_input.setRange(0, radius_max)
            
            # 显示分析结果
            org_center_x, org_center_y = self.processor.original_center
            self.center_org_label.setText(f"({org_center_x:.2f}, {org_center_y:.2f})")
            
            max_x, max_y = self.processor.max_etching_position
            self.center_max_label.setText(f"({max_x:.2f}, {max_y:.2f})")
            
            # 计算中心点偏移量
            x_offset = max_x - org_center_x
            y_offset = max_y - org_center_y
            self.center_offset_label.setText(f"X: {x_offset:.2f}mm, Y: {y_offset:.2f}mm")
            
            # 计算插值后的峰值强度
            grid_z = contour_data['grid_z']
            peak_value = np.max(grid_z)
            self.peak_label.setText(f"{peak_value:.2f} nm")
            
            # 显示背景厚度和实际有效半径
            self.bg_thickness_label.setText(f"{self.processor.background_thickness:.2f} nm")
            self.actual_radius_label.setText(f"{self.processor.radius:.2f} mm")
            
            # 更新所有图表
            self._plot_contour(contour_data)
            self._plot_surface(surface_data)
            self._plot_cross_sections(contour_data)  # 新增：绘制截面曲线
            
            # 启用导出按钮
            self.export_btn.setEnabled(True)
            self.export_status.setText("数据就绪可导出")
            
        except Exception as e:
            logger.exception("处理数据失败")
            QMessageBox.critical(self, "错误", f"处理数据时出错:\n{str(e)}")
            self._create_plots()  # 恢复初始状态
            self.export_btn.setEnabled(False)
            self.radius_input.setEnabled(False)
            self.export_status.setText("数据未处理")
    
    def _plot_cross_sections(self, contour_data):
        """绘制X轴和Y轴截面曲线"""
        grid_x = contour_data['grid_x']
        grid_y = contour_data['grid_y']
        grid_z = contour_data['grid_z']
        
        # 清除之前的图形
        self.cross_section_figure.clear()
        
        # 创建上下两个子图
        ax_x = self.cross_section_figure.add_subplot(211)  # 上部分为X截面
        ax_y = self.cross_section_figure.add_subplot(212)  # 下部分为Y截面
        
        ########################################################################
        # 修复1: 正确提取Y=0时的X轴截面数据 (X坐标和蚀刻能力)
        # 找到最接近Y=0的索引位置
        y0_indices = np.where(np.abs(grid_y) < 0.01)  # 使用容差0.01mm
        
        if len(y0_indices[0]) > 0:
            # 提取Y=0附近的所有点数据
            x_section = grid_x[y0_indices]
            z_section = grid_z[y0_indices]
            
            # 为了绘制平滑曲线，按X坐标排序
            sorted_indices = np.argsort(x_section)
            x_section = x_section[sorted_indices]
            z_section = z_section[sorted_indices]
            
            # 绘制X轴截面曲线
            ax_x.plot(x_section, z_section, 'b-', linewidth=2)
        else:
            logger.warning("未找到Y=0的截面数据")
            ax_x.text(0.5, 0.5, "未找到Y=0截面数据", ha='center', va='center')
        ########################################################################
        
        ax_x.set_title("X轴截面曲线 (Y=0)")
        ax_x.set_xlabel("X位置 (mm)")
        ax_x.set_ylabel("蚀刻能力 (nm)")
        ax_x.set_xlim(-15, 15)
        ax_x.grid(True)
        
        # 标记有效半径
        if self.processor.radius > 0:
            # 左边有效半径点
            ax_x.axvline(x=-self.processor.radius, color='r', linestyle='--', alpha=0.7)
            # 右边有效半径点
            ax_x.axvline(x=self.processor.radius, color='r', linestyle='--', alpha=0.7, 
                        label=f'有效半径: ±{self.processor.radius:.2f}mm')
            ax_x.legend(loc='best')
        
        ########################################################################
        # 修复2: 正确提取X=0时的Y轴截面数据 (Y坐标和蚀刻能力)
        # 找到最接近X=0的索引位置
        x0_indices = np.where(np.abs(grid_x) < 0.01)  # 使用容差0.01mm
        
        if len(x0_indices[0]) > 0:
            # 提取X=0附近的所有点数据
            y_section = grid_y[x0_indices]
            z_section = grid_z[x0_indices]
            
            # 为了绘制平滑曲线，按Y坐标排序
            sorted_indices = np.argsort(y_section)
            y_section = y_section[sorted_indices]
            z_section = z_section[sorted_indices]
            
            # 绘制Y轴截面曲线
            ax_y.plot(y_section, z_section, 'g-', linewidth=2)
        else:
            logger.warning("未找到X=0的截面数据")
            ax_y.text(0.5, 0.5, "未找到X=0截面数据", ha='center', va='center')
        ########################################################################
        
        ax_y.set_title("Y轴截面曲线 (X=0)")
        ax_y.set_xlabel("Y位置 (mm)")
        ax_y.set_ylabel("蚀刻能力 (nm)")
        ax_y.set_xlim(-15, 15)
        ax_y.grid(True)
        
        # 标记有效半径
        if self.processor.radius > 0:
            # 上边有效半径点
            ax_y.axvline(x=self.processor.radius, color='r', linestyle='--', alpha=0.7)
            # 下边有效半径点
            ax_y.axvline(x=-self.processor.radius, color='r', linestyle='--', alpha=0.7,
                        label=f'有效半径: ±{self.processor.radius:.2f}mm')
            ax_y.legend(loc='best')
        
        # 调整布局
        self.cross_section_figure.tight_layout()
        self.cross_section_canvas.draw()

    
    def _plot_contour(self, data):
        """绘制等高线图，范围从-15mm到+15mm"""
        grid_x = data['grid_x']
        grid_y = data['grid_y']
        grid_z = data['grid_z']
        
        # 清除旧图
        self.contour_figure.clear()
        ax = self.contour_figure.add_subplot(111)
        
        # 绘制等高线
        peak_value = np.max(grid_z)
        levels = np.linspace(0, peak_value, 20) if peak_value > 0 else np.linspace(0, 1, 20)
            
        contour = ax.contourf(
            grid_x, grid_y, grid_z, 
            levels=levels, cmap='viridis'
        )
        
        # 添加颜色条
        cbar = self.contour_figure.colorbar(contour, ax=ax)
        cbar.set_label('蚀刻能力 (nm)')
        
        # 标记中心点
        ax.scatter([0], [0], s=100, c='red', marker='o', edgecolors='white', label='中心点')
        
        # 添加蚀刻能力有效半径线
        if self.processor.radius > 0:
            circle = plt.Circle(
                (0, 0), 
                self.processor.radius, 
                color='white', 
                linestyle='--', 
                fill=False, 
                linewidth=1.5,
                label=f'有效半径: {self.processor.radius:.2f}mm'
            )
            ax.add_patch(circle)
        
        # 标记峰值位置
        peak_idx = np.unravel_index(np.argmax(grid_z), grid_z.shape)
        peak_x = grid_x[peak_idx]
        peak_y = grid_y[peak_idx]
        
        if abs(peak_x) > 0.5 or abs(peak_y) > 0.5:
            ax.scatter([peak_x], [peak_y], s=100, c='blue', marker='*', 
                      edgecolors='white', label=f'峰值位置: ({peak_x:.1f}, {peak_y:.1f})')
        
        # 设置图表属性
        ax.set_title("蚀刻能力等高线图")
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        ax.set_aspect('equal')
        ax.legend(loc='upper right')
        
        # 设置绘图范围
        ax.set_xlim(-15, 15)
        ax.set_ylim(-15, 15)
        ax.grid(True, linestyle='--', alpha=0.7)
        self.contour_figure.tight_layout()
        
        # 重绘画布
        self.contour_canvas.draw()

    def _plot_surface(self, data):
        """绘制3D表面图，范围从-15mm到+15mm"""
        x = data['x_flat']
        y = data['y_flat']
        z = data['z_flat']
        grid_shape = data['grid_shape']
        grid_z = z.reshape(grid_shape)
        
        # 计算峰值强度
        peak_value = np.max(grid_z)
        
        # 创建3D网格
        X = x.reshape(grid_shape)
        Y = y.reshape(grid_shape)
        Z = z.reshape(grid_shape)
        
        # 清除旧图
        self.model_figure.clear()
        ax = self.model_figure.add_subplot(111, projection='3d')
        
        # 绘制3D表面
        surf = ax.plot_surface(
            X, Y, Z, 
            cmap='viridis',
            edgecolor='none',
            rstride=3, 
            cstride=3,
            alpha=0.8,
            vmin=0,
            vmax=peak_value
        )
        
        # 添加中心点标记
        ax.scatter([0], [0], [peak_value*1.1], s=100, c='red', marker='o', 
                  edgecolors='white', label='中心点')
        
        # 添加蚀刻能力有效半径线（在平面上）
        if self.processor.radius > 0:
            theta = np.linspace(0, 2 * np.pi, 100)
            x_circle = self.processor.radius * np.cos(theta)
            y_circle = self.processor.radius * np.sin(theta)
            z_circle = np.zeros_like(x_circle) + 0.01
            
            use_label = True
            for x_val, y_val in zip(x_circle, y_circle):
                if abs(x_val) > 15 or abs(y_val) > 15:
                    use_label = False
                    break
            
            if use_label:
                ax.plot(x_circle, y_circle, z_circle, 'w--', linewidth=2, 
                       label=f'有效半径: {self.processor.radius:.2f}mm')
        
        # 设置图表属性
        ax.set_title("蚀刻能力3D模型")
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        ax.set_zlabel("蚀刻能力 (nm)")
        ax.legend(loc='upper right')
        
        # 设置坐标轴范围
        ax.set_xlim3d(-15, 15)
        ax.set_ylim3d(-15, 15)
        ax.set_zlim(0, np.max(Z) * 1.25)
        ax.view_init(elev=30, azim=45)
        
        # 添加颜色条
        cbar = self.model_figure.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
        cbar.set_label('蚀刻能力 (nm)')
        
        self.model_figure.tight_layout()
        self.model_canvas.draw()
        
    def _export_interpolated_data(self):
        """导出插值结果到CSV文件"""
        if self.grid_data is None:
            QMessageBox.warning(self, "警告", "无有效插值数据可供导出")
            return
            
        try:
            current_time = QtCore.QDateTime.currentDateTime().toString("yyyyMMddHHmmss")
            default_filename = f"{current_time}_BeamSpot.csv"
            
            save_path, _ = QFileDialog.getSaveFileName(
                self, "保存插值数据文件",
                os.path.join(os.path.expanduser('~'), default_filename),
                "CSV Files (*.csv)"
            )
            
            if not save_path:
                return
                
            if not save_path.lower().endswith('.csv'):
                save_path += '.csv'
            
            x_grid = np.linspace(-15, 15, 31)
            y_grid = np.linspace(-15, 15, 31)
            grid_vals = np.zeros((31, 31), dtype=float)
            grid_step = 0.1
            grid_range = np.arange(-14.9, 15.1, grid_step)
            
            for i, y_val in enumerate(y_grid):
                for j, x_val in enumerate(x_grid):
                    x_index = np.argmin(np.abs(grid_range - x_val))
                    y_index = np.argmin(np.abs(grid_range - y_val))
                    #grid_vals[i, j] = self.grid_data[y_index, x_index]
                    grid_vals[i, j] = self.grid_data[x_index, y_index]
            
            # 确保所有导出的值非负
            negative_count = np.sum(grid_vals < 0)
            if negative_count > 0:
                min_val = np.min(grid_vals)
                logger.warning(f"导出前存在 {negative_count} 个负值点, 最低值为: {min_val:.6f} nm")
                logger.info("导出前更正所有负值点为0")
                grid_vals = np.maximum(grid_vals, 0)
            
            # 写入CSV
            with open(save_path, 'w', newline='') as file:
                writer = csv.writer(file)
                for i in range(31):
                    row_values = [f"{val:.2f}" for val in grid_vals[i, :]]
                    writer.writerow(row_values)
            
            # 更新状态
            self.export_status.setText(f"成功导出: {os.path.basename(save_path)}")
            timer = QtCore.QTimer(self)
            timer.singleShot(3000, lambda: self.export_status.setText("数据就绪可导出"))
            
            QMessageBox.information(self, "导出成功", 
                                   f"蚀刻能力矩阵数据已成功导出至:\n{save_path}")
            
        except Exception as e:
            logger.error(f"导出蚀刻能力数据时出错: {str(e)}")
            QMessageBox.critical(self, "导出失败", f"导出过程中发生错误:\n{str(e)}")
            self.export_status.setText("导出失败")
