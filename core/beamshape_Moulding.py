import numpy as np
import pandas as pd
import os
from pathlib import Path

def load_and_resample_csv(filepath, total_points=31, shift_range=15):
    """加载并重采样CSV文件数据"""
    data = pd.read_csv(filepath, header=None)
    positions = data.iloc[:, 0].values
    depths = data.iloc[:, 1].values
    
    # 找到深度最大值的位置
    peak_idx = np.argmax(depths)
    center_offset = positions[peak_idx]
    
    # 平移所有位置让最大值位于0点
    shifted_positions = positions - center_offset
    
    # 创建新的插值坐标（1mm间隔）
    x_new = np.linspace(-shift_range, shift_range, total_points)
    
    # 使用线性插值获取新位置的数据
    interp_depths = np.interp(
        x_new, 
        shifted_positions, 
        depths, 
        left=0.0, 
        right=0.0
    )
    
    return interp_depths, center_offset, x_new

def save_shifted_profile(positions, depths, filename):
    """保存平移后的截面深度分布"""
    df = pd.DataFrame({
        'Position (mm)': positions,
        'Etching Depth': depths
    })
    df.to_csv(filename, index=False)

def save_beamprofile_with_diffs(beam_profile, x_profile, y_profile, iteration, folder='beamprofile_iterations'):
    """保存beamprofile矩阵并添加差异信息"""
    rows, cols = beam_profile.shape
    
    # 计算行和（卷积x方向）和列和（卷积y方向）
    row_sums = np.sum(beam_profile, axis=1)
    col_sums = np.sum(beam_profile, axis=0)
    
    # 计算与实验值的差异
    col_diffs = col_sums - x_profile  # 列和与x_crosssect差异
    row_diffs = row_sums - y_profile  # 行和与y_crosssect差异
    
    # 扩展矩阵添加差异列
    extended_beam = np.zeros((rows + 1, cols + 1))
    extended_beam[:rows, :cols] = beam_profile
    
    # 添加列差异（最后一行）
    extended_beam[rows, :cols] = col_diffs
    
    # 添加行差异（最后一列）
    extended_beam[:rows, cols] = row_diffs
    
    # 创建数据框（添加行列标签）
    df = pd.DataFrame(extended_beam)
    
    # 添加行列标签
    y_labels = [f"y={15-i}mm" for i in range(rows)] + ['Y-Conv Diff']
    df.insert(0, 'Row/Y-Position', y_labels)
    
    x_labels = [f"x={i-15}mm" for i in range(cols)] + ['X-Conv Diff']
    df.columns = ['Position'] + x_labels
    
    # 保存到文件
    # 处理迭代次数的显示
    iter_str = f"{iteration:03d}" if isinstance(iteration, int) else iteration
    filename = Path(folder) / f"iteration_{iter_str}_beamprofile.csv"
    df.to_csv(filename, index=False)
    return filename

def save_initial_profiles(x_pos, x_data, y_pos, y_data, folder, filename="shifted_initial_profiles.csv"):
    """保存用于计算循环的初始截面数据"""
    # 反转y_data以匹配beamprofile的行顺序
    reversed_y_data = y_data[::-1]
    
    # 创建数据框
    df = pd.DataFrame({
        'Position (mm)': np.concatenate([x_pos, y_pos]),
        'Etching Depth': np.concatenate([x_data, reversed_y_data]),
        'Profile Type': ['x_crosssect'] * len(x_pos) + ['y_crosssect'] * len(y_pos)
    })
    
    # 保存到文件
    file_path = Path(folder) / filename
    df.to_csv(file_path, index=False)
    return file_path

def reconstruct_beam_profile(x_file, y_file, output_dir):
    """重构光束轮廓主函数"""
    # 确保输出目录存在
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建存放迭代和临时结果的文件夹
    iter_dir = output_dir / "beamprofile_iterations"
    iter_dir.mkdir(exist_ok=True)
    
    # 加载数据并重采样
    x_profile, x_offset, x_positions = load_and_resample_csv(x_file)
    y_profile_raw, y_offset, y_positions = load_and_resample_csv(y_file)
    
    # 保存平移后的截面数据
    save_shifted_profile(x_positions, x_profile, iter_dir / "shifted_x_crosssection.csv")
    save_shifted_profile(y_positions, y_profile_raw, iter_dir / "shifted_y_crosssection.csv")
    
    # 反转y_profile数据以匹配顺序
    y_profile = y_profile_raw[::-1]
    
    # 保存组合的初始截面数据
    initial_profiles_file = save_initial_profiles(
        x_positions, x_profile, 
        y_positions, y_profile_raw, 
        iter_dir, "initial_shifted_profiles.csv"
    )
    
    # 初始化beamprofile和相关向量
    beam_profile = np.zeros((31, 31))
    iteration_count = 0
    processed_rows = np.full(31, False)  # 标记已处理的行
    
    # 计算归一化因子
    one_over_31_x = x_profile / 31.0
    sum_x = np.sum(x_profile)
    unit_of_x_crosssect = x_profile / sum_x
    
    # 初始填充beamprofile
    for i in range(31):
        beam_profile[i, :] = one_over_31_x
    
    def calculate_diffs():
        """计算行和、列和、卷积差"""
        row_sums = np.sum(beam_profile, axis=1)
        col_sums = np.sum(beam_profile, axis=0)
        diff_y = row_sums - y_profile
        diff_x = col_sums - x_profile
        return diff_y, diff_x, row_sums, col_sums
    
    def save_current_iteration(iter_num):
        """保存当前迭代状态"""
        return save_beamprofile_with_diffs(
            beam_profile, 
            x_profile, 
            y_profile, 
            iter_num, 
            iter_dir
        )
    
    # 保存初始状态 (迭代0)
    iteration_files = [str(save_current_iteration(0))]
    
    # 重构核心 - 迭代直到只剩下最后一行未处理
    while np.sum(~processed_rows) > 1:
        iteration_count += 1
        diff_y, _, _, _ = calculate_diffs()
        
        # 找出最大差异行 (只考虑未处理的行)
        unprocessed_indices = np.where(~processed_rows)[0]
        candidate_diffs = diff_y[unprocessed_indices]
        
        # 找到最大正差异值
        if len(candidate_diffs) == 0:
            break
            
        max_val = np.max(candidate_diffs)
        max_candidates = unprocessed_indices[abs(diff_y[unprocessed_indices] - max_val) < 1e-6]
        
        # 处理多个同最大值的情形（优先边缘行）
        if len(max_candidates) > 1:
            dist_to_center = np.abs(max_candidates - 15)
            selected_row = max_candidates[np.argmax(dist_to_center)]
        else:
            selected_row = max_candidates[0] if len(max_candidates) == 1 else unprocessed_indices[0]
        
        max_diff_val = diff_y[selected_row]
        y_position = 15 - selected_row
        
        # 调整目标行
        beam_profile[selected_row] -= max_diff_val * unit_of_x_crosssect
        processed_rows[selected_row] = True
        
        # 强制设该行差异为0
        diff_y[selected_row] = 0
        
        # 对其他未处理行进行补偿
        unprocessed_rows = np.where(~processed_rows)[0]
        if len(unprocessed_rows) > 0:
            compensation = (max_diff_val / len(unprocessed_rows)) * unit_of_x_crosssect
            for row_idx in unprocessed_rows:
                beam_profile[row_idx] += compensation
        
        # 保存当前迭代状态
        iter_file = save_current_iteration(iteration_count)
        iteration_files.append(str(iter_file))
    
    # 专门处理最后一行（中心行）
    unprocessed_rows = np.where(~processed_rows)[0]
    if len(unprocessed_rows) == 1:
        iteration_count += 1
        diff_y, _, _, _ = calculate_diffs()
        selected_row = unprocessed_rows[0]
        y_position = 15 - selected_row
        max_diff_val = diff_y[selected_row]
        
        # 修正最后一行
        beam_profile[selected_row] -= max_diff_val * unit_of_x_crosssect
        processed_rows[selected_row] = True
        
        # 对所有其他30行进行补偿
        compensation = (max_diff_val / 30) * unit_of_x_crosssect
        for row_idx in range(31):
            if row_idx != selected_row:
                beam_profile[row_idx] += compensation
        
        # 保存最终迭代
        final_iter_file = save_current_iteration(iteration_count)
        iteration_files.append(str(final_iter_file))
    
    # 处理负数 - 将负值设为0
    negative_count = np.sum(beam_profile < 0)
    if negative_count > 0:
        # 记录负数位置
        negative_positions = np.argwhere(beam_profile < 0)
        negative_correction = beam_profile.copy()
        
        # 将负数设为0
        beam_profile = np.maximum(beam_profile, 0)
        
        # 保存负数修正信息
        neg_df_data = []
        for pos in negative_positions:
            y_idx, x_idx = pos
            y_value = 15 - y_idx
            x_value = x_idx - 15
            neg_df_data.append({
                'Position Y': y_value,
                'Position X': x_value,
                'Original Value': negative_correction[y_idx, x_idx]
            })
        
        neg_df = pd.DataFrame(neg_df_data)
        neg_file = iter_dir / "negative_corrections.csv"
        neg_df.to_csv(neg_file, index=False)
    else:
        neg_file = None
    
    # 保存最终结果
    final_diff_y, final_diff_x, final_row_sums, final_col_sums = calculate_diffs()
    final_file = save_current_iteration("final")
    iteration_files.append(str(final_file))
    
    # 保存最终beamprofile（纯矩阵）
    final_matrix_file = output_dir / "reconstructed_beamprofile.csv"
    np.savetxt(final_matrix_file, beam_profile, delimiter=',')
    
    # 准备返回结果
    result = {
        "beam_profile": beam_profile,
        "row_sums": final_row_sums,
        "conv_y": final_col_sums,
        "diff_y": final_diff_y,
        "diff_x": final_diff_x,
        "x_profile": x_profile,
        "y_profile": y_profile,
        "iteration_files": iteration_files,
        "final_file": str(final_file),
        "negative_correction_file": str(neg_file) if neg_file else None,
        "initial_profiles_file": str(initial_profiles_file)
    }
    
    return result

# 测试代码保持原样
if __name__ == "__main__":
    print("运行本地测试...")
    
    test_dir = Path(__file__).parent.parent / "Data"
    x_file = test_dir / "inputs" / "x_crosssection_sample.csv"
    y_file = test_dir / "inputs" / "y_crosssection_sample.csv"
    output_dir = test_dir / "outputs" / "new_BeamShapeProfile"
    
    # 确保测试目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not x_file.exists() or not y_file.exists():
        print(f"测试文件不存在，请创建: {x_file} 和 {y_file}")
    else:
        print(f"开始重构光束形状...")
        print(f"X截面文件: {x_file}")
        print(f"Y截面文件: {y_file}")
        print(f"输出目录: {output_dir}")
        
        result = reconstruct_beam_profile(str(x_file), str(y_file), str(output_dir))
        
        print("\n重构完成!")
        print(f"最终光束轮廓大小: {result['beam_profile'].shape}")
        print(f"差异统计 - X轴差异最大值: {result['diff_x'].max():.6f}")
        print(f"              Y轴差异最大值: {result['diff_y'].max():.6f}")
