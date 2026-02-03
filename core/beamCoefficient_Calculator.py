import csv
import numpy as np
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QMessageBox
import pandas as pd

class BeamCoefficientCalculator:
    def __init__(self):
        # 初始化变量
        self.set_values = []
        self.pre_values = []
        self.post_values = []
        self.actual_values = []
        self.slope = None
        self.r_squared = None
        self.fig = None  # 保存图表对象
        self.simulation_file_path = None
        self.target_value = 0.0
        
        # 创建默认图表
        self._create_empty_plot()
    
    def _create_empty_plot(self):
        """创建空图表"""
        self.fig = Figure(figsize=(8, 6))
        self.fig.suptitle('请先加载数据并计算系数')
        ax = self.fig.add_subplot(111)
        ax.text(0.5, 0.5, "数据未加载", 
                ha='center', va='center', fontsize=12)
        ax.set_axis_off()
    
    def process_simulation_file(self, simulation_path, target_value):
        """
        处理用户选择的simulation文件
        """
        if not simulation_path:
            return None
        
        try:
            # 使用pandas读取文件，更简单处理CSV
            df = pd.read_csv(simulation_path)
            
            # 验证文件至少有3列
            if df.shape[1] < 3:
                raise ValueError("Simulation文件必须至少包含3列数据")
            
            # 提取第三列数据并减去目标值
            self.set_values = (df.iloc[:, 2] - float(target_value)).values.tolist()
            self.simulation_file_path = simulation_path
            self.target_value = float(target_value)
            
            return True
        except Exception as e:
            error_msg = f"处理Simulation文件失败: {str(e)}"
            self._show_error(error_msg)
            return False
        
    def _load_thickness_file(self, file_path, target_list):
        """读取厚度文件，只提取第三列数据"""
        target_list.clear()  # 清空现有数据
        
        try:
            # 使用pandas读取文件
            df = pd.read_csv(file_path)
            
            # 验证文件至少有3列
            if df.shape[1] < 3:
                raise ValueError("文件必须至少包含3列数据")
            
            # 提取第三列数据
            target_list.extend(df.iloc[:, 2].values.tolist())
            return True
        except Exception as e:
            error_msg = f"读取厚度文件失败: {str(e)}"
            self._show_error(error_msg)
            return False
    
    def calculate_coefficient(self, initial_path, after_path):
        """计算beam系数"""
        if not initial_path or not after_path:
            self._show_error("请选择初始厚度和刻蚀后厚度文件")
            return False
        
        try:
            # 1. 读取初始厚度文件
            if not self._load_thickness_file(initial_path, self.pre_values):
                return False
            
            # 2. 读取刻蚀后厚度文件
            if not self._load_thickness_file(after_path, self.post_values):
                return False
            
            # 3. 检查数据长度是否一致
            if len(self.pre_values) != len(self.post_values):
                raise ValueError(f"初始厚度文件长度({len(self.pre_values)})与刻蚀后厚度文件长度({len(self.post_values)})不匹配")
            
            # 4. 检查set_values长度
            if len(self.set_values) != len(self.pre_values):
                self._show_warning(
                    f"Simulation文件长度({len(self.set_values)})与厚度文件长度({len(self.pre_values)})不匹配\n"
                    f"使用较小长度进行截断计算"
                )
                min_length = min(len(self.set_values), len(self.pre_values))
                self.set_values = self.set_values[:min_length]
                self.pre_values = self.pre_values[:min_length]
                self.post_values = self.post_values[:min_length]
            
            # 5. 计算actual_value = pre - post
            self.actual_values = np.array(self.pre_values) - np.array(self.post_values)
            
            # 6. 确保有数据用于计算
            if len(self.set_values) < 1 or len(self.actual_values) < 1:
                raise ValueError("没有足够的数据用于计算")
            
            # 7. 线性回归 y = q*x (无需截距)
            x = np.array(self.set_values).flatten()
            y = self.actual_values.flatten()
            
            # 计算斜率 q = sum(x*y) / sum(x^2)
            numerator = np.sum(x * y)
            denominator = np.sum(x * x)
            if denominator == 0:
                raise ValueError("分母为0，无法计算斜率")
            
            self.slope = numerator / denominator
            
            # 8. 计算R平方
            y_pred = self.slope * x
            ss_res = np.sum((y - y_pred)**2)
            ss_tot = np.sum((y - np.mean(y))**2)
            if ss_tot < 1e-10:  # 避免除以0
                self.r_squared = 1.0
            else:
                self.r_squared = 1 - (ss_res / ss_tot)
            
            return True
        except Exception as e:
            error_msg = f"计算系数失败: {str(e)}"
            self._show_error(error_msg)
            return False
    
    def plot_data(self):
        """创建散点图和回归线"""
        try:
            # 如果数据不足，返回空图表
            if len(self.set_values) == 0 or len(self.actual_values) == 0 or self.slope is None:
                self._create_empty_plot()
                return self.fig
            
            self.fig = Figure(figsize=(8, 6))
            ax = self.fig.add_subplot(111)
            
            # 绘制散点图
            ax.scatter(
                self.set_values, 
                self.actual_values, 
                alpha=0.7,
                label='实测点'
            )
            
            # 绘制回归线
            x_min = min(self.set_values)
            x_max = max(self.set_values)
            y_min = self.slope * x_min
            y_max = self.slope * x_max
            ax.plot(
                [x_min, x_max], [y_min, y_max], 
                color='red', 
                linestyle='-',
                linewidth=1.5,
                label=f'拟合直线 (y={self.slope:.4f}x, R²={self.r_squared:.4f})'
            )
            
            ax.set_title('实际变化值 vs. 设定变化值')
            ax.set_xlabel(f'设定变化值 (Simulation目标值: {self.target_value:.2f})')
            ax.set_ylabel('实际变化值 (初始厚度 - 刻蚀后厚度)')
            ax.grid(True, linestyle='--', alpha=0.5)
            ax.legend()
            
            return self.fig
        except Exception as e:
            error_msg = f"生成图表失败: {str(e)}"
            self._show_error(error_msg)
            return self._create_empty_plot()
    
    def _show_error(self, message):
        """显示错误消息"""
        print(f"错误: {message}")
    
    def _show_warning(self, message):
        """显示警告消息"""
        print(f"警告: {message}")
