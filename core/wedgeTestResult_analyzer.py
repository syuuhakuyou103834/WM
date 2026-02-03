import csv
import numpy as np
from collections import defaultdict
from pathlib import Path

import os
import numpy as np
from utils.file_io import get_resource_path

class WedgeTestAnalyzer:

    # 改为动态方法获取路径
    @property
    def REGRESSION_DIR(self):
        regression_dir = get_resource_path("Data/outputs/Regression_Data")
        os.makedirs(regression_dir, exist_ok=True)
        return regression_dir
    
    @property
    def NEW_BEAM_PROFILE_DIR(self):
        new_beam_dir = get_resource_path("Data/outputs/new_BeamShapeProfile")
        os.makedirs(new_beam_dir, exist_ok=True)
        return new_beam_dir

    def __init__(self):
        self.map_wtr = None       # WTR坐标系的95x95阵列
        self.map_tm = None        # TM坐标系的95x95阵列
        self.map_wf = None        # WF薄膜厚度坐标系的稀疏网格
        self.wtr_center = None    # WTR坐标系中心点
        self.coord_tolerance = 0.001  # 坐标匹配容差
        self.beam_peak = None     # 新添加的Beam Peak值

    def load_recipe(self, filepath):
        """加载WedgeTestRecipe文件"""
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            data = []
            
            for row_idx, row in enumerate(reader):
                # 基本校验
                if len(row) < 5:
                    print(f"行 {row_idx+1} 列数不足，已跳过")
                    continue

                # 修正点1：仅使用A列判断第一行
                is_first_row = row[0] == '1'  # 直接判断A列是否为1
                
                # 末行过滤（保持原判断）
                is_last_row = False
                try:
                    b, c, d, e = map(float, row[1:5])
                    is_last_row = all(v == 0 for v in [b, c, d, e])
                except (ValueError, IndexError):  # 列不足或数据错误
                    pass

                # 触发过滤时的日志输出
                if is_first_row:
                    print(f"跳过首行: {row}")
                    continue
                if is_last_row:
                    print(f"跳过末行: {row}")
                    continue

                # 有效数据存储
                if len(row) == 5:
                    data.append(row)
                else:
                    print(f"行 {row_idx+1} 格式异常，已跳过")

            # 强制验证数据量（必须严格符合9025）
            if len(data) != 95*95:
                raise ValueError(f"数据行数异常！预期 9025 行，实际 {len(data)} 行")

            # 强制填充检查（确保二维矩阵无None）
            self.map_wtr = [[None for _ in range(95)] for _ in range(95)]
            try:
                for idx in range(95*95):
                    i, j = divmod(idx, 95)
                    row = data[idx]
                    self.map_wtr[i][j] = {
                        'x': float(row[1]),
                        'y': float(row[3]),
                        'vx': float(row[2]),
                        'vy': float(row[4])
                    }
            except IndexError:
                raise RuntimeError("数据填充时发生越界，请确认二维数组完整填充")

            # 中心点计算添加有效性检查
            valid_cells = [cell for row in self.map_wtr for cell in row if cell]
            x_coords = [cell['x'] for cell in valid_cells]
            y_coords = [cell['y'] for cell in valid_cells]
            
            self.wtr_center = {
                'x': (max(x_coords) + min(x_coords)) / 2,
                'y': (max(y_coords) + min(y_coords)) / 2
            }

            self._generate_tm_mapping()

    def _generate_tm_mapping(self):
        """生成TM坐标系统"""
        self.map_tm = [[None]*95 for _ in range(95)]
        for i in range(95):
            for j in range(95):
                wtr = self.map_wtr[i][j]
                x_tm = wtr['x'] - self.wtr_center['x']
                y_tm = self.wtr_center['y'] - wtr['y']
                self.map_tm[i][j] = {
                    'x_wtr': wtr['x'],
                    'y_wtr': wtr['y'],
                    'x_tm': x_tm,
                    'y_tm': y_tm,
                    'trimming_amount': None,
                    'vy': wtr['vy']
                }

    def load_thickness(self, initial_file, after_file):
        """加载薄膜厚度文件"""
        # 读取initial数据
        initial = self._read_thickness_file(initial_file)
        after = self._read_thickness_file(after_file)
        
        # 确定坐标边界
        x_coords = set()
        y_coords = set()
        for (x, y) in initial.keys():
            x_coords.add(x)
            y_coords.add(y)
        x_list = sorted(x_coords)
        y_list = sorted(y_coords)
        
        # 创建二维网格
        x_min, x_max = min(x_list), max(x_list)
        y_min, y_max = min(y_list), max(y_list)
        x_step = (x_max - x_min) / (len(x_list)-1) if len(x_list)>1 else 0
        y_step = (y_max - y_min) / (len(y_list)-1) if len(y_list)>1 else 0
        
        # 生成WF数组
        self.map_wf = defaultdict(dict)
        for x in np.arange(x_min, x_max + self.coord_tolerance, x_step):
            for y in np.arange(y_min, y_max + self.coord_tolerance, y_step):
                tm = initial.get((round(x,3), round(y,3)), 0) - after.get((round(x,3), round(y,3)), 0)
                self.map_wf[round(x,3)][round(y,3)] = tm

    def _read_thickness_file(self, filepath):
        """读取薄膜厚度文件"""
        data = {}
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # 跳过首行
            for row in reader:
                x = round(float(row[0]), 3)
                y = round(float(row[1]), 3)
                thickness = float(row[2])
                data[(x, y)] = thickness
        return data

    def transfer_trimming_amount(self):
        """将WF的刻蚀量传递到TM阵列"""
        for i in range(95):
            for j in range(95):
                tm_point = self.map_tm[i][j]
                x = round(tm_point['x_tm'], 3)
                y = round(tm_point['y_tm'], 3)
                
                # 在WF中找到对应的坐标
                found = False
                for wf_x in self.map_wf:
                    if abs(wf_x - x) < self.coord_tolerance:
                        for wf_y in self.map_wf[wf_x]:
                            if abs(wf_y - y) < self.coord_tolerance:
                                tm_point['trimming_amount'] = self.map_wf[wf_x][wf_y]
                                found = True
                                break
                        if found: break

    def calculate_slope(self):
        """计算回归斜率"""
        sum_xy = 0
        sum_xx = 0
        valid_points = 0

        for row in self.map_tm:
            for point in row:
                if (point['trimming_amount'] is not None
                    and point['trimming_amount'] != 0
                    and point['vy'] != 0):

                    x = 1 / point['vy']
                    y = point['trimming_amount']

                    sum_xy += x * y
                    sum_xx += x ** 2
                    valid_points +=1

        if valid_points < 2:
            raise ValueError("有效数据点不足")

        slope = sum_xy / sum_xx
        return slope

    def get_regression_data(self):
        """获取回归分析的数据点"""
        x_data = []
        y_data = []

        for row in self.map_tm:
            for point in row:
                if (point['trimming_amount'] is not None
                    and point['trimming_amount'] != 0
                    and point['vy'] != 0):

                    x = 1 / point['vy']
                    y = point['trimming_amount']

                    x_data.append(x)
                    y_data.append(y)

        return x_data, y_data

    def export_regression_data(self, output_dir: Path = None) -> Path:
        """导出回归分析数据""" 
        if not output_dir:
            output_dir = self.REGRESSION_DIR
        
        # 确保目录存在
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建文件名
        output_path = output_dir / "regression_data.csv"
        
        # 收集有效数据点
        data_points = []
        for row in self.map_tm:
            for point in row:
                if point['trimming_amount'] is not None and point['vy'] != 0 and point['trimming_amount'] != 0:
                    data_points.append((
                        1 / point['vy'],         # X: 1/vy
                        point['trimming_amount'] # Y: TM
                    ))

        # 写入CSV文件
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["1/vy", "Trimming_Amount"])
            writer.writerows(data_points)
        
        print(f"成功导出 {len(data_points)} 个数据点到 {output_path}")
        return output_path

    def calculate_beam_peak(self, k_factor: float) -> float:
        """计算Beam Peak值"""
        slope = self.calculate_slope()
        self.beam_peak = k_factor * slope
        return self.beam_peak

    def process_beam_profile(self, input_file: Path) -> Path:
        """
        处理Beam Profile文件：找出最大值，应用比例系数，保存新文件
        """
        if self.beam_peak is None:
            raise ValueError("Beam Peak值未计算，请先执行分析")

        # 读取Beam Profile数据
        with open(input_file, 'r') as f:
            reader = csv.reader(f)
            data = []
            for row in reader:
                # 只添加有效数字行
                valid_row = []
                for item in row:
                    try:
                        # 尝试转换为float
                        num = float(item)
                        valid_row.append(num)
                    except ValueError:
                        # 处理可能的空值或无效数据
                        valid_row.append(0.0)
                data.append(valid_row)

        # 转换为numpy数组并找出最大值
        array_2d = np.array(data)
        max_value = np.max(array_2d)

        if max_value <= 0:
            raise ValueError("Beam Profile最大值无效")

        # 计算比例系数
        scaling_factor = self.beam_peak / max_value

        # 应用比例系数并转换为新数组
        new_array = array_2d * scaling_factor

        # 创建新文件名和路径
        output_dir = self.NEW_BEAM_PROFILE_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"New_{input_file.name}"

        # 写入新文件，格式为31x31的CSV，保留8位小数
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            for row in new_array:
                # 每行格式化8位小数
                formatted_row = [f"{x:.8f}" for x in row]
                writer.writerow(formatted_row)

        return output_file

    def calculate_beam_y_integration(self, input_file: Path) -> tuple:
        """
        计算Beam Profile沿y轴积分

        Args:
            input_file: Beam Profile CSV文件路径

        Returns:
            tuple: (x坐标列表, y轴积分值列表, 总积分值)
        """
        # 读取Beam Profile数据
        with open(input_file, 'r') as f:
            reader = csv.reader(f)
            data = []
            for row in reader:
                # 只添加有效数字行
                valid_row = []
                for item in row:
                    try:
                        # 尝试转换为float
                        num = float(item)
                        valid_row.append(num)
                    except ValueError:
                        # 处理可能的空值或无效数据
                        valid_row.append(0.0)
                data.append(valid_row)

        # 转换为numpy数组
        array_2d = np.array(data)

        # 验证数组尺寸（应该是31x31）
        if array_2d.shape != (31, 31):
            raise ValueError(f"Beam Profile文件尺寸错误，期望31x31，实际{array_2d.shape}")

        # 计算每一列的和（沿y轴积分）
        column_sums = np.sum(array_2d, axis=0)

        # 生成x坐标（-15mm到+15mm，步长1mm）
        x_coords = np.arange(-15, 16)

        # 计算总积分值（所有列的和再次求和）
        total_integration = np.sum(column_sums)

        return x_coords.tolist(), column_sums.tolist(), total_integration

# 使用示例
if __name__ == "__main__":
    analyzer = WedgeTestAnalyzer()
    
    # Step 1: 加载Recipe文件
    analyzer.load_recipe("WedgeTestRecipe.csv")
    
    # Step 2: 加载厚度数据
    analyzer.load_thickness("THK_initial.csv", "THK_after.csv")
    
    # Step 3: 传递刻蚀量
    analyzer.transfer_trimming_amount()
    
    # Step 4: 计算斜率
    try:
        slope = analyzer.calculate_slope()
        beam_peak = analyzer.calculate_beam_peak(1.0)
        print(f"回归斜率: {slope:.6f}")
        print(f"Beam Peak: {beam_peak:.6f}")
        
        # Step 5: 假设有一个Beam Profile文件
        beam_profile = "beam.csv"
        if Path(beam_profile).exists():
            new_profile = analyzer.process_beam_profile(beam_profile)
            print(f"已创建新的Beam Profile: {new_profile}")
    except ValueError as e:
        print(e)
