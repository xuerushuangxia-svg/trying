#!/usr/bin/env python3
"""
独立启动器 - 内嵌 Streamlit 应用，不依赖外部文件
"""
import sys
import os
import webbrowser
import time
import socket
import threading
import tempfile
import shutil

# 设置路径
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后
    BUNDLE_DIR = sys._MEIPASS  # PyInstaller 解压的临时目录
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

# 创建工作目录并复制文件
WORK_DIR = os.path.join(tempfile.gettempdir(), 'xue_risk_app')
if os.path.exists(WORK_DIR):
    shutil.rmtree(WORK_DIR)
os.makedirs(WORK_DIR, exist_ok=True)

# 复制所有必要文件到工作目录
for item in ['main.py', 'config', 'services', 'ui', 'utils']:
    src = os.path.join(BUNDLE_DIR, item)
    dst = os.path.join(WORK_DIR, item)
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    elif os.path.isfile(src):
        shutil.copy2(src, dst)

os.chdir(WORK_DIR)
sys.path.insert(0, WORK_DIR)

# 设置环境变量
os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'


def find_free_port(start_port=8501):
    """查找可用端口"""
    port = start_port
    while port < start_port + 100:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            port += 1
    return start_port


def open_browser(port):
    """延迟打开浏览器"""
    time.sleep(2)
    webbrowser.open(f'http://localhost:{port}')


def main():
    """启动应用"""
    port = find_free_port()
    
    print(f"""
    ╔══════════════════════════════════════════════════╗
    ║     XUE 风险全维度穿透终端                        ║
    ║     正在启动...                                   ║
    ║     访问地址: http://localhost:{port}              ║
    ║     关闭此窗口停止应用                            ║
    ╚══════════════════════════════════════════════════╝
    """)
    
    # 在后台线程打开浏览器
    browser_thread = threading.Thread(target=open_browser, args=(port,))
    browser_thread.daemon = True
    browser_thread.start()
    
    # 使用 streamlit CLI 模式启动（更可靠）
    main_script = os.path.join(WORK_DIR, "main.py")
    
    sys.argv = [
        "streamlit", "run", main_script,
        "--server.port", str(port),
        "--server.address", "localhost",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false",
        "--server.fileWatcherType", "none",
    ]
    
    try:
        from streamlit.web import cli as stcli
        stcli.main()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        print("\n应用已停止")
    finally:
        # 清理临时目录
        try:
            shutil.rmtree(WORK_DIR)
        except:
            pass


if __name__ == "__main__":
    main()
