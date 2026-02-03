import numpy as np
import pandas as pd
from scipy.interpolate import interp1d, CubicSpline, PchipInterpolator

class BeamShapeCreator:
    def __init__(self):
        self.raw_x = None
        self.raw_y = None
        self.x_fwhm = None
        self.y_fwhm = None
        self.average_method = "几何平均"  # 默认平均方法
        self.interp_method = "三次样条"   # 默认插值方法
        self.edge_method = "指数衰减"     # 默认边缘处理方法
        
    def calculate_fwhm(self, coords, values):
        """计算半高宽(FWHM)"""
        # 增加插值提高计算精度
        interp = interp1d(coords, values, kind='cubic')
        dense_x = np.linspace(coords.min(), coords.max(), 1000)
        dense_y = interp(dense_x)
        values = dense_y  # 替换为高密度采样数据
        coords = dense_x

        """计算半高宽(FWHM)"""
        max_value = np.max(values)
        if max_value == 0 or np.max(values) < 50:
            return 0.0

        # 找出50%高度的索引
        half_max = max_value * 0.5
        above_half = np.where(values >= half_max)[0]
    
        if len(above_half) < 2:
            return 0.0

        # 确定左右边界
        left_idx = above_half[0]
        right_idx = above_half[-1]

        # 精确边界插值
        def find_edge(x1, x2, y1, y2):
            t = (half_max - y1) / (y2 - y1)
            return x1 + t*(x2 - x1)

        # 左边界插值
        if left_idx > 0:
            left = find_edge(coords[left_idx-1], coords[left_idx], 
                            values[left_idx-1], values[left_idx])
        else:
            left = coords[left_idx]

        # 右边界插值
        if right_idx < len(coords)-1:
            right = find_edge(coords[right_idx], coords[right_idx+1],
                             values[right_idx], values[right_idx+1])
        else:
            right = coords[right_idx]

        return abs(right - left)
        
    @staticmethod
    def validate_and_shift_coordinates(coordinates, values):
        """坐标轴预处理模块"""
        # 检查原始数据有效性
        if any(v < 0 for v in values):
            raise ValueError("输入数据包含负数强度值，无法处理")
        
        # 步骤1：找到峰值位置
        peak_idx = np.argmax(values)
        peak_coord = coordinates[peak_idx]
        
        # 步骤2：将峰值平移到原点（只平移坐标，不改变数值）
        shifted_coords = coordinates - peak_coord
        
        # 步骤3：找出原数据端点
        a, b = coordinates[0], coordinates[-1]  # 原始坐标端点
        offset = min(a, b)  # 新的偏移量基准
        
        # 步骤4：数值平移
        adjusted_values = values - offset
        
        # 数值修正（保证最小值为0）
        adjusted_values = np.where(adjusted_values < 0, 0, adjusted_values)
        return shifted_coords, adjusted_values  # 坐标仅做峰值平移，数值做偏移修正

    def load_and_normalize_data(self, x_path, y_path):
        """加载并预处理数据"""
        # 读取原始数据
        df_x = pd.read_csv(x_path, header=None).dropna().values.T
        df_y = pd.read_csv(y_path, header=None).dropna().values.T
        
        # 应用坐标预处理
        x_coord, x_val = self.validate_and_shift_coordinates(df_x[0], df_x[1])
        y_coord, y_val = self.validate_and_shift_coordinates(df_y[0], df_y[1])

        # 计算FWHM
        self.x_fwhm = self.calculate_fwhm(x_coord, x_val)
        self.y_fwhm = self.calculate_fwhm(y_coord, y_val)
        
        if self.x_fwhm == 0 or self.y_fwhm == 0:
            raise ValueError("无法计算有效FWHM")
        
        # 后续归一化处理
        x_coord, x_val = self.normalize_profile(x_coord, x_val)
        y_coord, y_val = self.normalize_profile(y_coord, y_val)
        
        # 存储原始数据
        self.raw_x = (x_coord, x_val)
        self.raw_y = (y_coord, y_val)
        
        return (x_coord, x_val, y_coord, y_val)

    @staticmethod
    def normalize_profile(coordinates, values):
        """归一化处理"""
        # 找到调整后的最大值
        new_peak_value = np.max(values)
        
        if new_peak_value <= 0:
            raise ValueError("归一化失败：调整后的峰值为非正值")
        
        # 归一化到100%
        normalized_values = (values / new_peak_value) * 100
        return coordinates, normalized_values  # 保持坐标已平移后的状态

    def create_axis_interpolators(self, x_coords, x_vals, y_coords, y_vals, plane_size):
        """创建插值函数"""
        # 扩展数据确保覆盖平面范围
        def extend_axis(orig_coords, orig_vals, boundary):
            """扩展数据点"""
            filtered = pd.DataFrame({
                'coord': orig_coords,
                'val': orig_vals
            }).groupby('coord')['val'].max().reset_index()
        
            # 添加边界点并去重
            ext_coords = np.concatenate([
                [orig_coords.min() - 0.1],  # 仅在左侧向外扩展小量
                filtered['coord'], 
                [orig_coords.max() + 0.1] 
            ])  
            ext_vals = np.concatenate([
                [0.0],  # 左扩展点强度
                filtered['val'],
                [0.0]   # 右扩展点强度
                ])
        
            # 使用最大值合并重复坐标
            ext_df = pd.DataFrame({'coord': ext_coords, 'val': ext_vals})
            ext_df = ext_df.groupby('coord')['val'].max().reset_index().sort_values('coord')
            return ext_df['coord'].values, ext_df['val'].values

        half_size = plane_size / 2
    
        # 处理X轴
        x_coords_ext, x_vals_ext = extend_axis(x_coords, x_vals, half_size)
        
        # 处理Y轴
        y_coords_ext, y_vals_ext = extend_axis(y_coords, y_vals, half_size)
    
        # 根据插值方法创建插值器
        method_map = {
            "三次样条": self._create_cubic_spline,
            "PCHIP保形": self._create_pchip,
            "五次样条": self._create_quintic_spline
        }
        
        if self.interp_method not in method_map:
            raise ValueError(f"不支持的插值方法: {self.interp_method}")
    
        interp_x = method_map[self.interp_method](x_coords_ext, x_vals_ext)
        interp_y = method_map[self.interp_method](y_coords_ext, y_vals_ext)
    
        # 应用缩放校正
        scaled_interp_x = self.create_scaled_interp(interp_x, x_coords_ext, self.x_fwhm)
        scaled_interp_y = self.create_scaled_interp(interp_y, y_coords_ext, self.y_fwhm)
    
        return (scaled_interp_x, x_coords_ext), (scaled_interp_y, y_coords_ext)

    def create_scaled_interp(self, raw_interp, coords, original_fwhm):
        """创建缩放校正后的插值器"""
        test_x = np.linspace(coords[0], coords[-1], 1000)
        test_y = raw_interp(test_x)
        current_fwhm = self.calculate_fwhm(test_x, test_y)

        if current_fwhm <= 0:
            return raw_interp

        scale_factor = original_fwhm / current_fwhm
    
        def final_interp(x):
            scaled_x = x * scale_factor
            return np.where(
                (scaled_x >= coords[0]) & (scaled_x <= coords[-1]),
                raw_interp(scaled_x),
                0.0
            )
        return final_interp

    def generate_asymmetric_grid(self, interp_info_x, interp_info_y, plane_size, step):
        """生成二维光束强度网格"""
        max_l = plane_size / 2
    
        # 生成坐标网格
        coords = np.linspace(-max_l, max_l, int((2 * max_l) / step) + 1, endpoint=True)
        xx, yy = np.meshgrid(coords, coords)
    
        # 获取已缩放的插值器
        (interp_x, _), (interp_y, _) = interp_info_x, interp_info_y
    
        # 计算各方向值
        a_vals = interp_x(xx.ravel()).reshape(xx.shape)
        b_vals = interp_y(yy.ravel()).reshape(yy.shape)
    
        # 根据用户选择的方法合并
        if self.average_method == "几何平均":
            # 几何平均（保证能量守恒）
            z_matrix = np.sqrt(a_vals * b_vals)
        elif self.average_method == "算术平均":
            # 算术平均
            z_matrix = (a_vals + b_vals) / 2
        else:
            # 默认回退到几何平均
            raise ValueError(f"未知的平均方法: {self.average_method}")
    
        # 根据选择的边缘处理方法应用不同的边缘过渡
        if self.edge_method == "指数衰减":
            # 应用指数衰减模式的边缘过渡
            falloff = self.calculate_radial_falloff(xx, yy, max_l)
            result_matrix = z_matrix * falloff
        elif self.edge_method == "z轴下移":
            # 1. 首先应用指数衰减
            falloff = self.calculate_radial_falloff(xx, yy, max_l)
            intermediate_matrix = z_matrix * falloff
            
            # 2. 在这个基础上应用z轴下移
            result_matrix = self.apply_z_shift(intermediate_matrix, max_l)
        else:
            # 没有边缘处理
            result_matrix = z_matrix
        
        return coords, result_matrix
    

    def apply_z_shift(self, z_matrix, max_l):
        """应用z轴下移边缘处理 - 在非零区域边界找到最大值并整体下移"""
        # 找到非零区域的边界索引
        non_zero_mask = z_matrix > 0
        
        if not non_zero_mask.any():
            return z_matrix  # 如果没有非零值直接返回

        # 获取非零区域的行列边界
        rows, cols = np.where(non_zero_mask)
        min_row, max_row = np.min(rows), np.max(rows)
        min_col, max_col = np.min(cols), np.max(cols)
        
        # 提取四个边界的值（包括角点）
        top_edge = z_matrix[min_row, min_col:max_col+1]     # 上边界
        bottom_edge = z_matrix[max_row, min_col:max_col+1]  # 下边界
        left_edge = z_matrix[min_row+1:max_row, min_col]    # 左边界（不含重复的角点）
        right_edge = z_matrix[min_row+1:max_row, max_col]   # 右边界（不含重复的角点）
        
        # 合并所有边界值并找到最大值
        boundary_values = np.concatenate((top_edge, bottom_edge, left_edge, right_edge))
        edge_max = np.max(boundary_values)
        
        # 整体向下平移并处理负值
        shifted_matrix = z_matrix - edge_max
        shifted_matrix[shifted_matrix < 0] = 0.0
        
        return shifted_matrix

    @staticmethod
    def calculate_radial_falloff(xx, yy, half_size):
        """指数衰减模式的边缘过渡"""
        radius = np.sqrt(xx**2 + yy**2)
        norm_radius = radius / half_size  # 归一化到0~1范围
    
        # 使用指数衰减曲线 (调整k值可改变衰减速度)
        k = 3  # 衰减系数，越大衰减越快
        falloff = np.exp(-k * norm_radius) - np.exp(-k)  # 确保边界处平滑到0
    
        # 应用条件过滤
        return np.where(
            (norm_radius <= 1.0),  # 在有效区域内
            np.clip(falloff / (1 - np.exp(-k)), 0.0, 1.0),  # 标准化到0~1区间
            0.0
        )

    @staticmethod
    def calculate_r_squared(original, predicted):
        """计算R方值"""
        ss_res = np.sum((original - predicted)**2)
        ss_tot = np.sum((original - np.mean(original))**2)
        return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    @staticmethod
    def save_as_csv(z_data, coords, output_path):
        """保存CSV文件"""
        x_labels = [f"{x:.4f}" for x in coords]
        y_labels = [f"{y:.4f}" for y in coords[::-1]]
        df = pd.DataFrame(z_data, columns=x_labels, index=y_labels)
        df.index.name = 'y\\x'
        
        # 使用 map 替代被废弃的 applymap
        df = df.round(4).map(lambda x: max(x, 0.0))  # 修正这里
        df.to_csv(output_path)
        
    def _create_cubic_spline(self, coords, values):
        """三次样条插值"""
        return interp1d(
            coords, values,
            kind='cubic',
            fill_value=0.0,
            bounds_error=False
        )

    def _create_pchip(self, coords, values):
        """PCHIP保形插值"""
        interp = PchipInterpolator(coords, values, extrapolate=None)
        return lambda x: np.where( 
            x < coords[0], 0.0,
            np.where(x > coords[-1], 0.0, interp(x))
        )

    def _create_quintic_spline(self, coords, values):
        """五次样条插值（需要scipy>=1.10）"""
        try:
            from scipy.interpolate import make_interp_spline
            # 构建五次样条插值
            spline = make_interp_spline(
                coords, 
                values,
                k=5,  # 五次样条
                bc_type='natural'  # 自然边界条件
            )
            return lambda x: np.where(
                (x >= coords[0]) & (x <= coords[-1]), 
                np.clip(spline(x), 0, None),  
                0.0  # 超出范围返回0
            )
        except ImportError:
            # 提示用户升级SciPy
            raise RuntimeError("五次样条需要SciPy 1.10+")
        except ValueError as ve:
            # 处理数据点不足等问题
            raise ValueError(f"创建五次样条失败: {str(ve)}")
