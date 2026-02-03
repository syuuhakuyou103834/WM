import numpy as np
import pandas as pd
from scipy.interpolate import griddata
import logging
import matplotlib.pyplot as plt

logger = logging.getLogger('BeamSpotTest')

class BeamSpotTestProcessor:
    def __init__(self):
        self.original_df = None
        self.X = None
        self.Y = None
        self.adjusted_X = None
        self.adjusted_Y = None
        self.thickness = None
        self.etching_ability = None
        self.radius = 0.0
        self.thk_max = 0.0
        self.thk_min = 0.0
        self.peak_offset = (0.0, 0.0)
        self.original_center = (0.0, 0.0)
        self.max_etching_position = (0.0, 0.0)
        self.background_thickness = None
        self.calculated_background = None  # 新增：试差法计算出的背景厚度

    def load_and_process(self, file_path, target_radius=None):
        """加载并预处理厚度数据"""
        try:
            logger.info(f"加载厚度文件: {file_path}")
            self._load_data(file_path)
            
            logger.info("识别并记录原始中心点...")
            self._identify_original_center()
            
            # 首先使用厚度最大值作为初始背景厚度
            self.background_thickness = self.thk_max
            logger.info(f"初始背景厚度: {self.background_thickness:.2f} nm")
            self._calculate_etching_ability()
            
            logger.info("将整个数据移动使最大值在(0,0)...")
            self._move_max_to_center()
            
            logger.info("计算初始蚀刻能力半径...")
            self._calculate_etching_radius()
            
            # 如果提供了目标有效半径，通过试差法计算所需背景厚度
            if target_radius is not None:
                logger.info(f"目标有效半径: {target_radius:.2f} mm")
                self.calculated_background = self._find_background_for_radius(target_radius)
                logger.info(f"计算得到的背景厚度: {self.calculated_background:.2f} nm")
                
                # 使用计算出的背景厚度重新计算蚀刻能力
                self.background_thickness = self.calculated_background
                self._calculate_etching_ability()
                self._calculate_etching_radius()
            
            logger.info("插值并生成网格数据...")
            contour_data, surface_data = self._interpolate_data()
            
            return contour_data, surface_data
            
        except Exception as e:
            logger.exception(f"处理失败: {str(e)}")
            raise
    
    def _load_data(self, file_path):
        """加载厚度数据文件"""
        self.original_df = pd.read_csv(file_path)
        
        if len(self.original_df) != 961:
            raise ValueError(f"文件应包含961行数据，实际有{len(self.original_df)}行")
        
        columns = self.original_df.columns.tolist()
        if len(columns) < 3:
            raise ValueError(f"文件应包含至少3列数据，实际有{len(columns)}列")
        
        self.X = self.original_df.iloc[:, 0].values.astype(float)
        self.Y = self.original_df.iloc[:, 1].values.astype(float)
        self.thickness = self.original_df.iloc[:, 2].values.astype(float)
        
        # 计算厚度范围
        self.thk_max = np.max(self.thickness)
        self.thk_min = np.min(self.thickness)
        
        # 初始化调整后坐标
        self.adjusted_X = self.X.copy()
        self.adjusted_Y = self.Y.copy()
    
    def _identify_original_center(self):
        """识别原始数据中心的坐标位置"""
        center_idx = 480
        
        if center_idx >= len(self.X):
            raise ValueError(f"索引{center_idx}超出数据范围")
        
        self.original_center = (self.X[center_idx], self.Y[center_idx])
        logger.info(f"原始数据中心点坐标: ({self.original_center[0]}, {self.original_center[1]})")
    
    def _calculate_etching_ability(self):
        """计算蚀刻能力数据并定位最大值"""
        # 计算蚀刻能力
        self.etching_ability = self.background_thickness - self.thickness
        
        # 将所有小于0的值设为0
        self.etching_ability = np.maximum(self.etching_ability, 0)
        
        # 找到蚀刻能力最大值的原始位置
        max_idx = np.argmax(self.etching_ability)
        self.max_etching_position = (self.X[max_idx], self.Y[max_idx])
        max_val = self.etching_ability[max_idx]
        
        logger.info(f"蚀刻能力最大值在原始位置: ({self.max_etching_position[0]}, {self.max_etching_position[1]}), 值: {max_val:.3f}")
    
    def _move_max_to_center(self):
        """将整个数据集移动，使蚀刻能力最大值点在(0,0)"""
        max_x, max_y = self.max_etching_position
        
        if max_x == 0 and max_y == 0:
            logger.info("最大值已在(0,0)，无需移动")
            return
        
        logger.info(f"移动整个数据集: X偏移: {-max_x:.3f}mm, Y偏移: {-max_y:.3f}mm")
        
        self.adjusted_X = self.X - max_x
        self.adjusted_Y = self.Y - max_y
        
    def _calculate_etching_radius(self):
        """计算蚀刻能力有效半径"""
        distances = np.sqrt(self.adjusted_X**2 + self.adjusted_Y**2)
        
        low_etching_mask = (self.etching_ability < max(self.etching_ability)*0.01) & (self.etching_ability > 0)
        #low_etching_mask = (self.etching_ability < 0.15) & (self.etching_ability > 0)
        low_etching_distances = distances[low_etching_mask]
        
        if len(low_etching_distances) == 0:
            logger.warning("未找到蚀刻能力<0.01的点")
            self.radius = 0.0
        else:
            # 计算有效半径
            self.radius = np.mean(low_etching_distances)
            logger.info(f"蚀刻能力有效半径: {self.radius:.2f} mm")
    
    def _find_background_for_radius(self, target_radius, max_iterations=100, tolerance=0.01):
        """
        通过试差法找到达到目标有效半径所需的背景厚度
        
        Args:
            target_radius: 目标有效半径 (mm)
            max_iterations: 最大迭代次数
            tolerance: 目标半径误差容限 (mm)
        
        Returns:
            计算出的背景厚度 (nm)
        """
        # 保存原始背景厚度和蚀刻能力
        original_background = self.background_thickness
        original_etching_ability = self.etching_ability.copy()
        
        # 初始步长设定 (nm)
        step_size = 1
        current_background = original_background
        best_background = current_background
        best_radius = self.radius
        min_error = abs(best_radius - target_radius)
        
        logger.info(f"开始试差法计算, 初始有效半径: {self.radius:.2f} mm, 目标: {target_radius:.2f} mm")
        
        # 迭代方向 (1 = 增加背景厚度, -1 = 减少背景厚度)
        direction = 0
        
        for i in range(max_iterations):
            # 计算当前误差
            current_error = abs(self.radius - target_radius)
            
            # 检查是否达到目标
            if current_error <= tolerance:
                logger.info(f"迭代收敛 ({i+1}/{max_iterations}), 目标半径: {target_radius:.2f} mm, 当前半径: {self.radius:.2f} mm")
                logger.info(f"计算出的背景厚度: {current_background:.2f} nm")
                break
            
            # 确定方向 (第一次迭代需要确定方向)
            if direction == 0:
                # 修复错误: 增加背景厚度会使半径变大，减小背景厚度会使半径变小
                if self.radius < target_radius:
                    # 当前有效半径小于目标，需要增大背景厚度（使半径变大）
                    direction = 1
                    logger.info("设定迭代方向: 增大背景厚度（当前半径小于目标）")
                else:
                    # 当前有效半径大于目标，需要减小背景厚度（使半径变小）
                    direction = -1
                    logger.info("设定迭代方向: 减小背景厚度（当前半径大于目标）")
            
            # 在接近目标时减小步长
            if step_size > 0.01 and current_error < 0.5:
                step_size = 0.01
                logger.info(f"减小步长至 {step_size:.2f} nm")
            
            # 更新背景厚度
            prev_background = current_background
            current_background = prev_background + direction * step_size
            
            # 确保背景厚度在合理范围内 (大于最小值)
            if current_background < self.thk_min:
                logger.warning(f"背景厚度已达最小值阈值 ({self.thk_min:.2f} nm)，停止迭代")
                break
            
            # 重新计算蚀刻能力和有效半径
            self.background_thickness = current_background
            self._calculate_etching_ability()
            self._calculate_etching_radius()
            
            # 记录最佳值
            if abs(self.radius - target_radius) < min_error:
                best_background = current_background
                best_radius = self.radius
                min_error = abs(best_radius - target_radius)
            
            logger.info(f"迭代 {i+1}: 背景厚度={current_background:.2f} nm, 有效半径={self.radius:.2f} mm, 目标误差={current_error:.4f} mm, 最佳误差={min_error:.4f} mm")
            
            # 检查是否出现误差增大
            if abs(self.radius - target_radius) > min_error and i > 15:
                # 恢复到最佳值
                logger.info(f"误差增大, 使用最佳背景厚度: {best_background:.2f} nm (最佳误差={min_error:.4f} mm)")
                self.background_thickness = best_background
                self._calculate_etching_ability()
                self._calculate_etching_radius()
                return best_background
        else:
            logger.warning(f"达到最大迭代次数 ({max_iterations}), 尚未完全收敛，最佳背景厚度: {best_background:.2f} nm, 有效半径: {best_radius:.2f} mm")
            logger.info(f"目标有效半径: {target_radius:.2f} mm, 当前有效半径: {best_radius:.2f} mm (误差: {abs(best_radius - target_radius):.4f} mm)")
            
            # 恢复到最佳值
            self.background_thickness = best_background
            self._calculate_etching_ability()
            self._calculate_etching_radius()
        
        return current_background
    
    def _interpolate_data(self):
        """插值生成高分辨率网格数据"""
        min_coord = -15
        max_coord = 15
        grid_step = 0.1
        grid_points = int((max_coord - min_coord) / grid_step) + 1
        
        grid_x, grid_y = np.mgrid[
            min_coord:max_coord:complex(0, grid_points),
            min_coord:max_coord:complex(0, grid_points)
        ]
        
        try:
            grid_z = griddata(
                (self.adjusted_X, self.adjusted_Y),
                self.etching_ability, 
                (grid_x, grid_y), 
                method='cubic',
                fill_value=0.0
            )
        except Exception as e:
            logger.error(f"立方插值失败: {str(e)}，尝试线性插值")
            grid_z = griddata(
                (self.adjusted_X, self.adjusted_Y),
                self.etching_ability,
                (grid_x, grid_y),
                method='linear',
                fill_value=0.0
            )
        
        # 确保所有插值点为非负值
        grid_z = np.maximum(grid_z, 0)
        
        # 准备图表数据
        contour_data = {
            'grid_x': grid_x,
            'grid_y': grid_y,
            'grid_z': grid_z,
            'min_coord': min_coord,
            'max_coord': max_coord
        }
        
        surface_data = {
            'x_flat': grid_x.flatten(),
            'y_flat': grid_y.flatten(),
            'z_flat': grid_z.flatten(),
            'grid_shape': grid_z.shape
        }
        
        return contour_data, surface_data
