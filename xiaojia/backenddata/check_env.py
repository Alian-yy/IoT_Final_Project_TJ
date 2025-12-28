# -*- coding: utf-8 -*-
"""
环境检查脚本 - 检查必要的依赖是否已安装
"""
import sys
import os

# 设置控制台编码为UTF-8（Windows）
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')

print("=" * 60)
print("Environment Check")
print("=" * 60)

# 检查Python版本
python_version = sys.version_info
print(f"[OK] Python Version: {python_version.major}.{python_version.minor}.{python_version.micro}")

if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
    print("[WARN] Recommended: Python 3.8 or higher")

# 检查必要的库
required_libs = {
    "paho-mqtt": "MQTT subscription (Required)",
    "pandas": "Data analysis (Optional)",
    "numpy": "Data analysis (Optional)",
    "sklearn": "Data analysis (Optional)",
    "scipy": "Data analysis (Optional)",
}

print("\nChecking dependencies:")
print("-" * 60)

all_ok = True
for lib_name, description in required_libs.items():
    try:
        if lib_name == "sklearn":
            import sklearn
            lib_version = sklearn.__version__
        elif lib_name == "paho-mqtt":
            # paho-mqtt的导入名称是paho.mqtt
            import paho.mqtt.client as mqtt
            lib_version = "installed"
        else:
            module = __import__(lib_name)
            lib_version = getattr(module, "__version__", "Unknown")
        
        print(f"[OK] {lib_name:15s} {lib_version:15s} - {description}")
    except ImportError:
        if lib_name == "paho-mqtt":
            print(f"[X]  {lib_name:15s} {'Not installed':15s} - {description} (Required!)")
            all_ok = False
        else:
            print(f"[!]  {lib_name:15s} {'Not installed':15s} - {description} (Optional)")

print("\n" + "=" * 60)

if all_ok:
    print("[OK] All required libraries installed! You can run test_subscribe.py")
else:
    print("[X]  Missing required libraries! Please install:")
    print("     pip install paho-mqtt")
    print("\n     For full features, install:")
    print("     pip install -r requirements.txt")

print("=" * 60)

