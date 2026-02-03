# main.py
import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon  # 添加此导入
import matplotlib as mpl
import matplotlib.font_manager as fm
from PyQt5.QtCore import QT_VERSION_STR
from PyQt5.Qt import PYQT_VERSION_STR

# 添加此函数获取图标路径
def get_icon_path():
    """获取应用程序图标路径"""
    # 开发环境中直接使用源文件路径
    if not getattr(sys, 'frozen', False):
        return "Data/WM.ico"
    
    # 打包环境中使用相对路径
    exe_dir = os.path.dirname(sys.executable)
    return os.path.join(exe_dir, "Data", "WM.ico")

# 配置日志
def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('wedge_master.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger('Main')
    logger.info("====== 启动 WedgeMaster ======")
    return logger

logger = setup_logging()

# 检查并记录 PyQt5 信息
try:
    print(f"PyQt5 Version: {PYQT_VERSION_STR}")
    print(f"Qt Runtime Version: {QT_VERSION_STR}")
    
    logger.info(f"PyQt5 版本: {PYQT_VERSION_STR}")
    logger.info(f"Qt 运行时版本: {QT_VERSION_STR}")
except Exception as e:
    logger.error(f"无法获取 PyQt5 版本信息: {str(e)}")
    sys.exit("无法导入 PyQt5")

try:
    # 其他初始化代码...
    logger.info("设置 Matplotlib 配置")
    
    if sys.platform == 'win32':
        mpl.rcParams['font.family'] = 'Microsoft YaHei'
    mpl.rcParams['axes.unicode_minus'] = False
    mpl.rcParams['font.size'] = 10
except Exception as e:
    logger.exception("初始化 Matplotlib 失败")
    sys.exit(f"初始化失败: {str(e)}")

# 运行主应用
def main():
    try:
        logger.info("导入应用模块...")
        from ui.main_window import MainWindow
        
        logger.info("创建应用实例...")
        app = QApplication(sys.argv)
        
        # ========== 新增图标设置代码 ==========
        icon_path = get_icon_path()
        if os.path.exists(icon_path):
            # 设置应用程序图标（影响任务栏图标）
            app.setWindowIcon(QIcon(icon_path))
            logger.info(f"已设置应用程序图标: {icon_path}")
        else:
            logger.warning(f"图标文件不存在: {icon_path}")
        # ====================================
        
        window = MainWindow()
        
        logger.info("显示主窗口...")
        window.show()
        
        logger.info("进入应用事件循环")
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"应用运行失败: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
