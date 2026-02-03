import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
    QLineEdit, QPushButton, QLabel, QFileDialog, QSplitter,
    QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np

from core.cross_test_stagecenter_analyzer import StageCenterAnalyzer

class CrossTestAnalyzerUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.analyzer = StageCenterAnalyzer()
        self.init_ui()
    
    def init_ui(self):
        # 主布局采用水平布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # 创建主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        
        # =========== 左侧区域: 文件设置 ===========
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(10)
        
        # 文件输入组
        file_group = QGroupBox("文件设置")
        file_grid = QGridLayout()
        
        # 初始文件
        file_grid.addWidget(QLabel("CrossTest初始文件:"), 0, 0)
        self.initial_file_entry = QLineEdit()
        file_grid.addWidget(self.initial_file_entry, 0, 1)
        self.initial_browse_btn = QPushButton("浏览...")
        self.initial_browse_btn.clicked.connect(lambda: self.browse_file(self.initial_file_entry, "选择CrossTest初始文件"))
        file_grid.addWidget(self.initial_browse_btn, 0, 2)
        
        # 刻蚀后文件
        file_grid.addWidget(QLabel("CrossTest刻蚀后文件:"), 1, 0)
        self.after_file_entry = QLineEdit()
        file_grid.addWidget(self.after_file_entry, 1, 1)
        self.after_browse_btn = QPushButton("浏览...")
        self.after_browse_btn.clicked.connect(lambda: self.browse_file(self.after_file_entry, "选择CrossTest刻蚀后文件"))
        file_grid.addWidget(self.after_browse_btn, 1, 2)
        
        file_group.setLayout(file_grid)
        left_layout.addWidget(file_group)
        
        # 状态标签
        self.status_label = QLabel("请选择CrossTest初始文件和刻蚀后文件")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; padding: 10px;")
        left_layout.addWidget(self.status_label)
        
        # 处理按钮
        self.process_btn = QPushButton("分析并计算新中心点")
        self.process_btn.setMinimumHeight(40)
        self.process_btn.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px;")
        self.process_btn.clicked.connect(self.process_data)
        left_layout.addWidget(self.process_btn)
        
        # 图表区域
        self.fig = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.fig)
        self.create_placeholder_plot()
        
        # 设置图表属性
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumHeight(300)
        left_layout.addWidget(self.canvas, 1)
        
        # =========== 右侧区域: 中心点计算 ===========
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)
        
        # 中心点设置组
        center_group = QGroupBox("中心点计算")
        center_grid = QGridLayout()
        
        # 旧中心点
        center_grid.addWidget(QLabel("原中心点X坐标:"), 0, 0)
        self.old_center_x_entry = QLineEdit()
        self.old_center_x_entry.setPlaceholderText("请输入原中心点X坐标")
        center_grid.addWidget(self.old_center_x_entry, 0, 1)
        
        center_grid.addWidget(QLabel("原中心点Y坐标:"), 1, 0)
        self.old_center_y_entry = QLineEdit()
        self.old_center_y_entry.setPlaceholderText("请输入原中心点Y坐标")
        center_grid.addWidget(self.old_center_y_entry, 1, 1)
        
        # 分隔线
        center_grid.addWidget(QLabel(), 2, 0)  # 空行
        center_grid.addWidget(QLabel("--- 计算结果 ---", self), 3, 0, 1, 2, Qt.AlignCenter)
        
        # 计算结果
        center_grid.addWidget(QLabel("新的中心点X坐标:"), 4, 0)
        self.new_center_x_label = QLabel("待计算")
        self.new_center_x_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        center_grid.addWidget(self.new_center_x_label, 4, 1)
        
        center_grid.addWidget(QLabel("新的中心点Y坐标:"), 5, 0)
        self.new_center_y_label = QLabel("待计算")
        self.new_center_y_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        center_grid.addWidget(self.new_center_y_label, 5, 1)
        
        center_grid.addWidget(QLabel(), 6, 0)  # 空行
        
        # 偏移量显示
        center_grid.addWidget(QLabel("上方偏移量 (Δ_up):"), 7, 0)
        self.delta_up_label = QLabel("待计算")
        center_grid.addWidget(self.delta_up_label, 7, 1)
        
        center_grid.addWidget(QLabel("下方偏移量 (Δ_down):"), 8, 0)
        self.delta_down_label = QLabel("待计算")
        center_grid.addWidget(self.delta_down_label, 8, 1)
        
        center_grid.addWidget(QLabel("右方偏移量 (Δ_right):"), 9, 0)
        self.delta_right_label = QLabel("待计算")
        center_grid.addWidget(self.delta_right_label, 9, 1)
        
        center_grid.addWidget(QLabel("左方偏移量 (Δ_left):"), 10, 0)
        self.delta_left_label = QLabel("待计算")
        center_grid.addWidget(self.delta_left_label, 10, 1)
        
        center_grid.addWidget(QLabel(), 11, 0)  # 空行
        
        center_grid.addWidget(QLabel("中心点X偏移量 (Δ_x):"), 12, 0)
        self.delta_x_label = QLabel("待计算")
        self.delta_x_label.setStyleSheet("font-weight: bold;")
        center_grid.addWidget(self.delta_x_label, 12, 1)
        
        center_grid.addWidget(QLabel("中心点Y偏移量 (Δ_y):"), 13, 0)
        self.delta_y_label = QLabel("待计算")
        self.delta_y_label.setStyleSheet("font-weight: bold;")
        center_grid.addWidget(self.delta_y_label, 13, 1)
        
        center_group.setLayout(center_grid)
        right_layout.addWidget(center_group)
        
        # 添加左右区域到主分割器
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        
        # 设置初始大小比例
        main_splitter.setSizes([500, 300])
        
        # 添加主分割器到主布局
        main_layout.addWidget(main_splitter)

    def create_placeholder_plot(self):
        """创建占位图表"""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.text(0.5, 0.5, '数据加载后将显示刻蚀量分布图', 
                horizontalalignment='center',
                verticalalignment='center',
                fontsize=14, alpha=0.5)
        ax.axis('off')
        self.canvas.draw()
    
    def browse_file(self, target_entry, title):
        """浏览并选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, title, 
            os.getcwd(), 
            "CSV文件 (*.csv);;所有文件 (*)"
        )
        if file_path:
            target_entry.setText(file_path)
            if self.initial_file_entry.text() and self.after_file_entry.text():
                self.status_label.setText("文件已选择，准备好计算")
    
    def process_data(self):
        """执行数据处理主流程"""
        try:
            # 检查文件是否选择
            if not self.initial_file_entry.text() or not self.after_file_entry.text():
                QMessageBox.warning(self, "输入错误", "请先选择初始文件和刻蚀后文件")
                return
                
            # 获取原中心点坐标
            try:
                old_center_x = float(self.old_center_x_entry.text().strip())
                old_center_y = float(self.old_center_y_entry.text().strip())
            except ValueError:
                QMessageBox.warning(self, "输入错误", "原中心点坐标必须是数字")
                return
                
            # 更新状态
            self.status_label.setText("处理中...")
            self.process_btn.setEnabled(False)
            
            # 加载文件
            self.analyzer.load_files(
                self.initial_file_entry.text(),
                self.after_file_entry.text()
            )
            
            # 计算结果
            results = self.analyzer.calculate_results(old_center_x, old_center_y)
            
            # 更新UI显示结果
            self.new_center_x_label.setText(f"{results['new_center_x']:.4f}")
            self.new_center_y_label.setText(f"{results['new_center_y']:.4f}")
            self.delta_up_label.setText(f"{results['delta_up']:.4f}")
            self.delta_down_label.setText(f"{results['delta_down']:.4f}")
            self.delta_right_label.setText(f"{results['delta_right']:.4f}")
            self.delta_left_label.setText(f"{results['delta_left']:.4f}")
            self.delta_x_label.setText(f"{results['delta_x']:.4f}")
            self.delta_y_label.setText(f"{results['delta_y']:.4f}")
            
            # 更新状态
            self.status_label.setText("计算完成")
            
            # 更新图表显示刻蚀量分布
            self.update_plot(results)
            
        except Exception as e:
            QMessageBox.critical(self, "处理错误", f"发生错误: {str(e)}")
            self.status_label.setText(f"错误: {str(e)}")
        finally:
            self.process_btn.setEnabled(True)
            
    def update_plot(self, results):
        """更新图表显示刻蚀量分布"""
        df = results['etching_df']
        
        # 创建4x4子图网格
        self.fig.clear()
        gs = self.fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        # 上方区域
        ax_top = self.fig.add_subplot(gs[0, 0])
        top_section = df.iloc[1:82]
        ax_top.plot(top_section['X'], top_section['TrimmingAmount'], 'b-')
        ax_top.axvline(results['delta_up'], color='r', linestyle='--')
        ax_top.set_title('上方刻蚀量分布 (y=40)')
        ax_top.set_xlabel('X 位置')
        ax_top.set_ylabel('刻蚀量 (nm)')
        
        # 下方区域
        ax_bottom = self.fig.add_subplot(gs[0, 1])
        bottom_section = df.iloc[82:163]
        ax_bottom.plot(bottom_section['X'], bottom_section['TrimmingAmount'], 'g-')
        ax_bottom.axvline(results['delta_down'], color='r', linestyle='--')
        ax_bottom.set_title('下方刻蚀量分布 (y=-40)')
        ax_bottom.set_xlabel('X 位置')
        
        # 右方区域
        ax_right = self.fig.add_subplot(gs[1, 0])
        right_section = df.iloc[163:244]
        ax_right.plot(right_section['Y'], right_section['TrimmingAmount'], 'm-')
        ax_right.axvline(results['delta_right'], color='r', linestyle='--')
        ax_right.set_title('右方刻蚀量分布 (x=40)')
        ax_right.set_xlabel('Y 位置')
        ax_right.set_ylabel('刻蚀量 (nm)')
        
        # 左方区域
        ax_left = self.fig.add_subplot(gs[1, 1])
        left_section = df.iloc[244:]
        ax_left.plot(left_section['Y'], left_section['TrimmingAmount'], 'c-')
        ax_left.axvline(results['delta_left'], color='r', linestyle='--')
        ax_left.set_title('左方刻蚀量分布 (x=-40)')
        ax_left.set_xlabel('Y 位置')
        
        # 添加总体标题
        self.fig.suptitle('刻蚀量分布图（红色虚线表示偏移量位置）', fontsize=12)
        self.fig.tight_layout(rect=[0, 0, 1, 0.97])  # 调整布局保留suptitle空间
        self.canvas.draw()
