# WebRTC分析和播放工具

这个项目提供了一系列工具，用于分析和播放WebRTC流媒体。特别针对SRS（Simple RTMP Server）服务器的WebRTC流进行了优化。

## 文件说明

- `final_srs_player.py` - 最终优化版本的WebRTC视频播放器，支持稳定播放SRS服务器的视频流
- `download_js.py` - 用于下载和分析页面中的JavaScript文件，提取WebRTC相关代码
- `analyze_page.py` - 用于分析网页源代码，查找WebRTC相关信息和API端点
- `requirements.txt` - 项目依赖列表