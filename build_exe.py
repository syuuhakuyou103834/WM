# build_exe.py
import os
import sys
import shutil
from pathlib import Path
from PyInstaller.__main__ import run

# 获取脚本的绝对路径作为根目录
script_dir = Path(__file__).resolve().parent

# 检查并创建必要的目录
print("=" * 60)
print("验证和创建所需目录结构...")
required_dirs = [
    'config',  # 新增：根目录下的config文件夹，用于存放配置文件
    'Data/config',
    'Data/inputs/CrossTrim_initial',
    'Data/inputs/CrossTrim_after',
    'Data/inputs/THK_initial',
    'Data/inputs/THK_after',
    'Data/inputs/WedgeTestRecipe',
    'Data/inputs/Default Beam coefficient test Map',  # 新增：默认Beam系数测试Map路径
    'Data/outputs/Data_processor',
    'Data/outputs/new_WedgeTestRecipe',
    'Data/outputs/new_BeamShapeProfile',
    'Data/outputs/Regression_Data',
    'Data/outputs/WedgeTest_Log'  # 新增：分析日志文件夹
]

for dir_path in required_dirs:
    full_dir = script_dir / dir_path
    full_dir.mkdir(parents=True, exist_ok=True)
    
    # 在每个目录中创建空文件 .keep
    keep_file = full_dir / '.keep'
    if not keep_file.exists():
        keep_file.touch()
    
    # 打印相对路径而不是完整路径
    print(f"  > 已验证/创建: {dir_path}")

# 图标文件路径 - 确保此文件存在
icon_path = script_dir / 'Data/WM.ico'
if not icon_path.exists():
    print(f"\n未找到图标文件: {icon_path.relative_to(script_dir)}, 尝试创建默认图标...")
    try:
        # 创建默认图标文件（如果不存在）
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (256, 256), color=(0, 100, 200, 255))  # 蓝色背景
        draw = ImageDraw.Draw(img)

        # 绘制简单的W字母
        draw.text((50, 80), "W", fill=(255, 255, 255, 255))  # 白色文字

        # 保存为ICO格式
        img.save(icon_path, 'ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        print(f"已创建默认图标: {icon_path.relative_to(script_dir)}")
    except ImportError:
        print("警告: PIL/Pillow未安装，无法创建图标文件")
        print("请手动将您的图标文件复制到: Data/WM.ico")
        icon_path = None
    except Exception as e:
        print(f"创建图标时出错: {str(e)}")
        print("请手动将您的图标文件复制到: Data/WM.ico")
        icon_path = None
else:
    print(f"\n已找到图标文件: {icon_path.relative_to(script_dir)}")

# 构建PyInstaller命令
print("\n配置PyInstaller打包参数...")
pyinstaller_args = [
    'main.py',
    '--name=WedgeMaster',
    '--onefile',
    '--windowed',
    '--add-data=core;core',
    '--add-data=ui;ui',
    '--add-data=utils;utils',
    '--add-data=Data;Data',

    # 隐藏导入支持
    '--hidden-import=sklearn.utils._weight_vector',
    '--hidden-import=sklearn.neighbors._typedefs',
    '--hidden-import=sklearn.neighbors._quad_tree',
    '--hidden-import=pandas._libs.tslibs.np_datetime',
    '--hidden-import=scipy.special.cython_special',
    '--hidden-import=scipy.spatial.transform._rotation_groups',

    # 确保收集所有必要的库
    '--collect-all=PyQt5',
    '--collect-all=sklearn',
    '--collect-all=pandas',
    '--collect-all=numpy',
    '--collect-all=scipy',
    '--collect-all=matplotlib',
    '--collect-all=PIL',

    # 版本信息（可选，帮助Windows识别应用程序）
    '--version-file=version_info.txt' if Path('version_info.txt').exists() else '',

    # 清理临时目录
    '--clean'
]

# 移除空的版本文件参数
pyinstaller_args = [arg for arg in pyinstaller_args if arg]

# 添加图标参数 - 确保使用绝对路径
if icon_path and icon_path.exists():
    # 检查图标文件大小，确保不是空文件
    if icon_path.stat().st_size > 0:
        icon_arg = f'--icon={str(icon_path.absolute())}'
        pyinstaller_args.append(icon_arg)
        print(f"使用图标文件: {icon_path.relative_to(script_dir)} (大小: {icon_path.stat().st_size} bytes)")
        print(f"图标参数: {icon_arg}")
    else:
        print("警告: 图标文件为空，将使用默认图标")
else:
    print("警告: 未找到有效的图标文件，将使用默认图标")
    print("请确保 WM.ico 文件存在于 Data 目录中")

# 调整路径，确保在当前目录运行
working_dir = os.getcwd()
os.chdir(script_dir)

# 执行打包
print("\n" + "=" * 60)
print("开始打包应用程序...")
print(f"工作目录: {script_dir}")
print(f"PyInstaller参数: {' '.join(pyinstaller_args)}")
print("=" * 60 + "\n")

run(pyinstaller_args)

# 恢复原始工作目录
os.chdir(working_dir)

# 获取 dist 目录和可执行文件路径
dist_dir = script_dir / 'dist'
exe_path = dist_dir / 'WedgeMaster.exe'

# 检查打包是否成功
print("\n" + "=" * 60)
if exe_path.exists():
    print(f"打包成功! EXE 文件位置: {exe_path}")
    print(f"EXE 文件大小: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")

    # 验证图标是否嵌入
    if icon_path and icon_path.exists():
        print(f"图标状态: 已使用 {icon_path.relative_to(script_dir)}")
    else:
        print("图标状态: 使用默认图标")

    # 复制 Data 目录到 dist 文件夹
    print("\n准备复制 Data 目录到 dist 文件夹...")
    
    try:
        # 源数据目录
        source_data = script_dir / 'Data'
        
        # 目标数据目录
        dest_data = dist_dir / 'Data'
        
        # 如果目标目录已存在，删除它
        if dest_data.exists():
            print(f" > 删除现有 Data 目录: {dest_data}")
            shutil.rmtree(dest_data)
        
        # 复制 Data 目录
        print(f" > 从 {source_data} 复制到 {dest_data}")
        shutil.copytree(source_data, dest_data)

        # 创建 config 目录在 dist 文件夹中
        config_dir = dist_dir / 'config'
        config_dir.mkdir(exist_ok=True)
        print(f" > 创建配置目录: {config_dir}")

        # 创建配置说明文件
        readme_file = config_dir / 'README.txt'
        if not readme_file.exists():
            readme_content = """WedgeMaster 配置文件目录

此目录包含应用程序的配置文件：

maintenance.ini - 离子化室保养时间设置
  - 自动保存用户设定的保养时间
  - 软件重启后自动加载
  - 可手动编辑或删除重置

注意事项：
- 请勿删除此目录
- 可以备份 maintenance.ini 文件以保存设置
- 如需重置保养时间，删除 maintenance.ini 文件即可
"""
            readme_file.write_text(readme_content, encoding='utf-8')
            print(f"  > 创建配置说明文件: {readme_file}")

        # 特别检查图标文件是否复制
        icon_in_dist = dest_data / 'WM.ico'
        if icon_in_dist.exists():
            print(f"  > 已复制图标文件: {icon_in_dist}")
        else:
            print(f" 警告: 图标文件未正确复制到 {icon_in_dist}")

        # 检查默认Beam系数测试Map文件
        default_map_source = source_data / 'inputs' / 'Default Beam coefficient test Map' / '2801-Default Map.csv'
        default_map_dest = dest_data / 'inputs' / 'Default Beam coefficient test Map' / '2801-Default Map.csv'
        if default_map_source.exists():
            print(f"  > 默认Map文件存在: {default_map_source}")
        else:
            print(f"  警告: 默认Map文件不存在: {default_map_source}")
            print(f"  > 请手动将2801-Default Map.csv文件放置到: Data/inputs/Default Beam coefficient test Map/")

        # 显示最终目录结构
        print("\n最终应用程序目录结构:")
        print(f"  {dist_dir}/")
        print(f"    ├── WedgeMaster.exe")
        print(f"    ├── config/         # 配置文件目录 (用户可见)")
        print(f"    │   ├── README.txt   # 配置说明文件")
        print(f"    │   └── maintenance.ini  # 保养时间设置 (运行时生成)")
        print(f"    └── Data/")
        print(f"        ├── WM.ico")  # 图标文件在Data目录下
        print(f"        ├── config/")
        print(f"        ├── inputs/")
        print(f"        │   ├── THK_initial/")
        print(f"        │   ├── THK_after/")
        print(f"        │   ├── CrossTrim_initial/")
        print(f"        │   ├── CrossTrim_after/")
        print(f"        │   ├── WedgeTestRecipe/")
        print(f"        │   └── Default Beam coefficient test Map/")  # 新增：默认Beam系数测试Map路径
        print(f"        │       └── 2801-Default Map.csv")  # 新增：默认Map文件
        print(f"        └── outputs/")
        print(f"            ├── Data_processor/")
        print(f"            ├── new_WedgeTestRecipe/")
        print(f"            ├── new_BeamShapeProfile/")
        print(f"            ├── Regression_Data/")
        print(f"            └── WedgeTest_Log/  # 分析日志目录")
    except Exception as e:
        print(f"复制 Data 目录时出错: {str(e)}")
else:
    print("打包失败！请查看上述输出以获取详细信息")

print("=" * 60 + "\n")
