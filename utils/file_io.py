import os
import sys
from pathlib import Path
import logging
import shutil

# 配置日志
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('wedge_master_fileio.log'),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger('FileIO')
logger.setLevel(logging.DEBUG)

# 获取项目根目录
ROOT_DIR = Path(__file__).resolve().parents[1]

def is_frozen():
    """检查是否是打包后的环境"""
    return getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS')

def get_resource_path(relative_path):
    """
    获取资源的绝对路径，适用于开发环境和打包后的EXE
    返回Path对象而不是字符串
    """
    try:
        base_path = None
        
        # 尝试获取 exe 所在目录
        if hasattr(sys, 'frozen') or hasattr(sys, '_MEIPASS'):
            exe_dir = Path(sys.executable).parent
            # 检查 exe 所在目录是否有 Data 文件夹
            exe_data_path = exe_dir / relative_path
            # 如果 exe 所在目录已有对应资源或目录，则使用 exe 所在目录作为基路径
            if exe_data_path.exists() or "Data" in relative_path.split(os.sep):
                base_path = exe_dir
                logger.info(f"使用应用所在目录: {base_path}")
                return base_path / relative_path
        
        # PyInstaller 创建的临时文件夹
        if hasattr(sys, '_MEIPASS'):
            base_path = Path(sys._MEIPASS)
            logger.info(f"MEIPASS 路径: {base_path}")
        # cx_Freeze 或其他打包工具
        elif is_frozen():
            base_path = Path(sys.executable).parent
            logger.info(f"冻结执行路径: {base_path}")
        else:
            # 开发环境 - 使用项目根目录
            base_path = ROOT_DIR
            logger.info(f"开发路径: {base_path}")
        
        full_path = base_path / relative_path
        
        # 记录路径信息
        logger.info(f"资源路径解析: {relative_path} -> {full_path}")
        
        # 确保路径存在
        if not full_path.exists():
            if '.' not in relative_path:  # 目录而非文件
                logger.warning(f"目录不存在，创建目录: {full_path}")
                full_path.mkdir(parents=True, exist_ok=True)
                # 确保目录下有空文件
                if not any(full_path.iterdir()):
                    (full_path / '.keep').touch()
            else:  # 文件
                logger.warning(f"文件目录不存在，创建父目录: {full_path.parent}")
                full_path.parent.mkdir(parents=True, exist_ok=True)
                # 创建空文件
                if not full_path.exists():
                    full_path.touch()
        
        return full_path
    
    except Exception as e:
        logger.exception(f"获取资源路径时出错: {str(e)}")
        # 返回开发环境路径作为后备
        return ROOT_DIR / relative_path

def get_latest_files():
    """获取最新配置文件、初始厚度和刻蚀后厚度文件"""
    try:
        # 使用get_resource_path获取各个目录
        recipe_dir = get_resource_path("Data/inputs/WedgeTestRecipe")
        initial_dir = get_resource_path("Data/inputs/THK_initial")
        after_dir = get_resource_path("Data/inputs/THK_after")
        
        logger.info(f"查找最新文件，目录:\nRecipe: {recipe_dir}\nInitial: {initial_dir}\nAfter: {after_dir}")
        
        # 获取所有符合条件的文件
        recipe_files = list(recipe_dir.glob("*.csv"))
        initial_files = list(initial_dir.glob("*.csv"))
        after_files = list(after_dir.glob("*.csv"))
        
        if not recipe_files:
            logger.warning(f"在 {recipe_dir} 目录中找不到Recipe文件")
        if not initial_files:
            logger.warning(f"在 {initial_dir} 目录中找不到初始厚度文件")
        if not after_files:
            logger.warning(f"在 {after_dir} 目录中找不到刻蚀后厚度文件")
        
        # 根据创建时间排序
        def get_file_info(files):
            if files:
                latest = max(files, key=lambda x: x.stat().st_mtime)
                return latest
            return None
        
        recipe_file = get_file_info(recipe_files)
        initial_file = get_file_info(initial_files)
        after_file = get_file_info(after_files)
        
        logger.info(f"查找到的文件:\nRecipe: {recipe_file}\nInitial: {initial_file}\nAfter: {after_file}")
        
        return recipe_file, initial_file, after_file
            
    except Exception as e:
        logger.exception(f"获取最新文件时出错: {str(e)}")
        raise RuntimeError(f"无法获取最新文件: {str(e)}")

def get_latest_thickness_files():
    """获取初始厚度和刻蚀后厚度文件的最新文件"""
    try:
        # 使用get_resource_path获取路径
        initial_dir = get_resource_path("Data/inputs/THK_initial")
        after_dir = get_resource_path("Data/inputs/THK_after")
        
        logger.info(f"查找最新厚度文件，目录:\nInitial: {initial_dir}\nAfter: {after_dir}")
        
        # 获取所有符合条件的文件
        initial_files = list(initial_dir.glob("*.csv"))
        after_files = list(after_dir.glob("*.csv"))
        
        if not initial_files:
            logger.warning(f"在 {initial_dir} 目录中找不到初始厚度文件")
        if not after_files:
            logger.warning(f"在 {after_dir} 目录中找不到刻蚀后厚度文件")
        
        # 根据创建时间排序
        initial_file = max(initial_files, key=lambda x: x.stat().st_mtime) if initial_files else None
        after_file = max(after_files, key=lambda x: x.stat().st_mtime) if after_files else None
        
        logger.info(f"查找到的厚度文件:\nInitial: {initial_file}\nAfter: {after_file}")
        
        if not initial_file or not after_file:
            raise FileNotFoundError("缺少初始或刻蚀后厚度文件")
            
        return Path(initial_file), Path(after_file)
            
    except Exception as e:
        logger.exception(f"获取最新厚度文件时出错: {str(e)}")
        raise RuntimeError(f"无法获取最新厚度文件: {str(e)}")

def ensure_dirs():
    """确保所需的所有目录都存在"""
    dirs = [
        "Data/config",
        "Data/inputs/CrossTrim_initial",
        "Data/inputs/CrossTrim_after",
        "Data/inputs/THK_initial",
        "Data/inputs/THK_after",
        "Data/inputs/WedgeTestRecipe",
        "Data/outputs/Data_processor",
        "Data/outputs/new_WedgeTestRecipe",
        "Data/outputs/new_BeamShapeProfile",
        "Data/outputs/Regression_Data"
    ]
    
    logger.info("开始验证和创建所需的目录结构...")
    
    for dir_path in dirs:
        try:
            resource_dir = get_resource_path(dir_path)
            if not resource_dir.exists():
                logger.info(f"创建缺失目录: {resource_dir}")
                resource_dir.mkdir(parents=True, exist_ok=True)
                
                # 确保目录下有空文件
                if not any(resource_dir.iterdir()):
                    keep_file = resource_dir / '.keep'
                    with keep_file.open('w') as f:
                        f.write("")
                        logger.info(f"在 {keep_file} 创建.keep文件")
        except Exception as e:
            logger.error(f"创建目录失败: {dir_path} - {str(e)}")

def validate_paths():
    """验证所有必要的目录都存在，如果不存在则创建"""
    ensure_dirs()
    
    # 特殊文件检查
    favicon = get_resource_path("Data/WM.ico")
    if not favicon.exists():
        try:
            # 创建默认图标
            from PIL import Image
            img = Image.new('RGB', (32, 32), color='gray')
            img.save(str(favicon), 'ICO')
            logger.info(f"创建默认图标: {favicon}")
        except ImportError:
            # 没有PIL时创建空文件
            favicon.touch()
            logger.warning(f"创建空图标文件: {favicon}")

# 为兼容旧代码添加的函数
def validate_path(path: str) -> Path:
    """
    (兼容旧代码)验证路径是否存在，不存在则创建
    返回Path对象
    """
    result = get_resource_path(path)
    logger.debug(f"验证路径: {path} -> {result}")
    return result

def ensure_dir(dir_path: str) -> Path:
    """
    (兼容旧代码)确保目录存在
    返回Path对象
    """
    result = get_resource_path(dir_path)
    if not result.exists():
        logger.info(f"创建目录: {result}")
        result.mkdir(parents=True, exist_ok=True)
    return result

def main():
    """测试函数"""
    print("=== 路径资源测试 ===\n")
    
    # 测试各种路径
    paths = [
        "Data/config",
        "Data/inputs/THK_initial/test.csv",
        "nonexistent_folder",
        "another_folder/missing_file"
    ]
    
    for path in paths:
        try:
            result = get_resource_path(path)
            print(f"原始路径: '{path}' -> 解析路径: {result}")
            print(f"路径存在: {'是' if result.exists() else '否'} | 是否目录: {'是' if result.is_dir() else '否'}")
            print()
        except Exception as e:
            print(f"路径 '{path}' 出错: {str(e)}\n")
    
    # 检查并创建所需目录
    validate_paths()
    
    # 测试文件查找
    print("\n=== 文件查找测试 ===")
    try:
        recipe, initial, after = get_latest_files()
        print(f"最新Recipe文件: {recipe}")
        print(f"最新初始厚度文件: {initial}")
        print(f"最新刻蚀后厚度文件: {after}")
    except Exception as e:
        print(f"获取最新文件失败: {str(e)}")

if __name__ == "__main__":
    main()
