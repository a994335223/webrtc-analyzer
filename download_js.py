import asyncio
import ssl
import sys
import os
from urllib.parse import urljoin

try:
    import aiohttp
except ImportError:
    print("缺少必要的依赖，正在安装...")
    import subprocess
    subprocess.check_call([
        "python", "-m", "pip", "install", "aiohttp"
    ])
    import aiohttp

async def download_file(session, url, output_dir, base_url):
    """下载文件"""
    # 解析完整URL
    if not url.startswith(('http://', 'https://')):
        url = urljoin(base_url, url)
        
    print(f"下载: {url}")
    
    # 提取文件名
    filename = url.split('/')[-1]
    output_path = os.path.join(output_dir, filename)
    
    # 创建SSL上下文
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        async with session.get(url, ssl=ssl_context) as response:
            if response.status != 200:
                print(f"  下载失败: 状态码 {response.status}")
                return None
            
            content = await response.text()
            
            # 保存文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print(f"  已保存到: {output_path} (大小: {len(content)} 字节)")
            return output_path
            
    except Exception as e:
        print(f"  下载出错: {e}")
        return None

async def main():
    # 基础URL和需下载的JS文件
    base_url = "https://123.56.22.103/players/"
    js_files = [
        "js/srs.sdk.js",
        "js/winlin.utility.js",
        "js/srs.page.js"
    ]
    
    # 创建输出目录
    output_dir = "downloaded_js"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    # 下载文件
    async with aiohttp.ClientSession() as session:
        tasks = []
        for js_file in js_files:
            task = download_file(session, js_file, output_dir, base_url)
            tasks.append(task)
            
        # 等待所有下载完成
        results = await asyncio.gather(*tasks)
        
        # 分析下载的文件
        for path in results:
            if path:
                filename = os.path.basename(path)
                print(f"\n分析: {filename}")
                
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 查找WebRTC相关代码
                webrtc_snippets = []
                
                # 关键词列表
                keywords = [
                    "RTCPeerConnection", "createOffer", "setLocalDescription",
                    "setRemoteDescription", "onicecandidate", "ontrack",
                    "addTransceiver", "addTrack", "getUserMedia",
                    "WebRTC", "SDP", "ICE", "RTC", "newWebRTCUrl"
                ]
                
                # 按行查找关键字
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    for keyword in keywords:
                        if keyword in line:
                            # 获取上下文
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            context = '\n'.join(lines[start:end])
                            
                            # 跳过重复的片段
                            if not any(context in s for s in webrtc_snippets):
                                webrtc_snippets.append(context)
                                break
                
                # 显示找到的片段
                if webrtc_snippets:
                    print(f"  找到 {len(webrtc_snippets)} 个WebRTC相关代码片段:")
                    for i, snippet in enumerate(webrtc_snippets[:10]):  # 只显示前10个片段
                        print(f"\n  片段 {i+1}:")
                        print(f"  {snippet}")
                else:
                    print("  未找到WebRTC相关代码")

if __name__ == "__main__":
    # 为Windows设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 运行主函数
    asyncio.run(main())