# backend/main.py
import sys
from dotenv import load_dotenv
import os
import Dumplings
import uuid
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import queue
import threading
from datetime import datetime
from typing import Dict, List
import traceback

# 加载环境变量
load_dotenv()

# 创建FastAPI应用
app = FastAPI(title="Dumplings Agent协作系统", description="基于Dumplings的多Agent协作系统")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 存储WebSocket连接和输出队列
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.output_queues: Dict[str, queue.Queue] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.output_queues[client_id] = queue.Queue()

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.output_queues:
            del self.output_queues[client_id]

    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    def put_output(self, client_id: str, content: str):
        if client_id in self.output_queues:
            self.output_queues[client_id].put(content)

    def get_output(self, client_id: str):
        if client_id in self.output_queues:
            try:
                return self.output_queues[client_id].get_nowait()
            except queue.Empty:
                return None
        return None


manager = ConnectionManager()

# 创建Agent类管理器
agent_classes = {}


def register_web_agent(uuid_str: str, name: str):
    def decorator(cls):
        Dumplings.register_agent(uuid_str, name)(cls)
        agent_classes[name] = cls
        return cls

    return decorator


# 工具注册
@Dumplings.tool_registry.register_tool(allowed_agents=["8841cd45eef54217bc8122cafebe5fd6", "time_agent"],
                                       name="get_time")
def get_time(xml: str) -> str:
    return datetime.now().strftime("%H:%M")


# 自定义BaseAgent，重写out方法以支持Web输出
class WebAgent(Dumplings.BaseAgent):
    def __init__(self, client_id: str = None):
        self.client_id = client_id
        super().__init__()

    def out(self, content: str):
        """重写输出方法，将输出发送到WebSocket"""
        print(content, end='', flush=True)
        if self.client_id:
            # 将内容拆分为字符，实现逐字输出效果
            for char in content:
                manager.put_output(self.client_id, char)
                # 添加小延迟，使前端显示更自然
                # import time
                # time.sleep(0.01)


# Agent注册 - 使用自定义的WebAgent和固定的UUID
@register_web_agent("scheduling_agent_id_123456", "scheduling_agent")
class scheduling_agent(WebAgent):
    prompt = f"你是一个名为汤圆Agent的AGI，你可以用<ask_for_help><agent_id>id</agent_id><message>message</message></ask_for_help>的方式与其他Agent通讯, 你可以使用<attempt_completion>标签退出对话， 它的语法为<attempt_completion><report_content>放入你想播报的内容，或留空</report_content></attempt_completion>"
    api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model_name = "qwen3-max"
    api_key = os.getenv("API_KEY")

    def __init__(self, client_id: str = None):
        super().__init__(client_id)


@register_web_agent("8841cd45eef54217bc8122cafebe5fd6", "time_agent")
class time_agent(WebAgent):
    prompt = "你是一个名为汤圆Agent的AGI的子agent名为时间管理者，你可以用<ask_for_help><agent_id>id</agent_id><message>message</message></ask_for_help>的方式与其他Agent通讯, 你还有get_time可以查询时间（直接<get_time></get_time>即可）"
    api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model_name = "qwen3-max"
    api_key = os.getenv("API_KEY")

    def __init__(self, client_id: str = None):
        super().__init__(client_id)


# 运行Agent对话的线程函数
def run_agent_conversation(client_id: str, message: str, agent_name: str = "scheduling_agent"):
    """在单独线程中运行Agent对话"""
    try:
        print(f"开始运行Agent对话，client_id: {client_id}, message: {message}")

        # 从我们自己的类管理器中获取Agent类
        agent_class = agent_classes[agent_name]
        agent_instance = agent_class(client_id=client_id)

        print(f"Agent实例创建成功，开始对话...")

        # 运行对话
        result = agent_instance.conversation_with_tool(message)

        print(f"对话完成，结果: {result}")

        # 发送完成信号
        manager.put_output(client_id, f"__COMPLETE__:{result if isinstance(result, str) else '对话完成'}")
    except Exception as e:
        print(f"运行Agent对话时出错: {str(e)}")
        print(traceback.format_exc())
        manager.put_output(client_id, f"__ERROR__:{str(e)}")


# SSE流式端点 - 基于Dumplings Agent系统
@app.get("/sse/collaboration")
async def sse_collaboration(request: Request, message: str = "你好"):
    """
    使用SSE协议提供Dumplings Agent协作服务，默认使用scheduling_agent
    """
    client_id = f"sse_{datetime.now().timestamp()}"

    print(f"收到SSE请求，client_id: {client_id}, message: {message}")

    async def event_generator():
        # 发送连接建立事件
        yield "event: connected\n"
        yield f"data: {json.dumps({'status': 'connected', 'timestamp': datetime.now().isoformat()})}\n\n"

        # 启动Agent对话线程
        thread = threading.Thread(
            target=run_agent_conversation,
            args=(client_id, message, "scheduling_agent"),
            daemon=True
        )
        thread.start()

        print(f"Agent对话线程已启动")

        # 持续发送输出直到完成
        while True:
            if await request.is_disconnected():
                print(f"客户端断开连接")
                break

            output = manager.get_output(client_id)
            if output:
                print(f"从队列获取输出: {output}")
                if output.startswith("__COMPLETE__"):
                    # 对话完成
                    complete_data = output.replace("__COMPLETE__:", "")
                    yield "event: complete\n"
                    yield f"data: {json.dumps({'status': 'complete', 'result': complete_data, 'timestamp': datetime.now().isoformat()})}\n\n"
                    break
                elif output.startswith("__ERROR__"):
                    # 发生错误
                    error_data = output.replace("__ERROR__:", "")
                    yield "event: error\n"
                    yield f"data: {json.dumps({'status': 'error', 'message': error_data, 'timestamp': datetime.now().isoformat()})}\n\n"
                    break
                else:
                    # 正常输出 - 直接发送字符
                    yield "event: message\n"
                    yield f"data: {json.dumps({'content': output, 'timestamp': datetime.now().isoformat()})}\n\n"
            else:
                await asyncio.sleep(0.1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            "Access-Control-Expose-Headers": "*"
        }
    )


# WebSocket端点 - 提供实时双向通信
@app.websocket("/ws/collaboration")
async def websocket_collaboration(websocket: WebSocket):
    await websocket.accept()
    client_id = f"ws_{datetime.now().timestamp()}"

    try:
        # 等待客户端发送消息
        data = await websocket.receive_text()
        message_data = json.loads(data)
        user_message = message_data.get("message", "你好")

        print(f"收到WebSocket消息，client_id: {client_id}, message: {user_message}")

        # 启动Agent对话线程
        thread = threading.Thread(
            target=run_agent_conversation,
            args=(client_id, user_message, "scheduling_agent"),
            daemon=True
        )
        thread.start()

        # 持续发送输出直到完成
        while True:
            output = manager.get_output(client_id)
            if output:
                if output.startswith("__COMPLETE__"):
                    # 对话完成
                    complete_data = output.replace("__COMPLETE__:", "")
                    await websocket.send_json({
                        "type": "complete",
                        "data": complete_data,
                        "timestamp": datetime.now().isoformat()
                    })
                    break
                elif output.startswith("__ERROR__"):
                    # 发生错误
                    error_data = output.replace("__ERROR__:", "")
                    await websocket.send_json({
                        "type": "error",
                        "data": error_data,
                        "timestamp": datetime.now().isoformat()
                    })
                    break
                else:
                    # 正常输出
                    await websocket.send_json({
                        "type": "message",
                        "data": output,
                        "timestamp": datetime.now().isoformat()
                    })
            else:
                await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        print(f"WebSocket客户端断开连接: {client_id}")
    except Exception as e:
        print(f"WebSocket处理错误: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "data": str(e),
            "timestamp": datetime.now().isoformat()
        })
    finally:
        manager.disconnect(client_id)


# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# 服务器信息
@app.get("/info")
async def server_info():
    return {
        "name": "Dumplings Agent协作系统",
        "version": "1.0",
        "protocols": ["Server-Sent Events (SSE)", "WebSocket"],
        "endpoints": {
            "sse_collaboration": "/sse/collaboration?message=你的消息",
            "websocket_collaboration": "/ws/collaboration",
            "web_interface": "/"
        }
    }


# 提供前端页面 - 直接返回HTML内容
@app.get("/")
async def read_index():
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dumplings Agent协作系统</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }

            body {
                background: linear-gradient(135deg, #1a2a6c, #b21f1f, #fdbb2d);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
                overflow-x: hidden;
            }

            .container {
                width: 100%;
                max-width: 900px;
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                overflow: hidden;
                display: flex;
                flex-direction: column;
                border: 2px solid #333;
                animation: containerAppear 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            }

            @keyframes containerAppear {
                0% {
                    opacity: 0;
                    transform: translateY(30px) scale(0.95);
                }
                100% {
                    opacity: 1;
                    transform: translateY(0) scale(1);
                }
            }

            .header {
                background: linear-gradient(to right, #4e54c8, #8f94fb);
                color: white;
                padding: 15px;
                text-align: center;
                border-bottom: 2px solid #333;
                position: relative;
                overflow: hidden;
            }

            .header::before {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: linear-gradient(to right, transparent, rgba(255,255,255,0.1), transparent);
                transform: rotate(30deg);
                animation: shimmer 8s infinite linear;
            }

            @keyframes shimmer {
                0% { transform: translateX(-100%) rotate(30deg); }
                100% { transform: translateX(100%) rotate(30deg); }
            }

            .header h1 {
                font-size: 1.8rem;
                margin-bottom: 5px;
                position: relative;
                animation: titleGlow 3s infinite alternate;
            }

            @keyframes titleGlow {
                0% { text-shadow: 0 0 5px rgba(255,255,255,0.5); }
                100% { text-shadow: 0 0 15px rgba(255,255,255,0.8); }
            }

            .header p {
                font-size: 1rem;
                opacity: 0.9;
                position: relative;
            }

            .protocol-selector {
                padding: 10px 15px;
                background-color: #f0f0f0;
                border-bottom: 1px solid #ddd;
                display: flex;
                gap: 10px;
            }

            .protocol-btn {
                padding: 5px 10px;
                border: 1px solid #4e54c8;
                background: white;
                color: #4e54c8;
                border-radius: 3px;
                cursor: pointer;
                transition: all 0.3s;
            }

            .protocol-btn.active {
                background: #4e54c8;
                color: white;
            }

            .input-section {
                padding: 15px;
                border-bottom: 2px solid #333;
                background-color: white;
            }

            .user-input-box {
                border: 2px solid #333;
                border-radius: 5px;
                padding: 10px;
                background-color: #f9f9f9;
                transition: all 0.3s ease;
                transform-origin: center;
            }

            .user-input-box:focus-within {
                border-color: #4e54c8;
                box-shadow: 0 0 0 3px rgba(78, 84, 200, 0.2);
                transform: scale(1.01);
            }

            .user-input {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 1rem;
                outline: none;
                resize: vertical;
                min-height: 60px;
                background-color: white;
                transition: all 0.3s ease;
            }

            .user-input:focus {
                border-color: #4e54c8;
                box-shadow: 0 0 5px rgba(78, 84, 200, 0.3);
            }

            .input-controls {
                display: flex;
                justify-content: space-between;
                margin-top: 10px;
            }

            .send-btn {
                background: linear-gradient(to right, #4e54c8, #8f94fb);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                cursor: pointer;
                font-size: 0.9rem;
                transition: all 0.3s;
                position: relative;
                overflow: hidden;
            }

            .send-btn::after {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 5px;
                height: 5px;
                background: rgba(255, 255, 255, 0.5);
                opacity: 0;
                border-radius: 100%;
                transform: scale(1, 1) translate(-50%);
                transform-origin: 50% 50%;
            }

            .send-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(78, 84, 200, 0.4);
            }

            .send-btn:active::after {
                animation: ripple 0.6s ease-out;
            }

            @keyframes ripple {
                0% {
                    transform: scale(0, 0);
                    opacity: 0.5;
                }
                100% {
                    transform: scale(20, 20);
                    opacity: 0;
                }
            }

            .conversation-section {
                display: flex;
                flex-direction: column;
                padding: 15px;
                gap: 15px;
                flex: 1;
                min-height: 400px;
                background-color: #f9f9f9;
            }

            .single-conversation {
                display: flex;
                flex-direction: column;
                flex: 1;
            }

            .single-ai-box {
                flex: 1;
                border: 2px solid #333;
                border-radius: 5px;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                background-color: white;
                transition: all 0.3s ease;
                transform-origin: center;
            }

            .ai-header {
                background: linear-gradient(to right, #4e54c8, #8f94fb);
                color: white;
                padding: 10px;
                display: flex;
                align-items: center;
                border-bottom: 2px solid #333;
                position: relative;
                overflow: hidden;
            }

            .ai-header::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                transform: translateX(-100%);
            }

            .ai-header.active::after {
                animation: headerShine 2s ease-in-out;
            }

            @keyframes headerShine {
                0% { transform: translateX(-100%); }
                50% { transform: translateX(100%); }
                100% { transform: translateX(100%); }
            }

            .ai-avatar {
                width: 30px;
                height: 30px;
                border-radius: 50%;
                background-color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                margin-right: 10px;
                font-weight: bold;
                color: #4e54c8;
                border: 1px solid #333;
                animation: avatarPulse 2s infinite;
            }

            @keyframes avatarPulse {
                0% { box-shadow: 0 0 0 0 rgba(78, 84, 200, 0.4); }
                70% { box-shadow: 0 0 0 10px rgba(78, 84, 200, 0); }
                100% { box-shadow: 0 0 0 0 rgba(78, 84, 200, 0); }
            }

            .ai-name {
                font-weight: bold;
                font-size: 1rem;
            }

            .ai-conversation {
                flex: 1;
                padding: 10px;
                overflow-y: auto;
                background-color: #f9f9f9;
                min-height: 300px;
                display: flex;
                flex-direction: column;
            }

            .message {
                margin-bottom: 10px;
                padding: 8px 12px;
                border-radius: 5px;
                max-width: 90%;
                animation: messageAppear 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                font-size: 0.9rem;
                transform-origin: left;
            }

            @keyframes messageAppear {
                0% {
                    opacity: 0;
                    transform: translateY(20px) scale(0.9);
                }
                100% {
                    opacity: 1;
                    transform: translateY(0) scale(1);
                }
            }

            .ai-message {
                background-color: #e5e5ea;
                align-self: flex-start;
                position: relative;
            }

            .ai-message::before {
                content: '';
                position: absolute;
                left: -8px;
                top: 10px;
                width: 0;
                height: 0;
                border-top: 8px solid transparent;
                border-bottom: 8px solid transparent;
                border-right: 8px solid #e5e5ea;
            }

            .user-message {
                background-color: #007bff;
                color: white;
                align-self: flex-end;
                position: relative;
                animation-delay: 0.1s;
            }

            .user-message::after {
                content: '';
                position: absolute;
                right: -8px;
                top: 10px;
                width: 0;
                height: 0;
                border-top: 8px solid transparent;
                border-bottom: 8px transparent;
                border-left: 8px solid #007bff;
            }

            .typing-indicator {
                display: flex;
                align-items: center;
                margin-top: 5px;
                animation: fadeIn 0.3s ease;
            }

            .typing-dots {
                display: flex;
                margin-left: 10px;
            }

            .typing-dot {
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background-color: #999;
                margin: 0 2px;
                animation: typing 1.4s infinite ease-in-out;
            }

            .typing-dot:nth-child(1) {
                animation-delay: -0.32s;
            }

            .typing-dot:nth-child(2) {
                animation-delay: -0.16s;
            }

            @keyframes typing {
                0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
                40% { transform: scale(1); opacity: 1; }
            }

            .status-bar {
                padding: 8px 15px;
                background-color: #f0f0f0;
                border-top: 2px solid #333;
                display: flex;
                justify-content: space-between;
                font-size: 0.8rem;
                color: #666;
            }

            .connection-status {
                display: flex;
                align-items: center;
            }

            .status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: #4CAF50;
                margin-right: 6px;
                animation: statusPulse 2s infinite;
            }

            @keyframes statusPulse {
                0% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7); }
                70% { box-shadow: 0 0 0 5px rgba(76, 175, 80, 0); }
                100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0); }
            }

            .disconnected {
                background-color: #f44336 !important;
            }

            @media (max-width: 768px) {
                .container {
                    max-width: 100%;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🥟 Dumplings Agent协作系统</h1>
                <p>基于Dumplings的多Agent协作对话系统 - 默认使用Scheduling Agent</p>
            </div>

            <div class="protocol-selector">
                <button class="protocol-btn active" id="sseBtn">SSE协议</button>
                <button class="protocol-btn" id="wsBtn">WebSocket协议</button>
            </div>

            <div class="input-section">
                <div class="user-input-box">
                    <textarea class="user-input" id="userInput" placeholder="输入您想要与Scheduling Agent对话的内容..."></textarea>
                </div>
                <div class="input-controls">
                    <div>
                        <button class="send-btn" id="clearBtn">清空对话</button>
                    </div>
                    <button class="send-btn" id="sendBtn">发送消息</button>
                </div>
            </div>

            <div class="conversation-section">
                <div class="single-conversation" id="singleConversation">
                    <div class="single-ai-box" id="singleAiBox">
                        <div class="ai-header">
                            <div class="ai-avatar">AI</div>
                            <div class="ai-name">Scheduling Agent</div>
                        </div>
                        <div class="ai-conversation" id="aiSingleConversation">
                            <div class="message ai-message">
                                <div class="message-text">您好！我是Scheduling Agent。我可以处理您的问题，并在需要时召唤其他Agent提供专业支持。</div>
                            </div>
                        </div>
                        <div class="typing-indicator" id="aiSingleTyping" style="display: none;">
                            <div class="ai-avatar" style="width:25px;height:25px;font-size:0.8rem;">AI</div>
                            <div class="typing-dots">
                                <div class="typing-dot"></div>
                                <div class="typing-dot"></div>
                                <div class="typing-dot"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="status-bar">
                <div class="connection-status">
                    <div class="status-dot" id="statusDot"></div>
                    <span id="connectionStatus">准备就绪</span>
                </div>
                <div>Dumplings Agent协作系统 v1.0</div>
            </div>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', function() {
                const userInput = document.getElementById('userInput');
                const sendBtn = document.getElementById('sendBtn');
                const clearBtn = document.getElementById('clearBtn');
                const aiSingleConversation = document.getElementById('aiSingleConversation');
                const statusDot = document.getElementById('statusDot');
                const connectionStatus = document.getElementById('connectionStatus');
                const sseBtn = document.getElementById('sseBtn');
                const wsBtn = document.getElementById('wsBtn');

                let eventSource = null;
                let websocket = null;
                let currentProtocol = 'sse'; // 默认使用SSE
                let currentBuffer = '';

                // 协议切换
                sseBtn.addEventListener('click', function() {
                    currentProtocol = 'sse';
                    sseBtn.classList.add('active');
                    wsBtn.classList.remove('active');
                    connectionStatus.textContent = '已切换到SSE协议';
                });

                wsBtn.addEventListener('click', function() {
                    currentProtocol = 'ws';
                    wsBtn.classList.add('active');
                    sseBtn.classList.remove('active');
                    connectionStatus.textContent = '已切换到WebSocket协议';
                });

                // 发送消息函数
                function sendMessage() {
                    const messageText = userInput.value.trim();
                    if (messageText === '') return;

                    // 添加用户消息
                    addMessage(aiSingleConversation, 'user', messageText);

                    // 清空输入框
                    userInput.value = '';

                    // 禁用发送按钮
                    sendBtn.disabled = true;

                    // 更新状态
                    statusDot.style.backgroundColor = '#FF9800';
                    connectionStatus.textContent = '正在与Agent对话...';

                    // 显示输入指示器
                    showTypingIndicator('aiSingleTyping');

                    // 根据协议选择连接方式
                    if (currentProtocol === 'sse') {
                        connectSSE(messageText);
                    } else {
                        connectWebSocket(messageText);
                    }
                }

                // 连接SSE端点
                function connectSSE(message) {
                    if (eventSource) {
                        eventSource.close();
                    }

                    currentBuffer = '';

                    eventSource = new EventSource(`/sse/collaboration?message=${encodeURIComponent(message)}`);

                    eventSource.addEventListener('connected', function(event) {
                        console.log('SSE连接已建立');
                        statusDot.style.backgroundColor = '#4CAF50';
                        connectionStatus.textContent = '已连接到Agent服务';
                    });

                    eventSource.addEventListener('message', function(event) {
                        const data = JSON.parse(event.data);
                        currentBuffer += data.content;

                        // 更新消息显示
                        updateMessageDisplay(currentBuffer);
                    });

                    eventSource.addEventListener('complete', function(event) {
                        const data = JSON.parse(event.data);
                        console.log('SSE对话已完成:', data);

                        // 隐藏输入指示器
                        hideTypingIndicator('aiSingleTyping');

                        // 标记消息完成
                        completeMessage();

                        statusDot.style.backgroundColor = '#4CAF50';
                        connectionStatus.textContent = '对话完成';
                        sendBtn.disabled = false;

                        if (eventSource) {
                            eventSource.close();
                            eventSource = null;
                        }
                    });

                    eventSource.addEventListener('error', function(event) {
                        const data = JSON.parse(event.data);
                        console.error('SSE错误:', data);

                        // 隐藏输入指示器
                        hideTypingIndicator('aiSingleTyping');

                        // 添加错误消息
                        addMessage(aiSingleConversation, 'ai', `发生错误: ${data.message}`);

                        statusDot.style.backgroundColor = '#f44336';
                        connectionStatus.textContent = '对话错误';
                        sendBtn.disabled = false;

                        if (eventSource) {
                            eventSource.close();
                            eventSource = null;
                        }
                    });

                    eventSource.onerror = function(event) {
                        console.error('SSE连接错误:', event);
                        statusDot.style.backgroundColor = '#f44336';
                        connectionStatus.textContent = '连接错误';
                        sendBtn.disabled = false;

                        if (eventSource) {
                            eventSource.close();
                            eventSource = null;
                        }
                    };
                }

                // 连接WebSocket端点
                function connectWebSocket(message) {
                    if (websocket) {
                        websocket.close();
                    }

                    currentBuffer = '';

                    websocket = new WebSocket(`ws://${window.location.host}/ws/collaboration`);

                    websocket.onopen = function(event) {
                        console.log('WebSocket连接已建立');
                        statusDot.style.backgroundColor = '#4CAF50';
                        connectionStatus.textContent = '已连接到Agent服务';

                        // 发送消息
                        websocket.send(JSON.stringify({
                            message: message
                        }));
                    };

                    websocket.onmessage = function(event) {
                        const data = JSON.parse(event.data);

                        if (data.type === 'message') {
                            currentBuffer += data.data;
                            updateMessageDisplay(currentBuffer);
                        } else if (data.type === 'complete') {
                            // 隐藏输入指示器
                            hideTypingIndicator('aiSingleTyping');

                            // 标记消息完成
                            completeMessage();

                            statusDot.style.backgroundColor = '#4CAF50';
                            connectionStatus.textContent = '对话完成';
                            sendBtn.disabled = false;

                            websocket.close();
                            websocket = null;
                        } else if (data.type === 'error') {
                            // 隐藏输入指示器
                            hideTypingIndicator('aiSingleTyping');

                            // 添加错误消息
                            addMessage(aiSingleConversation, 'ai', `发生错误: ${data.data}`);

                            statusDot.style.backgroundColor = '#f44336';
                            connectionStatus.textContent = '对话错误';
                            sendBtn.disabled = false;

                            websocket.close();
                            websocket = null;
                        }
                    };

                    websocket.onerror = function(event) {
                        console.error('WebSocket错误:', event);
                        statusDot.style.backgroundColor = '#f44336';
                        connectionStatus.textContent = '连接错误';
                        sendBtn.disabled = false;
                    };

                    websocket.onclose = function(event) {
                        console.log('WebSocket连接已关闭');
                        if (sendBtn.disabled) {
                            statusDot.style.backgroundColor = '#f44336';
                            connectionStatus.textContent = '连接已断开';
                            sendBtn.disabled = false;
                        }
                    };
                }

                // 更新消息显示
                function updateMessageDisplay(content) {
                    // 查找或创建消息元素
                    let messageElement = aiSingleConversation.querySelector('.ai-message:last-child');
                    if (!messageElement || messageElement.classList.contains('completed')) {
                        messageElement = document.createElement('div');
                        messageElement.className = 'message ai-message';
                        aiSingleConversation.appendChild(messageElement);
                    }

                    // 更新消息内容
                    const messageTextDiv = messageElement.querySelector('.message-text');
                    if (messageTextDiv) {
                        messageTextDiv.textContent = content;
                    } else {
                        const newMessageTextDiv = document.createElement('div');
                        newMessageTextDiv.className = 'message-text';
                        newMessageTextDiv.textContent = content;
                        messageElement.appendChild(newMessageTextDiv);
                    }

                    // 滚动到底部
                    aiSingleConversation.scrollTop = aiSingleConversation.scrollHeight;
                }

                // 标记消息完成
                function completeMessage() {
                    const messageElement = aiSingleConversation.querySelector('.ai-message:last-child');
                    if (messageElement) {
                        messageElement.classList.add('completed');
                    }
                }

                // 添加消息到对话容器
                function addMessage(conversationElement, sender, text) {
                    const messageDiv = document.createElement('div');
                    messageDiv.className = `message ${sender}-message`;

                    const messageTextDiv = document.createElement('div');
                    messageTextDiv.className = 'message-text';
                    messageTextDiv.textContent = text;

                    messageDiv.appendChild(messageTextDiv);

                    conversationElement.appendChild(messageDiv);

                    // 滚动到底部
                    conversationElement.scrollTop = conversationElement.scrollHeight;
                }

                // 显示输入指示器
                function showTypingIndicator(typingId) {
                    const typingIndicator = document.getElementById(typingId);
                    if (typingIndicator) {
                        typingIndicator.style.display = 'flex';

                        // 滚动到底部
                        const conversationElement = typingIndicator.parentElement.querySelector('.ai-conversation');
                        if (conversationElement) {
                            conversationElement.scrollTop = conversationElement.scrollHeight;
                        }
                    }
                }

                // 隐藏输入指示器
                function hideTypingIndicator(typingId) {
                    const typingIndicator = document.getElementById(typingId);
                    if (typingIndicator) {
                        typingIndicator.style.display = 'none';
                    }
                }

                // 清空对话
                function clearConversations() {
                    // 添加淡出动画
                    aiSingleConversation.style.opacity = '0.5';

                    setTimeout(() => {
                        aiSingleConversation.innerHTML = '';

                        // 添加初始消息
                        const initialMsg = document.createElement('div');
                        initialMsg.className = 'message ai-message';
                        initialMsg.innerHTML = '<div class="message-text">您好！我是Scheduling Agent。我可以处理您的问题，并在需要时召唤其他Agent提供专业支持。</div>';
                        aiSingleConversation.appendChild(initialMsg);

                        // 重置状态
                        statusDot.style.backgroundColor = '#4CAF50';
                        connectionStatus.textContent = '准备就绪';
                        sendBtn.disabled = false;

                        // 关闭连接
                        if (eventSource) {
                            eventSource.close();
                            eventSource = null;
                        }
                        if (websocket) {
                            websocket.close();
                            websocket = null;
                        }

                        // 恢复不透明度
                        aiSingleConversation.style.opacity = '1';
                    }, 300);
                }

                // 事件监听器
                sendBtn.addEventListener('click', sendMessage);

                clearBtn.addEventListener('click', clearConversations);

                userInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                    }
                });
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    import time  # 添加time模块用于延迟

    # 使用字符串方式启用热重载
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)