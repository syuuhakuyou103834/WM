import csv
from pathlib import Path
from typing import List, Tuple, Optional  # 添加 Optional
import os
from utils.file_io import validate_path, ensure_dir
from utils.file_io import get_resource_path, validate_path

class RecipeCenterAdjuster:
    # 列索引常量
    COL_NUM = 5  # 总列数
    COL_X = 1    # X坐标列
    COL_Y = 3    # Y坐标列
    
    
    def __init__(self):
        # 修改为使用动态路径
        input_dir = get_resource_path("Data/inputs/WedgeTestRecipe")
        output_dir = get_resource_path("Data/outputs/new_WedgeTestRecipe")
        
        # 确保目录存在
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        self.input_dir = input_dir
        self.output_dir = output_dir
    
    @staticmethod
    def get_original_center(input_path: Path) -> Tuple[float, float]:
        """获取文件的原始中心点 - 静态方法，便于UI直接调用"""
        header, body_lines, footer = RecipeCenterAdjuster._read_recipe(input_path)
        return RecipeCenterAdjuster._calculate_original_center(body_lines)
        
    @staticmethod
    def _read_recipe(file_path: Path) -> Tuple[List, List, List]:
        """读取Recipe文件并验证格式"""
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            raw_lines = [row for row in reader]
        
        if len(raw_lines) < 3:
            raise ValueError("文件至少需要包含首行、一个数据行、末行")

        header = raw_lines[0]
        footer = raw_lines[-1]
        body_lines = raw_lines[1:-1]

        # 首行验证
        if len(header) < RecipeCenterAdjuster.COL_NUM or not header[0].isdigit():
            raise ValueError(f"首行格式错误: {header}")

        #### 修改部分：放宽末行验证 ####
        # 末行验证 - 只需要检查第2列到第5列是否全为0
        if len(footer) < RecipeCenterAdjuster.COL_NUM:
            raise ValueError(f"末行列数不足: {footer}，应为{RecipeCenterAdjuster.COL_NUM}列")
        
        # 检查第2列到第5列是否全为0（索引1到4）
        if not all(v.strip() == '0' for v in footer[1:RecipeCenterAdjuster.COL_NUM]):
            raise ValueError(f"末行第2-5列必须为0: {footer[1:RecipeCenterAdjuster.COL_NUM]}")
        ##############################

        # 数据行验证 - 保持不变
        for idx, row in enumerate(body_lines, start=2):
            if len(row) < RecipeCenterAdjuster.COL_NUM:
                raise ValueError(f"第{idx+1}行列数不足: {row}，应为{RecipeCenterAdjuster.COL_NUM}列")
            try:
                float(row[RecipeCenterAdjuster.COL_X])
                float(row[RecipeCenterAdjuster.COL_Y])
            except ValueError:
                raise ValueError(f"第{idx+1}行坐标值无效: X={row[1]}, Y={row[3]}")

        return header, body_lines, footer

    @staticmethod
    def _calculate_original_center(body_lines) -> Tuple[float, float]:
        """计算原始中心点坐标"""
        try:
            x_coords = [float(row[RecipeCenterAdjuster.COL_X]) for row in body_lines]
            y_coords = [float(row[RecipeCenterAdjuster.COL_Y]) for row in body_lines]
            return (
                (max(x_coords) + min(x_coords)) / 2,
                (max(y_coords) + min(y_coords)) / 2
            )
        except (IndexError, ValueError) as e:
            raise RuntimeError(f"中心点计算错误: {str(e)}")

    def adjust_single_file(self, input_path: Path, output_path: Path, 
                         delta_x: float, delta_y: float) -> None:
        """调整单个配方文件"""
        header, body_lines, footer = self._read_recipe(input_path)
        processed_body = self._process_body(body_lines, delta_x, delta_y)
        self._write_output(output_path, header, processed_body, footer)
    
    @staticmethod
    def _process_body(body_lines, delta_x, delta_y):
        """处理文件主体数据"""
        processed = []
        for row in body_lines:
            try:
                row = row[:]  # 创建副本
                # 更新X坐标
                x_val = round(
                    float(row[RecipeCenterAdjuster.COL_X]) + delta_x, 
                    8
                )
                row[RecipeCenterAdjuster.COL_X] = f"{x_val:.8f}"
                
                # 更新Y坐标
                y_val = round(
                    float(row[RecipeCenterAdjuster.COL_Y]) + delta_y, 
                    8
                )
                row[RecipeCenterAdjuster.COL_Y] = f"{y_val:.8f}"
                
                processed.append(row)
            except (ValueError, IndexError) as e:
                print(f"处理行时出错: {row} - {str(e)}")
        return processed

    @staticmethod
    def _write_output(output_path, header, processed_body, footer):
        """写入处理后的文件 - 修改为创建目录如果不存在"""
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 写入文件
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(processed_body)
            writer.writerow(footer)

# 测试入口
if __name__ == "__main__":
    adjuster = RecipeCenterAdjuster()
    # 注意缺少 process_all 
    # adjuster.process_all()
