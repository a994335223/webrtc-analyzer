# WebRTC分析器

这是一个用于分析和播放WebRTC流的工具集，专为SRS流媒体服务器优化。

## 主要功能

- 网页分析：提取WebRTC播放页面中的关键信息
- JavaScript代码分析：下载并分析页面中的JavaScript代码，查找WebRTC相关实现
- WebRTC播放：连接到SRS WebRTC服务器并播放媒体流
- 视频显示：使用OpenCV显示接收到的视频流
- 视频录制：保存接收到的流到MP4文件

## 安装

```bash
# 克隆仓库
git clone https://github.com/a994335223/webrtc-analyzer.git
cd webrtc-analyzer

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 1. 分析网页

```bash
python analyze_page.py https://example.com/players/play.html
```

这将分析指定页面并提取标题、脚本标签、视频标签等信息。

### 2. 分析JavaScript代码

```bash
python download_js.py
```

下载并分析播放页面中引用的JavaScript文件，查找WebRTC相关代码。

### 3. 播放WebRTC流

```bash
# 基础播放（控制台输出）
python srs_player.py https://example.com/players/play.html

# 显示视频
python final_srs_player.py https://example.com/players/play.html --display

# 录制视频
python final_srs_player.py https://example.com/players/play.html --record --output video.mp4

# 无限期播放（直到手动中断）
python final_srs_player.py https://example.com/players/play.html --display --timeout 0
```

## 参数说明

`final_srs_player.py` 支持以下参数：

- `url`：WebRTC播放页面的URL或API URL（必需）
- `--stream`：要播放的流名称（可选）
- `--timeout`：连接超时和播放时长（秒），0表示无限期运行，默认30秒
- `--verbose`：启用详细日志输出
- `--display`：显示视频窗口
- `--record`：录制视频
- `--output`：输出文件名（仅在--record时使用），默认为output.mp4

## 最近修复的问题

### 窗口关闭问题

修复了关闭OpenCV窗口后程序不退出或重新打开窗口的问题。现在点击窗口右上角X按钮将正确关闭程序。主要改进包括：

1. 添加全局变量`exit_program`跟踪退出状态
2. 增加窗口状态检测机制，通过`cv2.getWindowProperty`检查窗口是否仍然打开
3. 实现优雅的进程退出流程，确保所有资源正确释放
4. 使用`asyncio`事件循环机制安全地触发程序退出
5. 确保程序在各种场景下都能正确退出，包括关闭窗口、按ESC键、按Ctrl+C等

## 常见问题

1. **连接失败**：检查URL是否正确，以及是否能在浏览器中正常播放
2. **ICE连接错误**：可能是防火墙问题，尝试使用其他STUN服务器
3. **解码错误**：确保已安装必要的编解码器支持

## 开发者说明

主要文件：
- `analyze_page.py`：网页分析工具
- `download_js.py`：JS下载和分析工具
- `srs_player.py`：基础SRS WebRTC播放器
- `final_srs_player.py`：优化版SRS WebRTC播放器，支持视频显示和录制

## 贡献

欢迎提交问题报告和改进建议！

## 许可

MIT