import pandas as pd
import numpy as np
from pathlib import Path
import os

def flatten_baseline(df, coord_col, value_col):
    """
    通过端点连线校正基线，使两侧端点归零
    
    原理：根据左右端点的值计算基准线，然后从所有点中减去基准值
    
    参数:
    df (pd.DataFrame): 输入数据
    coord_col (str): 坐标列名 (如'X')
    value_col (str): 值列名 (如'Trimmed_Thickness')
    
    返回:
    pd.DataFrame: 基线校正后的数据
    """
    # 获取首尾端点坐标
    start_x = df[coord_col].iloc[0]
    end_x = df[coord_col].iloc[-1]
    start_y = df[value_col].iloc[0]
    end_y = df[value_col].iloc[-1]
    
    # 检查数据是否合理
    if start_x == end_x:
        raise ValueError(f"坐标列 {coord_col} 的首尾值相同，无法计算基线")
    
    # 计算基准线的斜率和截距
    slope = (end_y - start_y) / (end_x - start_x)
    intercept = start_y - slope * start_x
    
    # 计算每个点的基准值并校正
    base_value = slope * df[coord_col] + intercept
    df[value_col] = df[value_col] - base_value
    
    # 确保端点精确归零
    df[value_col].iloc[0] = 0.0
    df[value_col].iloc[-1] = 0.0
    
    # 非负化处理（按需可选）
    # df[value_col] = np.maximum(df[value_col], 0.0)
    
    return df

def process_and_save_outputs(initial_file, after_file, output_base_dir):
    """
    处理初始和扫描后文件，生成刻蚀量数据和截面文件
    
    参数:
    initial_file (str): 初始膜厚文件路径
    after_file (str): 扫描后膜厚文件路径
    output_base_dir (str): 输出基础目录
    
    返回:
    tuple: (trimming_thk_path, x_section_path, y_section_path) 三个输出文件的路径
    """
    # 创建输出目录
    output_dir = Path(output_base_dir) / "Data_processor"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 读取数据文件（保留原始列名和索引）
    initial_df = pd.read_csv(initial_file)
    after_df = pd.read_csv(after_file)
    
    # 数据验证 - 确保两个文件行数一致
    if len(initial_df) != len(after_df):
        raise ValueError("初始文件和扫描后文件数据行数不一致")
    
    # === 步骤1: 计算刻蚀量 ===
    # 自动判断厚度列名称
    thickness_col = None
    possible_names = ['Thickness(nm)', 'Thickness', '厚度', '膜厚']
    
    for name in possible_names:
        if name in initial_df.columns and name in after_df.columns:
            thickness_col = name
            break
    
    if not thickness_col:
        # 如果找不到标准列名，使用第三列
        if len(initial_df.columns) >= 3 and len(after_df.columns) >= 3:
            thickness_col = initial_df.columns[2]
        else:
            raise ValueError("无法识别厚度数据列")
    
    # 计算刻蚀量并保留原始坐标
    initial_df['Trimmed_Thickness'] = initial_df[thickness_col] - after_df[thickness_col]
    
    # 保存刻蚀量文件
    trimming_thk_path = output_dir / "trimming_thk.csv"
    initial_df.to_csv(trimming_thk_path, index=False)
    
    # === 步骤2: 提取X截面数据 (y=40, x从-15到15) ===
    # 直接根据坐标范围提取数据 (-15 ≤ x ≤ 15, y=40)
    x_section_df = initial_df[
        (initial_df['X'].between(-15.0, 15.0)) & 
        (initial_df['Y'] == 40.0)
    ].sort_values('X')
    
    # 验证数据完整性 (应有121个点)
    if len(x_section_df) != 121:
        raise ValueError(f"X截面数据点应为121个，实际找到{len(x_section_df)}个")
    
    # 基线拉平处理
    x_section_df = flatten_baseline(
        df=x_section_df, 
        coord_col='X', 
        value_col='Trimmed_Thickness'
    )
    
    # 保存为要求的格式 (无表头)
    x_section_path = output_dir / "x_crosssection_trimmed_amount_profile_of_Movement_on_Y-axis.csv"
    x_section_df[['X', 'Trimmed_Thickness']].to_csv(x_section_path, index=False, header=False)
    
    # === 步骤3: 提取Y截面数据 (x=40, y从-15到15) ===
    # 直接根据坐标范围提取数据 (-15 ≤ y ≤ 15, x=40)
    y_section_df = initial_df[
        (initial_df['Y'].between(-15.0, 15.0)) & 
        (initial_df['X'] == 40.0)
    ].sort_values('Y')
    
    # 验证数据完整性 (应有121个点)
    if len(y_section_df) != 121:
        raise ValueError(f"Y截面数据点应为121个，实际找到{len(y_section_df)}个")
    
    # 基线拉平处理
    y_section_df = flatten_baseline(
        df=y_section_df, 
        coord_col='Y', 
        value_col='Trimmed_Thickness'
    )
    
    # 保存为要求的格式 (无表头)
    y_section_path = output_dir / "y_crosssection_trimmed_amount_profile_of_Movement_on_X-axis.csv"
    y_section_df[['Y', 'Trimmed_Thickness']].to_csv(y_section_path, index=False, header=False)
    
    return (str(trimming_thk_path), str(x_section_path), str(y_section_path))

# 示例用法（本地测试）
if __name__ == "__main__":
    # 测试路径 - 在实际应用中会被替换
    test_base_dir = Path(r"Data/outputs")
    initial_file = r"Data/inputs/CrossTrim_initial/2602_30mm_crosstest_initial.csv"
    after_file = r"Data/inputs/CrossTrim_after/2602_crosstest_30mm_after.csv"
    
    try:
        results = process_and_save_outputs(initial_file, after_file, test_base_dir)
        print(f"处理完成! 文件已保存到:")
        print(f"刻蚀量文件: {results[0]}")
        print(f"X截面文件: {results[1]}")
        print(f"Y截面文件: {results[2]}")
        
        # 验证端点值
        try:
            # 检查X截面端点
            x_section = pd.read_csv(results[1], header=None, names=['X', 'Trimmed'])
            start_val = x_section['Trimmed'].iloc[0]
            end_val = x_section['Trimmed'].iloc[-1]
            print(f"\n基线拉平验证 (X截面):")
            print(f"起点(-15)值: {start_val:.6f} | 终点(15)值: {end_val:.6f}")
            
            # 检查Y截面端点
            y_section = pd.read_csv(results[2], header=None, names=['Y', 'Trimmed'])
            start_val = y_section['Trimmed'].iloc[0]
            end_val = y_section['Trimmed'].iloc[-1]
            print(f"\n基线拉平验证 (Y截面):")
            print(f"起点(-15)值: {start_val:.6f} | 终点(15)值: {end_val:.6f}")
        except Exception as e:
            print(f"端点验证失败: {str(e)}")
            
    except Exception as e:
        import traceback
        print(f"处理失败: {str(e)}\n详细错误:\n{traceback.format_exc()}")
