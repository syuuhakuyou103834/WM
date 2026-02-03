import os
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
                            QLineEdit, QPushButton, QLabel, QComboBox, 
                            QFileDialog, QSizePolicy, QMessageBox, QCheckBox, QSplitter)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from core.beamShape_creator import BeamShapeCreator
from utils.file_io import ROOT_DIR

class BeamShapeCreatorUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.processor = BeamShapeCreator()
        # 首先设置默认输出目录
        self.default_output_dir = ROOT_DIR / "Data" / "outputs" / "new_BeamShapeProfile"
        self.default_output_dir.mkdir(parents=True, exist_ok=True)  # 确保目录存在
        
        self.init_ui()

    def init_ui(self):
        
        # 主布局采用垂直布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(0)
        
        # 创建主分割器 (垂直方向：上部分设置区，下部分图表区)
        main_splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(main_splitter)
        
        # =========== 顶部区域 ===========
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setSpacing(5)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建水平分割器用于文件设置和参数设置
        settings_splitter = QSplitter(Qt.Horizontal)
        top_layout.addWidget(settings_splitter)
        
        # ===== 左侧: 文件选择区 =====
        file_group = QGroupBox("输入/输出文件设置")
        file_grid = QGridLayout()
        
        # X方向数据
        file_grid.addWidget(QLabel("X方向剖面数据:"), 0, 0)
        self.x_path_entry = QLineEdit()
        file_grid.addWidget(self.x_path_entry, 0, 1)
        self.x_browse_btn = QPushButton("浏览...")
        self.x_browse_btn.clicked.connect(self.browse_x_file)
        file_grid.addWidget(self.x_browse_btn, 0, 2)
        
        # Y方向数据
        file_grid.addWidget(QLabel("Y方向剖面数据:"), 1, 0)
        self.y_path_entry = QLineEdit()
        file_grid.addWidget(self.y_path_entry, 1, 1)
        self.y_browse_btn = QPushButton("浏览...")
        self.y_browse_btn.clicked.connect(self.browse_y_file)
        file_grid.addWidget(self.y_browse_btn, 1, 2)
        
        # 输出文件
        file_grid.addWidget(QLabel("输出文件:"), 2, 0)
        self.output_entry = QLineEdit()
        file_grid.addWidget(self.output_entry, 2, 1)
        self.output_browse_btn = QPushButton("浏览...")
        self.output_browse_btn.clicked.connect(self.browse_output_file)
        file_grid.addWidget(self.output_browse_btn, 2, 2)
        
        # 自动填充路径作为默认值
        default_output_path = self.default_output_dir / "beam_shape.csv"
        self.output_entry.setText(str(default_output_path))
        file_group.setLayout(file_grid)
        settings_splitter.addWidget(file_group)
        
        # ===== 右侧: 参数设置区 =====
        param_widget = QWidget()
        param_layout = QVBoxLayout(param_widget)
        param_layout.setSpacing(5)
        param_layout.setContentsMargins(0, 0, 0, 0)
        
        param_group = QGroupBox("参数设置")
        param_inner_layout = QGridLayout()
        
        # 平面尺寸
        param_inner_layout.addWidget(QLabel("输出平面尺寸 (mm):"), 0, 0)
        self.size_entry = QLineEdit("30.0")
        self.size_entry.setMaximumWidth(100)
        param_inner_layout.addWidget(self.size_entry, 0, 1)
        
        # 采样步长
        param_inner_layout.addWidget(QLabel("采样步长 (mm):"), 0, 2)
        self.step_entry = QLineEdit("1.0")
        self.step_entry.setMaximumWidth(100)
        param_inner_layout.addWidget(self.step_entry, 0, 3)
        
        # 插值方法
        param_inner_layout.addWidget(QLabel("插值方法:"), 1, 0)
        self.interp_method = QComboBox()
        self.interp_method.addItems(["三次样条", "PCHIP保形", "五次样条"])
        self.interp_method.setCurrentIndex(0)  # 默认三次样条
        self.interp_method.setToolTip("选择一维插值方法")
        param_inner_layout.addWidget(self.interp_method, 1, 1, 1, 3)  # 跨1行3列
        
        # 平均方法
        param_inner_layout.addWidget(QLabel("平均方法:"), 2, 0)
        self.average_method = QComboBox()
        self.average_method.addItems(["几何平均", "算术平均"])
        self.average_method.setCurrentIndex(0)  # 默认几何平均
        self.average_method.setToolTip("选择XY方向的合并方法")
        param_inner_layout.addWidget(self.average_method, 2, 1, 1, 3)  # 跨列
        
        # 边缘过渡方法
        param_inner_layout.addWidget(QLabel("边缘过渡方法:"), 3, 0)
        self.edge_method = QComboBox()
        self.edge_method.addItems(["无", "指数衰减", "z轴下移"])
        self.edge_method.setCurrentIndex(1)  # 默认指数衰减
        self.edge_method.setToolTip("选择如何过渡到边缘")
        param_inner_layout.addWidget(self.edge_method, 3, 1, 1, 3)  # 跨列
        
        param_group.setLayout(param_inner_layout)
        param_layout.addWidget(param_group)
        
        # 处理按钮
        self.process_btn = QPushButton("生成光束轮廓")
        self.process_btn.setMinimumHeight(35)
        self.process_btn.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        self.process_btn.clicked.connect(self.process_data)
        param_layout.addWidget(self.process_btn)
        
        # 状态标签
        self.status_label = QLabel("就绪: 请选择输入文件")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px; border: 1px solid #CCCCCC; padding: 5px;")
        param_layout.addWidget(self.status_label)
        
        param_layout.addStretch(1)  # 弹性空间以保持组件顶部对齐
        settings_splitter.addWidget(param_widget)
        
        # =========== 添加顶部区域到主分割器 ===========
        main_splitter.addWidget(top_widget)
        
        # =========== 底部区域: 图表区 ===========
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setSpacing(0)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建图表容器
        self.fig = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, chart_widget)
        
        # 设置图表属性
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumHeight(400)  # 更大高度
        
        # 添加图表组件
        chart_layout.addWidget(self.toolbar)
        chart_layout.addWidget(self.canvas)
        
        # =========== 添加底部区域到主分割器 ===========
        main_splitter.addWidget(chart_widget)
        
        # 设置默认大小比例
        settings_splitter.setSizes([400, 600])  # 文件设置:参数设置 = 4:6
        main_splitter.setSizes([300, 700])      # 顶部设置:底部图表 = 3:7
        
        # 保存分隔条的句柄，以便在后续可以调整
        self.settings_splitter = settings_splitter
        self.main_splitter = main_splitter
    
    def browse_x_file(self):
        """浏览并选择X方向数据文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择X方向剖面数据", 
            os.getcwd(), 
            "CSV文件 (*.csv);;所有文件 (*)"
        )
        if file_path:
            self.x_path_entry.setText(file_path)
            self.status_label.setText(f"已加载X数据: {os.path.basename(file_path)}")
    
    def browse_y_file(self):
        """浏览并选择Y方向数据文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Y方向剖面数据", 
            os.getcwd(), 
            "CSV文件 (*.csv);;所有文件 (*)"
        )
        if file_path:
            self.y_path_entry.setText(file_path)
            self.status_label.setText(f"已加载Y数据: {os.path.basename(file_path)}")
            
            # 如果X数据已设置，更新输出文件名
            if self.x_path_entry.text():
                x_file = os.path.basename(self.x_path_entry.text())
                y_file = os.path.basename(file_path)
                output_name = f"beam_{os.path.splitext(x_file)[0]}_x_{os.path.splitext(y_file)[0]}.csv"
                output_path = self.default_output_dir / output_name
                self.output_entry.setText(str(output_path))
    
    def browse_output_file(self):
        """浏览并选择输出文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择输出文件位置", 
            self.output_entry.text(), 
            "CSV文件 (*.csv)"
        )
        if file_path:
            if not file_path.lower().endswith('.csv'):
                file_path += '.csv'
            self.output_entry.setText(file_path)
    
    def process_data(self):
        
        """执行数据处理主流程"""
        try:
            # 确保输出目录存在
            output_path = self.output_entry.text()
            if output_path:
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    
            self.status_label.setText("处理中...")
            self.process_btn.setEnabled(False)
            
            # 检查必要文件
            if not self.x_path_entry.text() or not self.y_path_entry.text():
                raise ValueError("请先选择X和Y方向的数据文件")
                
            if not self.output_entry.text():
                raise ValueError("请指定输出文件路径")
            
            # 获取参数
            params = {
                "x_path": self.x_path_entry.text(),
                "y_path": self.y_path_entry.text(),
                "output_path": self.output_entry.text(),
                "plane_size": float(self.size_entry.text().strip() or "30.0"),
                "step": float(self.step_entry.text().strip() or "1.0"),
                "interp_method": self.interp_method.currentText().split(' ')[0],
                "average_method": self.average_method.currentText().split(' ')[0],
                "edge_method": self.edge_method.currentText()
            }
            
            # 保存用户选择的平均方法
            self.processor.average_method = params["average_method"]
            # 处理插值方法
            self.processor.interp_method = params["interp_method"]
            # 保存边缘处理方法
            self.processor.edge_method = params["edge_method"]
            
            # 加载并归一化数据
            self.processor.load_and_normalize_data(params["x_path"], params["y_path"])
            
            # 创建插值器
            interp_info_x, interp_info_y = self.processor.create_axis_interpolators(
                *self.processor.raw_x, 
                *self.processor.raw_y,
                params["plane_size"]
            )
            
            # 生成二维网格 (根据选择的边缘处理方法)
            coords, z_matrix = self.processor.generate_asymmetric_grid(
                interp_info_x, interp_info_y, 
                params["plane_size"], params["step"]
            )
            
            # 保存结果
            self.processor.save_as_csv(z_matrix, coords, params["output_path"])
            
            # 显示成功消息
            self.status_label.setText(
                f"处理完成 | "
                f"FWHM: X={self.processor.x_fwhm:.2f}mm, Y={self.processor.y_fwhm:.2f}mm | "
                f"输出文件: {os.path.basename(params['output_path'])}"
            )
            
            # 可视化结果
            self.visualize_results(interp_info_x, interp_info_y, coords, z_matrix, params)
            
        except Exception as e:
            QMessageBox.critical(self, "处理错误", f"发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"错误: {str(e)}")
        finally:
            self.process_btn.setEnabled(True)
    
    def visualize_results(self, interp_info_x, interp_info_y, coords, z_matrix, params):
        """结果可视化"""
        self.fig.clear()
        gs = self.fig.add_gridspec(3, 2, height_ratios=[2, 1, 1])
        
        # ====================== 图表1: 3D表面图 ======================
        ax_3d = self.fig.add_subplot(gs[0, :], projection='3d')
        xx, yy = np.meshgrid(coords, coords)
        surf = ax_3d.plot_surface(
            xx, yy, z_matrix, 
            cmap='jet', 
            rstride=1, 
            cstride=1, 
            edgecolor='k', 
            linewidth=0.1, 
            alpha=0.6
        )
        
        # 添加图例（颜色条）
        cbar = self.fig.colorbar(surf, ax=ax_3d, shrink=0.5, aspect=5)
        cbar.set_label('强度 (%)')
        
        # 添加标题
        ax_3d.set_title(f"光束轮廓 3D 视图 ({params['interp_method']}插值 + {params['average_method']}平均)")
        ax_3d.set_xlabel('X (mm)')
        ax_3d.set_ylabel('Y (mm)')
        ax_3d.set_zlabel('强度 (%)')
        
        # ====================== 图表2: 2D等高线图 ======================
        ax_contour = self.fig.add_subplot(gs[1, 0])
        ctf = ax_contour.contourf(xx, yy, z_matrix, 15, cmap='jet')
        self.fig.colorbar(ctf, ax=ax_contour).set_label('强度 (%)')
        
        # 添加轮廓线
        ax_contour.contour(xx, yy, z_matrix, 6, colors='black', linewidths=0.5)
        
        # 标记FWHM点
        half_val_x = self.processor.raw_x[1].max() * 0.5
        half_val_y = self.processor.raw_y[1].max() * 0.5
        
        # 标记FWHM矩形框
        ax_contour.plot(
            [-self.processor.x_fwhm/2, self.processor.x_fwhm/2],
            [-self.processor.y_fwhm/2, -self.processor.y_fwhm/2],
            'k--', linewidth=1.0
        )
        ax_contour.plot(
            [-self.processor.x_fwhm/2, self.processor.x_fwhm/2],
            [self.processor.y_fwhm/2, self.processor.y_fwhm/2],
            'k--', linewidth=1.0
        )
        ax_contour.plot(
            [-self.processor.x_fwhm/2, -self.processor.x_fwhm/2],
            [-self.processor.y_fwhm/2, self.processor.y_fwhm/2],
            'k--', linewidth=1.0
        )
        ax_contour.plot(
            [self.processor.x_fwhm/2, self.processor.x_fwhm/2],
            [-self.processor.y_fwhm/2, self.processor.y_fwhm/2],
            'k--', linewidth=1.0
        )
        
        ax_contour.set_title(f"等高线图 (FWHM: X={self.processor.x_fwhm:.2f}mm Y={self.processor.y_fwhm:.2f}mm)")
        ax_contour.set_xlabel('X (mm)')
        ax_contour.set_ylabel('Y (mm)')
        
        # ====================== 图表3: X方向剖面 ======================
        ax_x = self.fig.add_subplot(gs[1, 1])
    
        # 原始数据
        orig_x_coords, orig_x_vals = self.processor.raw_x
        ax_x.plot(orig_x_coords, orig_x_vals, 'bo-', linewidth=1, markersize=3, label='原始数据')
        
        # 插值后的中心线数据 (沿X轴)
        x_line = coords.copy()
        interp_x, _ = interp_info_x
        center_x_vals = interp_x(x_line)
        
        ax_x.plot(x_line, center_x_vals, 'r-', linewidth=1.5, label='插值曲线')
        
        # 标记FWHM点
        ax_x.axhline(y=50, color='k', linestyle='--', alpha=0.5)
        ax_x.axvline(x=-self.processor.x_fwhm/2, color='g', linestyle='--', alpha=0.7)
        ax_x.axvline(x=self.processor.x_fwhm/2, color='g', linestyle='--', alpha=0.7)
        
        ax_x.set_title(f"X方向剖面 (FWHM={self.processor.x_fwhm:.2f}mm)")
        ax_x.set_xlabel('位置 (mm)')
        ax_x.set_ylabel('强度 (%)')
        ax_x.legend(loc='best')
        ax_x.grid(True)
        
        # ====================== 图表4: Y方向剖面 ======================
        ax_y = self.fig.add_subplot(gs[2, 0])
    
        # 原始数据
        orig_y_coords, orig_y_vals = self.processor.raw_y
        ax_y.plot(orig_y_coords, orig_y_vals, 'bo-', linewidth=1, markersize=3, label='原始数据')
        
        # 插值后的中心线数据 (沿Y轴)
        y_line = coords.copy()
        interp_y, _ = interp_info_y
        center_y_vals = interp_y(y_line)
        
        ax_y.plot(y_line, center_y_vals, 'r-', linewidth=1.5, label='插值曲线')
        
        # 标记FWHM点
        ax_y.axhline(y=50, color='k', linestyle='--', alpha=0.5)
        ax_y.axvline(x=-self.processor.y_fwhm/2, color='g', linestyle='--', alpha=0.7)
        ax_y.axvline(x=self.processor.y_fwhm/2, color='g', linestyle='--', alpha=0.7)
        
        ax_y.set_title(f"Y方向剖面 (FWHM={self.processor.y_fwhm:.2f}mm)")
        ax_y.set_xlabel('位置 (mm)')
        ax_y.set_ylabel('强度 (%)')
        ax_y.legend(loc='best')
        ax_y.grid(True)
        
        # ====================== 图表5: 对角轮廓 ======================
        ax_diag = self.fig.add_subplot(gs[2, 1])
        
        # 计算对角线
        diag_line = np.linspace(-params['plane_size']/2, params['plane_size']/2, len(coords))
        diag_vals = []
        
        # 对角线上的点位置
        for i in range(len(diag_line)):
            x_val = diag_line[i]
            y_val = diag_line[i]
            
            x_intensity = interp_x(x_val)
            y_intensity = interp_y(y_val)
            
            if params['average_method'] == '几何平均':
                diag_vals.append(np.sqrt(x_intensity * y_intensity))
            else:
                diag_vals.append((x_intensity + y_intensity) / 2)
        
        ax_diag.plot(diag_line, diag_vals, 'r-', linewidth=1.5, label='对角剖面')
        ax_diag.set_title(f"对角线轮廓 (45度)")
        ax_diag.set_xlabel('径向距离 (mm)')
        ax_diag.set_ylabel('强度 (%)')
        ax_diag.grid(True)
        
        # 调整布局
        self.fig.tight_layout()
        self.canvas.draw()
        
        # 成功消息
        self.status_label.setText(
            f"处理完成 | "
            f"FWHM: X={self.processor.x_fwhm:.2f}mm, Y={self.processor.y_fwhm:.2f}mm | "
            f"输出文件: {os.path.basename(params['output_path'])}"
        )

# 用于独立测试的模块
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = BeamShapeCreatorUI()
    window.setWindowTitle("光束轮廓生成器")
    window.resize(1200, 900)  # 更大的初始大小便于分隔条操作
    window.show()
    sys.exit(app.exec_())
