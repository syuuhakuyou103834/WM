import sys
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QMenuBar, QAction, 
    QTabWidget, QStatusBar, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from pathlib import Path  # 确保导入了 Path

from .center_adjust_ui import CenterAdjustUI
from .analyzer_ui import AnalyzerUI
from .coefficient_calculator_ui import CoefficientCalculatorUI 
from .shape_creator_ui import BeamShapeCreatorUI
from .cross_test_analyzer_ui import CrossTestAnalyzerUI
from .shape_Moulding_ui import ShapeMouldingUI  # 新增UI组件
from utils.file_io import get_latest_files, get_resource_path
from .beam_spot_test_ui import BeamSpotTestUI  # Beamspottest组件


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WedgeMaster beta 1.0.4.3 —— Tools for GCIB trimmer powered by Zhou Boyang 2025.11.18")
        self.setGeometry(100, 100, 1500, 800)
        
        # 设置窗口图标
        self.setWindowIcon(self.get_app_icon())
        
        # 创建菜单栏
        self._create_menu_bar()
        
        # 主选项卡
        self.tab_widget = QTabWidget()
        
        # 将所有标签页集中在此处创建
        self.center_adjust_tab = CenterAdjustUI()
        self.analyzer_tab = AnalyzerUI()
        self.coeff_calculator_tab = CoefficientCalculatorUI()
        self.beam_shape_tab = BeamShapeCreatorUI()
        self.cross_test_analyzer_tab = CrossTestAnalyzerUI()
        # 新增的beam形状重构UI
        self.shape_moulding_tab = ShapeMouldingUI()  # 添加shapeMoulding新组件
        self.beam_spot_test_tab = BeamSpotTestUI()  # 添加BeamSpotTest新组建

        
        # 添加到选项卡控件
        self.tab_widget.addTab(self.center_adjust_tab, "调整中心点")
        self.tab_widget.addTab(self.analyzer_tab, "WedgeTest分析")
        self.tab_widget.addTab(self.coeff_calculator_tab, "Beam系数计算")
        self.tab_widget.addTab(self.beam_shape_tab, "Beam形状创建")
        self.tab_widget.addTab(self.cross_test_analyzer_tab, "CrossTest中心点分析")
        self.tab_widget.addTab(self.shape_moulding_tab, "Beam形状重构")  
        self.tab_widget.addTab(self.beam_spot_test_tab, "Beam Spot测试")  
        
        # 设置中心控件
        self.setCentralWidget(self.tab_widget)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 自动加载最新文件
        self.load_default_files()
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = QMenuBar(self)
        
        # 文件菜单
        file_menu = menu_bar.addMenu("开始")
        
        load_recipe_action = QAction("加载Recipe", self)
        load_recipe_action.triggered.connect(self.load_recipe)
        file_menu.addAction(load_recipe_action)
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        about_action = QAction("关于WedgeMaster", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
        self.setMenuBar(menu_bar)

    def show_about_dialog(self):
        """显示关于对话框，包含作者信息和版权声明"""
        about_text = """
        <html>
        <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
            }
            h2 {
                color: #2c3e50;
                text-align: center;
            }
            .org {
                font-weight: bold;
                color: #2980b9;
            }
            .contact {
                color: #27ae60;
            }
            .copyright {
                font-style: italic;
                color: #7f8c8d;
            }
        </style>
        </head>
        <body>
            <div style="text-align:center; margin-bottom:20px;">
                <h2>WedgeMaster beta - v1.0.4.3</h2>
                <p>WedgeTest分析工具集</p>
            </div>
            
            <div style="margin-bottom:15px;">
                <p><span class="org">开发者：</span></p>
                <p>周伯阳</p>
            </div>
            
            <div style="margin-bottom:15px;">
                <p><span class="org">联系方式：</span></p>
                <p class="contact">邮箱：infinitewill@outlook.com</p>
                <p class="contact">电话：</p>
                
            </div>
            
            
            <hr style="margin:20px 0;">
            
            <div>
                <p class="copyright">© 2025 WedgeMaster Pro. 保留所有权利。</p>
                <p class="copyright">本软件的开发和使用受《中华人民共和国著作权法》和相关国际版权公约保护。</p>
                <p class="copyright">未经许可，禁止对本软件进行任何形式的逆向工程、反编译，或商业性用途。</p>
                <p class="copyright">知识产权法违规者将承担相应法律责任。</p>
            </div>
        </body>
        </html>
        """
        
        # 创建消息框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("关于 WedgeMaster Pro")
        
        # 设置应用图标
        icon_path = get_resource_path("Data/WM.ico")
        if icon_path.exists():
            msg_box.setWindowIcon(QIcon(str(icon_path)))
        
        # 设置样式
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #f9f9f9;
            }
            QLabel {
                min-width: 500px;
            }
        """)
        
        # 设置内容
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(about_text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # 显示对话框
        msg_box.exec_()
    
    def get_app_icon(self):
        """获取应用程序图标"""
        icon_path = get_resource_path("Data/WM.ico")
        if icon_path.exists():
            logging.getLogger('UI').info(f"已加载应用程序图标: {icon_path}")
            return QIcon(str(icon_path))
            
        logging.getLogger('UI').error("无法找到WM.ico文件")
        
        # 返回默认图标作为备份
        return QIcon()
    
    def load_default_files(self):
        """加载默认的最新文件"""
        try:
            recipe_file, initial_file, after_file = get_latest_files()
            self.center_adjust_tab.set_recipe_file(recipe_file)
            self.analyzer_tab.set_files(recipe_file, initial_file, after_file)
            self.status_bar.showMessage("已加载最新文件")
            
            # 为Beam系数计算选项卡也加载默认厚度文件
            self.coeff_calculator_tab._load_default_files()
            
        except Exception as e:
            self.status_bar.showMessage(f"加载最新文件失败: {str(e)}")
            logging.getLogger('UI').error(f"加载最新文件失败: {str(e)}")
    
    def load_recipe(self):
        """加载Recipe文件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Recipe文件", "", "CSV Files (*.csv)", options=options)
        
        if file_path:
            self.center_adjust_tab.set_recipe_file(file_path)
            self.analyzer_tab.set_recipe_file(file_path)
            self.status_bar.showMessage(f"已加载Recipe: {file_path}")
    
    def closeEvent(self, event):
        """关闭窗口前保存配置"""
        # 可以在这里添加配置保存逻辑
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序图标（这将影响任务栏图标）
    from pathlib import Path  # 确保导入 Path
    icon_path = Path("Data/WM.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
