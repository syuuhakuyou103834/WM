from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QGridLayout, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from core.center_adjuster import RecipeCenterAdjuster
from pathlib import Path

class CenterAdjustUI(QWidget):
    def __init__(self):
        super().__init__()
        self.adjuster = RecipeCenterAdjuster()
        self.recipe_file = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        main_layout = QGridLayout()
        
        # 文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QFormLayout()
        
        self.recipe_label = QLabel("未选择Recipe文件")
        self.select_button = QPushButton("选择Recipe")
        self.select_button.clicked.connect(self.select_recipe)
        
        file_layout.addRow("Recipe文件:", self.recipe_label)
        file_layout.addRow(self.select_button)
        file_group.setLayout(file_layout)
        
        # 中心点设置区域
        center_group = QGroupBox("中心点设置")
        center_layout = QFormLayout()
        
        self.original_x = QLineEdit()
        self.original_x.setReadOnly(True)
        center_layout.addRow("原始中心 X:", self.original_x)
        
        self.original_y = QLineEdit()
        self.original_y.setReadOnly(True)
        center_layout.addRow("原始中心 Y:", self.original_y)
        
        self.new_x = QLineEdit()
        self.new_x.setPlaceholderText("输入新X坐标")
        center_layout.addRow("新中心 X:", self.new_x)
        
        self.new_y = QLineEdit()
        self.new_y.setPlaceholderText("输入新Y坐标")
        center_layout.addRow("新中心 Y:", self.new_y)
        
        self.calculate_button = QPushButton("计算偏移量")
        self.calculate_button.clicked.connect(self.calculate_offset)
        center_layout.addRow(self.calculate_button)
        
        self.delta_x = QLineEdit()
        self.delta_x.setReadOnly(True)
        center_layout.addRow("偏移量 ΔX:", self.delta_x)
        
        self.delta_y = QLineEdit()
        self.delta_y.setReadOnly(True)
        center_layout.addRow("偏移量 ΔY:", self.delta_y)
        
        center_group.setLayout(center_layout)
        
        # 操作按钮
        self.execute_button = QPushButton("执行调整")
        self.execute_button.clicked.connect(self.execute_adjustment)
        self.execute_button.setEnabled(False)
        
        main_layout.addWidget(file_group, 0, 0)
        main_layout.addWidget(center_group, 0, 1)
        main_layout.addWidget(self.execute_button, 1, 0, 1, 2)
        
        self.setLayout(main_layout)
    
    def set_recipe_file(self, file_path):
        """设置并显示所选的Recipe文件"""
        self.recipe_file = file_path
        self.recipe_label.setText(file_path)
        self._load_original_center()
    
    def select_recipe(self):
        """选择Recipe文件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Recipe文件", "", "CSV Files (*.csv)", options=options)
        
        if file_path:
            self.set_recipe_file(file_path)
    
    def _load_original_center(self):
        """加载原始中心点坐标"""
        if not self.recipe_file:
            return
            
        try:
            # 使用静态方法获取原始中心点
            original_x, original_y = RecipeCenterAdjuster.get_original_center(Path(self.recipe_file))
            self.original_x.setText(f"{original_x:.8f}")
            self.original_y.setText(f"{original_y:.8f}")
        except Exception as e:
            error_msg = f"加载原始中心点失败: {str(e)}"
            self.execute_button.setEnabled(False)
            self._show_error(error_msg)
    
    def _show_error(self, message):
        """显示错误信息"""
        QMessageBox.critical(
            self, 
            "错误", 
            message,
            QMessageBox.Ok
        )
    
    def calculate_offset(self):
        """计算偏移量"""
        if not self.recipe_file or not self.new_x.text() or not self.new_y.text():
            return
            
        try:
            # 获取原始中心点
            original_x = float(self.original_x.text())
            original_y = float(self.original_y.text())
            
            # 获取新中心点
            new_x = float(self.new_x.text())
            new_y = float(self.new_y.text())
            
            # 计算偏移量
            delta_x = new_x - original_x
            delta_y = new_y - original_y
            
            self.delta_x.setText(f"{delta_x:.8f}")
            self.delta_y.setText(f"{delta_y:.8f}")
            self.execute_button.setEnabled(True)
        except ValueError:
            self._show_error("请输入有效的坐标值")
            self.delta_x.setText("错误")
            self.delta_y.setText("错误")
            self.execute_button.setEnabled(False)
    
    def execute_adjustment(self):
        """执行中心点调整"""
        if not self.recipe_file:
            return
            
        try:
            # 获取状态栏的引用
            if hasattr(self, "parent") and hasattr(self.parent(), "window") and hasattr(self.parent().window(), "status_bar"):
                status_bar = self.parent().window().status_bar
            else:
                status_bar = None
            
            # 生成输出文件名
            original_name = Path(self.recipe_file).name
            output_path = self.adjuster.output_dir / f"adjusted_{original_name}"
            
            # 获取偏移量
            delta_x = float(self.delta_x.text())
            delta_y = float(self.delta_y.text())

            # 执行调整
            self.adjuster.adjust_single_file(Path(self.recipe_file), output_path, delta_x, delta_y)
            
            # 显示成功消息
            success_msg = f"已生成调整后的Recipe: {output_path}"
            if status_bar:
                status_bar.showMessage(success_msg)
            
            # 显示成功弹窗
            QMessageBox.information(
                self, 
                "调整成功", 
                f"新Recipe文件已生成在:\n{output_path}",
                QMessageBox.Ok
            )
                
            # 重新加载原始中心
            self._load_original_center()
        except Exception as e:
            error_msg = f"执行调整失败: {str(e)}"
            self._show_error(error_msg)
            
            # 在状态栏显示错误
            if status_bar:
                status_bar.showMessage(error_msg)
