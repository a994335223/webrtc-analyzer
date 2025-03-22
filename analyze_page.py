import asyncio
import ssl
import sys

try:
    import aiohttp
    from bs4 import BeautifulSoup
except ImportError:
    print("缺少必要的依赖，正在安装...")
    import subprocess
    subprocess.check_call([
        "python", "-m", "pip", "install", 
        "aiohttp", "beautifulsoup4"
    ])
    import aiohttp
    from bs4 import BeautifulSoup

async def fetch_and_analyze(url):
    """获取并分析页面内容"""
    print(f"分析网页: {url}")
    
    # 创建SSL上下文
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, ssl=ssl_context) as response:
                if response.status != 200:
                    print(f"获取页面失败: 状态码 {response.status}")
                    return
                
                html = await response.text()
                print(f"成功获取页面，大小: {len(html)} 字节")
                
                # 解析HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # 分析标题
                title = soup.title.string if soup.title else "无标题"
                print(f"页面标题: {title}")
                
                # 分析JavaScript文件
                script_tags = soup.find_all('script')
                print(f"发现 {len(script_tags)} 个脚本标签")
                
                for i, script in enumerate(script_tags):
                    src = script.get('src')
                    if src:
                        print(f"  外部脚本 {i+1}: {src}")
                    elif script.string:
                        # 如果是内联脚本，找WebRTC相关代码
                        code = script.string
                        code_preview = code[:100].replace('\n', ' ') + "..." if len(code) > 100 else code
                        print(f"  内联脚本 {i+1}: {code_preview}")
                        
                        # 查找WebRTC关键字
                        webrtc_keywords = [
                            "RTCPeerConnection", "createOffer", "setLocalDescription",
                            "setRemoteDescription", "onicecandidate", "ontrack",
                            "addTransceiver", "addTrack", "getUserMedia"
                        ]
                        
                        found_keywords = []
                        for keyword in webrtc_keywords:
                            if keyword in code:
                                found_keywords.append(keyword)
                        
                        if found_keywords:
                            print(f"    WebRTC相关代码: {', '.join(found_keywords)}")
                            
                            # 查找URL或API端点
                            possible_urls = []
                            lines = code.split('\n')
                            for line in lines:
                                if "url" in line.lower() or "fetch" in line.lower() or "ajax" in line.lower() or "http" in line.lower():
                                    possible_urls.append(line.strip())
                            
                            if possible_urls:
                                print("    可能的API端点:")
                                for url_line in possible_urls[:5]:  # 只显示前5个
                                    print(f"      {url_line}")
                
                # 查找video标签
                video_tags = soup.find_all('video')
                print(f"发现 {len(video_tags)} 个视频标签")
                for i, video in enumerate(video_tags):
                    print(f"  视频 {i+1}: ID='{video.get('id')}', Class='{video.get('class')}'")
                    
                # 查找表单和输入框
                forms = soup.find_all('form')
                print(f"发现 {len(forms)} 个表单")
                
                # 查找按钮和控件
                buttons = soup.find_all(['button', 'input[type="button"]', 'a.button'])
                print(f"发现 {len(buttons)} 个按钮或控件")
                
                # 输出完整HTML供分析
                print("\n页面HTML (前1000字符):")
                print(html[:1000] + "...")
                
    except Exception as e:
        print(f"分析过程中出错: {e}")

async def main():
    # 目标URL
    url = "https://123.56.22.103/players/play.html"
    
    try:
        await fetch_and_analyze(url)
    except Exception as e:
        print(f"程序出错: {e}")

if __name__ == "__main__":
    # 为Windows设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 运行主函数
    asyncio.run(main())