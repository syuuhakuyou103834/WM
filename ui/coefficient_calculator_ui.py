from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QPushButton, QFileDialog, QHBoxLayout, QSplitter,
    QMessageBox, QSizePolicy, QLineEdit
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pathlib import Path
from core.beamCoefficient_Calculator import BeamCoefficientCalculator
from utils.file_io import get_latest_thickness_files, get_resource_path

class CoefficientCalculatorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.calculator = BeamCoefficientCalculator()
        self.initial_path = None  # 保存初始厚度文件路径
        self.after_path = None    # 保存刻蚀后厚度文件路径
        self.simulation_path = None # 保存Simulation文件路径
        self.target_value = None   # 保存目标膜厚值

        # 设置默认Map文件路径
        self.default_simulation_file = get_resource_path("Data/inputs/Default Beam coefficient test Map/2801-Default Map.csv")

        self._setup_ui()

        # 初始化默认Map文件
        self._initialize_default_simulation()

        # 自动加载最新厚度文件
        self._load_default_files()

    def _initialize_default_simulation(self):
        """初始化默认Map文件"""
        try:
            # 检查默认Map文件是否存在
            if Path(self.default_simulation_file).exists():
                self.simulation_path = self.default_simulation_file
                self.sim_label.setText("已选择默认Map文件")
            else:
                # 如果默认文件不存在，保持原状
                self.sim_label.setText("默认Map文件不存在")
                self.simulation_path = None
        except Exception as e:
            print(f"初始化默认Map文件失败: {e}")
            self.simulation_path = None

    def _setup_ui(self):
        # 使用水平布局作为主布局
        main_layout = QHBoxLayout()
        
        ############################
        # 左侧区域 - 文件选择 (40%)
        ############################
        left_container = QWidget()
        left_layout = QVBoxLayout()
        
        # Simulation文件选择组
        sim_group = QGroupBox("Simulation文件及目标选择")
        sim_layout = QFormLayout()
        
        self.sim_label = QLabel("未选择Simulation文件")
        self.sim_label.setWordWrap(True)  # 允许文本换行
        self.select_sim_button = QPushButton("选择非默认Map的其他Map")
        self.select_sim_button.clicked.connect(self._select_simulation_file)
        
        # 目标膜厚输入
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("输入目标膜厚值")
        
        # 处理文件按钮
        self.process_button = QPushButton("处理Simulation文件")
        self.process_button.clicked.connect(self._process_simulation)
        
        sim_layout.addRow("文件位置:", self.sim_label)
        sim_layout.addRow(self.select_sim_button)
        sim_layout.addRow("目标膜厚:", self.target_edit)
        sim_layout.addRow(self.process_button)
        
        sim_group.setLayout(sim_layout)
        
        # 厚度文件选择组
        file_group = QGroupBox("厚度文件选择")
        file_layout = QFormLayout()
        
        self.initial_label = QLabel("未选择初始厚度文件")
        self.initial_label.setWordWrap(True)  # 允许文本换行
        self.select_initial_button = QPushButton("选择初始厚度文件")
        self.select_initial_button.clicked.connect(
            lambda: self._select_thickness_file("initial")
        )
        
        # 刻蚀后厚度文件选择
        self.after_label = QLabel("未选择刻蚀后厚度文件")
        self.after_label.setWordWrap(True)  # 允许文本换行
        self.select_after_button = QPushButton("选择刻蚀后厚度文件")
        self.select_after_button.clicked.connect(
            lambda: self._select_thickness_file("after")
        )
        
        # 加载默认文件按钮
        self.load_default_button = QPushButton("加载默认最新文件")
        self.load_default_button.clicked.connect(self._load_default_files)
        
        file_layout.addRow("初始厚度:", self.initial_label)
        file_layout.addRow(self.select_initial_button)
        file_layout.addRow("刻蚀后厚度:", self.after_label)
        file_layout.addRow(self.select_after_button)
        file_layout.addRow(self.load_default_button)
        
        file_group.setLayout(file_layout)
        
        left_layout.addWidget(sim_group)
        left_layout.addWidget(file_group)
        left_layout.addStretch(1)  # 添加弹性空间使文件选择组保持在顶部
        
        left_container.setLayout(left_layout)
        left_container.setMinimumWidth(350)  # 设置更大宽度
        
        ############################
        # 右侧区域 - 结果和图表 (60%)
        ############################
        right_container = QWidget()
        right_layout = QVBoxLayout()
        
        # 创建垂直分离器，将结果和数据分成上下两部分
        right_splitter = QSplitter(Qt.Vertical)
        
        # 计算结果组 (占右侧高度的20%)
        result_group = QGroupBox("计算结果")
        result_layout = QFormLayout()
        
        self.slope_label = QLabel("尚未计算")
        result_layout.addRow("斜率(q):", self.slope_label)
        
        self.r2_label = QLabel("尚未计算")
        result_layout.addRow("R平方值:", self.r2_label)
        
        # 计算按钮
        self.calculate_button = QPushButton("计算系数")
        self.calculate_button.clicked.connect(self._calculate_coefficient)
        result_layout.addRow(self.calculate_button)
        
        result_group.setLayout(result_layout)
        
        # 绘图区域 (占右侧高度的80%)
        plot_container = QWidget()
        plot_layout = QVBoxLayout()
        plot_layout.setContentsMargins(0, 0, 0, 0)
        
        self.figure = None
        self.canvas = FigureCanvas(Figure(figsize=(8, 6)))
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        plot_layout.addWidget(self.canvas)
        
        plot_container.setLayout(plot_layout)
        
        # 将结果组和绘图容器添加到垂直分离器
        right_splitter.addWidget(result_group)
        right_splitter.addWidget(plot_container)
        
        # 设置初始比例 (结果组20%，图表80%)
        right_splitter.setSizes([int(self.height() * 0.2), int(self.height() * 0.8)])
        
        right_layout.addWidget(right_splitter)
        right_container.setLayout(right_layout)
        
        ############################
        # 添加水平分离器分隔左右区域
        ############################
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(left_container)
        main_splitter.addWidget(right_container)
        
        # 设置初始比例 (左侧40%，右侧60%)
        main_splitter.setSizes([int(self.width() * 0.4), int(self.width() * 0.6)])
        
        # 用户可以通过鼠标拖动调整分隔条位置
        main_splitter.setChildrenCollapsible(False)  # 防止子部件被完全折叠
        
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)
    
    def _select_simulation_file(self):
        """选择非默认的Simulation文件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择非默认Map的其他Map",
            "",
            "CSV Files (*.csv)",
            options=options
        )

        if file_path:
            self.simulation_path = file_path
            if file_path == self.default_simulation_file:
                self.sim_label.setText("已选择默认Map文件")
            else:
                self.sim_label.setText(file_path)

    def set_simulation_file(self, file_path):
        """设置Simulation文件路径"""
        self.simulation_path = file_path
        if file_path == self.default_simulation_file:
            self.sim_label.setText("已选择默认Map文件")
        else:
            self.sim_label.setText(file_path)
    
    def _process_simulation(self):
        """处理用户选择的simulation文件"""
        target_text = self.target_edit.text().strip()
        if not self.simulation_path:
            QMessageBox.warning(self, "警告", "请先选择Simulation文件")
            return
        
        if not target_text:
            QMessageBox.warning(self, "警告", "请输入目标膜厚值")
            return
        
        try:
            # 尝试转换为浮点数
            target_value = float(target_text)
        except ValueError:
            QMessageBox.warning(self, "警告", "目标膜厚值必须是数字")
            return
        
        try:
            # 调用计算器处理文件
            success = self.calculator.process_simulation_file(
                self.simulation_path, 
                target_value
            )
            
            if success:
                QMessageBox.information(self, "成功", "Simulation文件处理成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理失败: {str(e)}")
    
    def _select_thickness_file(self, file_type):
        """选择厚度文件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            f"选择{file_type}文件", 
            "", 
            "CSV Files (*.csv)", 
            options=options
        )
        
        if not file_path:
            return
        
        if file_type == "initial":
            self.initial_path = file_path
            self.initial_label.setText(file_path)
        else:
            self.after_path = file_path
            self.after_label.setText(file_path)
    
    def _load_default_files(self):
        """加载默认的最新文件"""
        try:
            initial_path, after_path = get_latest_thickness_files()
            self.initial_path = initial_path
            self.after_path = after_path
            self.initial_label.setText(str(initial_path))
            self.after_label.setText(str(after_path))
        except Exception as e:
            self._show_error(f"无法加载默认文件: {str(e)}")
    
    def _calculate_coefficient(self):
        """计算beam系数"""
        # Validation
        validation_errors = []
        
        # 检查Simulation文件是否已处理
        if len(self.calculator.set_values) == 0:
            validation_errors.append("请先选择并处理Simulation文件")
        
        if not self.initial_path:
            validation_errors.append("请选择初始厚度文件")
        
        if not self.after_path:
            validation_errors.append("请选择刻蚀后厚度文件")
        
        if validation_errors:
            self._show_error("\n".join(validation_errors))
            return
        
        try:
            # 计算系数
            success = self.calculator.calculate_coefficient(
                self.initial_path, 
                self.after_path
            )
            
            if success:
                # 更新结果标签
                self.slope_label.setText(f"{self.calculator.slope:.6f}")
                self.r2_label.setText(f"{self.calculator.r_squared:.6f}")
                
                # 更新图表
                fig = self.calculator.plot_data()
                self.canvas.figure = fig
                self.canvas.draw()
        except Exception as e:
            self._show_error(f"计算失败: {str(e)}")
    
    def _show_error(self, message):
        """显示错误消息"""
        self.slope_label.setText(f"错误: {message}")
        self.r2_label.setText("")

        # 创建错误信息图表
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, message, 
                ha='center', va='center', fontsize=12, color='red')
        ax.set_axis_off()
        self.canvas.figure = fig
        self.canvas.draw()
        
        # 显示错误消息框
        QMessageBox.critical(self, "错误", message)
