import asyncio
import json
import sys
import ssl
import os
import argparse
import logging
import time
import re
from urllib.parse import urlparse, urljoin
import ssl

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

try:
    import aiohttp
    from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
    from aiortc.contrib.media import MediaPlayer, MediaRecorder
except ImportError:
    logger.error("缺少必要的依赖，正在安装...")
    import subprocess
    subprocess.check_call([
        "python", "-m", "pip", "install", "aiortc", "aiohttp"
    ])
    import aiohttp
    from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
    from aiortc.contrib.media import MediaPlayer, MediaRecorder

class SRSWebRTCClient:
    def __init__(self, api_url=None, ice_servers=None, timeout=30):
        """
        初始化SRS WebRTC客户端
        
        参数:
            api_url: SRS API的URL（如果为None，将从页面URL自动推断）
            ice_servers: ICE服务器列表（如果为None，使用默认服务器）
            timeout: 连接超时时间（秒）
        """
        # 设置ICE服务器
        if ice_servers is None:
            ice_servers = [RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
        
        # 创建RTCConfiguration对象
        self.rtc_config = RTCConfiguration(iceServers=ice_servers)
        
        # 存储API URL
        self.api_url = api_url
        
        # 存储连接超时时间
        self.timeout = timeout
        
        # 创建SSL上下文（忽略证书验证）
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # 连接状态和统计信息
        self.connection_start_time = None
        self.ice_connection_state = None
        self.connection_state = None
        self.track_stats = {}
        self.received_frames = 0
        self.peer_connection = None
        self.closed = False
        self.recorder = None

    async def extract_api_url(self, webpage_url):
        """从网页中提取SRS WebRTC API URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(webpage_url, ssl=self.ssl_context) as response:
                    if response.status != 200:
                        raise Exception(f"无法加载网页，状态码: {response.status}")
                    
                    html = await response.text()
                    
                    # 尝试找到API URL的不同模式
                    patterns = [
                        r'var\s+url\s*=\s*"([^"]+)"',
                        r'url\s*:\s*"([^"]+)"',
                        r'api_server\s*=\s*"([^"]+)"',
                        r"'([^']*\/api\/v1\/rtc\/.*?)'"
                    ]
                    
                    for pattern in patterns:
                        matches = re.search(pattern, html)
                        if matches:
                            api_endpoint = matches.group(1)
                            logger.info(f"从页面提取到API端点: {api_endpoint}")
                            
                            # 处理相对URL
                            if not api_endpoint.startswith(('http://', 'https://')):
                                parsed_url = urlparse(webpage_url)
                                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                                api_endpoint = urljoin(base_url, api_endpoint)
                            
                            return api_endpoint
                    
                    # 如果没有匹配，使用默认SRS WebRTC端点
                    # SRS通常在端口1985上提供API服务
                    parsed_url = urlparse(webpage_url)
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    default_api = urljoin(base_url, "/rtc/v1/play/")
                    
                    # 尝试修改端口为1985
                    if ':' in parsed_url.netloc:
                        host = parsed_url.netloc.split(':')[0]
                        alt_api = f"{parsed_url.scheme}://{host}:1985/rtc/v1/play/"
                        logger.info(f"未找到API端点，尝试默认URL: {alt_api}")
                        return alt_api
                    else:
                        logger.info(f"未找到API端点，尝试默认URL: {default_api}")
                        return default_api
        
        except Exception as e:
            logger.error(f"提取API URL时出错: {e}")
            # 假设API默认位于同一服务器的/rtc/v1/play/路径
            parsed_url = urlparse(webpage_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            default_api = urljoin(base_url, "/rtc/v1/play/")
            logger.info(f"使用默认API URL: {default_api}")
            return default_api

    async def connect(self, webpage_url, stream_url=None):
        """连接到SRS WebRTC服务器并播放指定的流"""
        # 记录开始时间
        self.connection_start_time = time.time()
        
        # 如果未提供API URL，从网页URL提取
        if self.api_url is None:
            self.api_url = await self.extract_api_url(webpage_url)
            
        logger.info(f"使用API URL: {self.api_url}")
        
        # 如果未提供流URL，尝试从页面URL或API URL中提取
        if stream_url is None:
            parsed_api = urlparse(self.api_url)
            parsed_page = urlparse(webpage_url)
            
            # 尝试从查询参数中提取流名称
            query_params = parsed_page.query.split('&')
            for param in query_params:
                if param.startswith('stream='):
                    stream_url = param.split('=', 1)[1]
                    break
            
            # 如果仍未找到，使用默认流名
            if not stream_url:
                stream_url = "livestream"
            
            logger.info(f"使用流URL: {stream_url}")
        
        # 创建RTCPeerConnection
        self.peer_connection = RTCPeerConnection(configuration=self.rtc_config)
        
        # 设置事件处理器
        @self.peer_connection.on("connectionstatechange")
        async def on_connectionstatechange():
            self.connection_state = self.peer_connection.connectionState
            logger.info(f"连接状态变更: {self.connection_state}")
            if self.connection_state == "failed":
                await self.close()
        
        @self.peer_connection.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            self.ice_connection_state = self.peer_connection.iceConnectionState
            logger.info(f"ICE连接状态变更: {self.ice_connection_state}")
            if self.ice_connection_state == "failed":
                await self.close()
        
        # 处理媒体轨道
        @self.peer_connection.on("track")
        def on_track(track):
            logger.info(f"收到轨道: {track.kind}")
            self.track_stats[track.kind] = {"start_time": time.time(), "frames": 0}
            
            @track.on("ended")
            async def on_ended():
                logger.info(f"轨道结束: {track.kind}")
                
            if track.kind == "video":
                # 如果需要，可以在这里设置视频录制
                pass
        
        # 创建offer
        offer = await self.peer_connection.createOffer()
        await self.peer_connection.setLocalDescription(offer)
        
        # 准备发送给SRS服务器的JSON数据
        data = {
            "api": self.api_url,
            "streamurl": stream_url,
            "sdp": offer.sdp
        }
        
        # 发送offer给SRS服务器
        async with aiohttp.ClientSession() as session:
            try:
                logger.info(f"向服务器发送SDP offer")
                
                async with session.post(
                    self.api_url, 
                    json={"streamurl": stream_url, "sdp": offer.sdp},
                    ssl=self.ssl_context
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"服务器响应错误 {response.status}: {error_text}")
                        return False
                    
                    # 解析响应
                    try:
                        answer_data = await response.json()
                        if "code" in answer_data and answer_data["code"] != 0:
                            logger.error(f"SRS服务器返回错误码: {answer_data['code']}, 消息: {answer_data.get('msg', '未知错误')}")
                            return False
                            
                        sdp = answer_data.get("sdp")
                        if not sdp:
                            logger.error("服务器响应中缺少SDP")
                            return False
                            
                        # 设置远程描述
                        answer = RTCSessionDescription(sdp=sdp, type="answer")
                        await self.peer_connection.setRemoteDescription(answer)
                        logger.info("成功设置远程描述")
                        
                        # 等待连接建立
                        count = 0
                        while count < self.timeout:
                            if self.peer_connection.iceConnectionState == "connected" or \
                               self.peer_connection.iceConnectionState == "completed":
                                logger.info(f"连接成功建立，耗时: {time.time() - self.connection_start_time:.2f}秒")
                                return True
                                
                            if self.peer_connection.iceConnectionState == "failed":
                                logger.error("ICE连接失败")
                                return False
                                
                            await asyncio.sleep(1)
                            count += 1
                            if count % 5 == 0:
                                logger.info(f"等待连接... ({count}秒)")
                                
                        logger.error(f"连接超时，{self.timeout}秒后未建立连接")
                        return False
                        
                    except json.JSONDecodeError:
                        response_text = await response.text()
                        logger.error(f"无法解析JSON响应: {response_text[:200]}...")
                        return False
                        
            except Exception as e:
                logger.error(f"连接过程中出错: {e}")
                return False
    
    async def wait_for_connection(self, timeout=None):
        """等待连接建立或超时"""
        if timeout is None:
            timeout = self.timeout
            
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.peer_connection and (
                self.peer_connection.iceConnectionState == "connected" or
                self.peer_connection.iceConnectionState == "completed"
            ):
                return True
                
            if self.peer_connection and self.peer_connection.iceConnectionState == "failed":
                return False
                
            await asyncio.sleep(0.5)
            
        return False
    
    async def close(self):
        """关闭连接并清理资源"""
        if self.closed:
            return
            
        self.closed = True
        logger.info("正在关闭连接...")
        
        # 关闭录制器（如果有）
        if self.recorder:
            await self.recorder.stop()
            
        # 关闭RTCPeerConnection
        if self.peer_connection:
            await self.peer_connection.close()
            
        # 输出连接统计信息
        if self.connection_start_time:
            duration = time.time() - self.connection_start_time
            logger.info(f"连接总时长: {duration:.2f}秒")
            
        for kind, stats in self.track_stats.items():
            if "start_time" in stats:
                track_duration = time.time() - stats["start_time"]
                logger.info(f"{kind}轨道播放时长: {track_duration:.2f}秒")

async def run_webrtc_client(webpage_url, stream_url=None, record=False, output_file=None, timeout=60):
    """运行WebRTC客户端"""
    # 创建SRS WebRTC客户端
    client = SRSWebRTCClient(timeout=timeout)
    
    try:
        # 连接到服务器
        success = await client.connect(webpage_url, stream_url)
        if not success:
            logger.error("连接服务器失败")
            return False
            
        # 等待指定的时间
        logger.info(f"将保持连接 {timeout} 秒...")
        await asyncio.sleep(timeout)
        
    except KeyboardInterrupt:
        logger.info("用户中断，正在关闭连接...")
    except Exception as e:
        logger.error(f"运行时错误: {e}")
    finally:
        # 关闭连接
        await client.close()
        
    return True

async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="SRS WebRTC流播放器")
    parser.add_argument("url", help="WebRTC播放页面的URL或直接的API URL")
    parser.add_argument("--stream", help="要播放的流名称")
    parser.add_argument("--timeout", type=int, default=30, help="连接超时和播放时长（秒）")
    parser.add_argument("--verbose", action="store_true", help="启用详细日志")
    
    args = parser.parse_args()
    
    # 根据需要设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # 运行WebRTC客户端
    await run_webrtc_client(
        webpage_url=args.url,
        stream_url=args.stream,
        timeout=args.timeout
    )

if __name__ == "__main__":
    # 为Windows设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 运行主函数
    asyncio.run(main())