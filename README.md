# XUE 风险全维度穿透终端

A股风险分析工具，提供深度风险穿透报告。

## 快速开始

```bash
pip install -r requirements.txt
streamlit run main.py
```

## 打包为应用程序

### 本地打包

```bash
pip install pyinstaller
pyinstaller build.spec --noconfirm
```

- **macOS**: `dist/XUE风险穿透终端.app`
- **Windows**: `dist/XUE风险穿透终端/XUE风险穿透终端.exe`

### 跨平台自动打包

推送到 GitHub 后，创建 tag 触发 Actions：

```bash
git tag v1.0.0
git push --tags
```

自动构建 Windows + macOS 版本，在 Releases 页面下载。
