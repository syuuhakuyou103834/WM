import pandas as pd
import numpy as np
import logging

class StageCenterAnalyzer:
    def __init__(self):
        self.delta_up = None
        self.delta_down = None
        self.delta_right = None
        self.delta_left = None
        self.delta_x = None
        self.delta_y = None
        self.new_center = None
        self.results = {
            "delta_up": None, 
            "delta_down": None,
            "delta_right": None,
            "delta_left": None,
            "delta_x": None,
            "delta_y": None
        }
        # 添加日志记录器
        self.logger = logging.getLogger('StageCenterAnalyzer')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def load_files(self, initial_path, after_path):
        """加载初始文件和刻蚀后文件"""
        try:
            self.logger.info(f"开始加载文件: {initial_path} 和 {after_path}")
            
            # 读取CSV文件
            df_initial = pd.read_csv(initial_path)
            df_after = pd.read_csv(after_path)
            
            self.logger.info(f"初始文件原始行数: {len(df_initial)}")
            self.logger.info(f"刻蚀后文件原始行数: {len(df_after)}")
            
            # 清理文件：删除任何可能存在的空行
            df_initial = df_initial.dropna(how='all')
            df_after = df_after.dropna(how='all')
            
            self.logger.info(f"初始文件清理后行数: {len(df_initial)}")
            self.logger.info(f"刻蚀后文件清理后行数: {len(df_after)}")
            
            # 验证文件格式
            required_columns = ['X', 'Y', 'Thickness(nm)']
            missing_initial = [col for col in required_columns if col not in df_initial.columns]
            missing_after = [col for col in required_columns if col not in df_after.columns]
            
            if missing_initial:
                error_msg = f"初始文件缺少必要的列名: {', '.join(missing_initial)}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            if missing_after:
                error_msg = f"刻蚀后文件缺少必要的列名: {', '.join(missing_after)}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # 验证行数 - CSV文件中应有1行表头+324行数据 = 总共325行
            # 但Pandas读取后会去掉表头，所以数据行数应为324行
            expected_rows = 324
            self.logger.info(f"预期数据行数(不包括表头): {expected_rows}")
            
            if len(df_initial) != expected_rows or len(df_after) != expected_rows:
                self.logger.error(f"初始文件实际行数: {len(df_initial)}, 刻蚀后文件实际行数: {len(df_after)}")
                raise ValueError(f"文件应包含324行数据（不包括表头）。当前初始文件{len(df_initial)}行，刻蚀后文件{len(df_after)}行")
            
            # 重置索引，确保索引连续
            self.initial_df = df_initial.reset_index(drop=True)
            self.after_df = df_after.reset_index(drop=True)
            
            self.logger.info("文件加载成功")
            return True
        
        except Exception as e:
            self.logger.exception("文件加载失败")
            raise RuntimeError(f"文件加载失败: {str(e)}")
    
    def calculate_results(self, old_center_x, old_center_y):
        """计算四个方向的偏移量和新的中心点位置"""
        self.logger.info(f"开始计算中心点偏移结果, 旧中心点: ({old_center_x}, {old_center_y})")
        
        # 复制数据避免修改原始文件
        initial_df = self.initial_df.copy()
        after_df = self.after_df.copy()
        
        # 计算刻蚀量（初始厚度 - 刻蚀后厚度）
        etching_df = initial_df.copy()
        etching_df["TrimmingAmount"] = initial_df["Thickness(nm)"] - after_df["Thickness(nm)"]
        
        # 数据分区 (基于324行数据)
        # 共324行数据，分为4个区域，每个区域81行
        
        # 上方: 第0行到第80行 (共81行)
        top_section = etching_df.iloc[0:81]
        self.logger.info(f"上方区域行数: {len(top_section)}")
        
        # 下方: 第81行到第161行 (共81行)
        bottom_section = etching_df.iloc[81:162]
        self.logger.info(f"下方区域行数: {len(bottom_section)}")
        
        # 右方: 第162行到第242行 (共81行)
        right_section = etching_df.iloc[162:243]
        self.logger.info(f"右方区域行数: {len(right_section)}")
        
        # 左方: 第243行到第323行 (共81行)
        left_section = etching_df.iloc[243:324]
        self.logger.info(f"左方区域行数: {len(left_section)}")
        
        # 计算各方向偏移量
        self.delta_up = self._calculate_offset(top_section, "上方")
        self.delta_down = self._calculate_offset(bottom_section, "下方")
        self.delta_right = self._calculate_offset(right_section, "右方", is_vertical=False)
        self.delta_left = self._calculate_offset(left_section, "左方", is_vertical=False)
        
        self.logger.info(f"上方偏移量: {self.delta_up}")
        self.logger.info(f"下方偏移量: {self.delta_down}")
        self.logger.info(f"右方偏移量: {self.delta_right}")
        self.logger.info(f"左方偏移量: {self.delta_left}")
        
        # 计算中心点偏移量
        self.delta_x = -(self.delta_up + self.delta_down) / 2
        self.delta_y = (self.delta_right + self.delta_left) / 2
        
        # 计算新的中心点坐标
        self.new_center_x = old_center_x + self.delta_x
        self.new_center_y = old_center_y + self.delta_y
        
        self.logger.info(f"X轴偏移量: {self.delta_x}")
        self.logger.info(f"Y轴偏移量: {self.delta_y}")
        self.logger.info(f"新中心点坐标: ({self.new_center_x}, {self.new_center_y})")
        
        # 存储结果
        self.results = {
            "delta_up": self.delta_up, 
            "delta_down": self.delta_down,
            "delta_right": self.delta_right,
            "delta_left": self.delta_left,
            "delta_x": self.delta_x,
            "delta_y": self.delta_y,
            "new_center_x": self.new_center_x,
            "new_center_y": self.new_center_y,
            "etching_df": etching_df  # 包含刻蚀量的完整数据
        }
        
        self.logger.info("计算完成")
        return self.results
    
    def _calculate_offset(self, section, section_name, is_vertical=True):
        """计算特定区域的偏移量"""
        if section.empty:
            self.logger.warning(f"{section_name}区域为空")
            return 0.0
        
        # 找到刻蚀量最大值的索引
        max_idx = section["TrimmingAmount"].idxmax()
        max_value = section["TrimmingAmount"].max()
        
        result = section.at[max_idx, "X"] if is_vertical else section.at[max_idx, "Y"]
        self.logger.info(f"{section_name}区域: 最大刻蚀量 {max_value:.4f} 在坐标 [{section.at[max_idx, 'X']}, {section.at[max_idx, 'Y']}]")
        
        return result

