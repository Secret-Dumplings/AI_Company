#!/usr/bin/env python3
"""
Agent SSE 服务器 - 直接使用 Dumplings.agent_list 中的实例
"""

import sys
import os
import json
import queue
import threading
import logging
import uuid
import time
import traceback
import copy

from dotenv import load_dotenv
from flask import Flask, request, Response, jsonify, render_template_string

# ==================== 检查依赖 ====================
try:
    from bs4 import BeautifulSoup
    import lxml  # 检查lxml是否安装

    logger = logging.getLogger(__name__)
except ImportError as e:
    print(f"缺少依赖库: {e}")
    print("请安装缺少的依赖: pip install lxml beautifulsoup4")
    sys.exit(1)

# ==================== 加载环境变量 ====================
load_dotenv()

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 导入 Dumplings 库 ====================
try:
    import Dumplings

    logger.info("成功导入 Dumplings 库")
except ImportError as e:
    logger.error(f"导入 Dumplings 库失败: {e}")
    print("请确保 Dumplings 库已正确安装")
    sys.exit(1)


# ==================== SSE Agent 包装器 ====================
class SSEAgentWrapper:
    """将 Dumplings Agent 实例包装为支持 SSE 的版本"""

    def __init__(self, agent_instance, sse_queue: queue.Queue = None):
        """
        初始化 SSE 包装器

        Args:
            agent_instance: Dumplings Agent 实例（从 Dumplings.agent_list 获取）
            sse_queue: SSE 消息队列
        """
        # 存储原始 Agent 实例
        self.agent = agent_instance
        self.sse_queue = sse_queue

        # 保存原始的 out 方法
        self.original_out = agent_instance.out

        # 获取 Agent 信息
        self.uuid = getattr(agent_instance, 'uuid', str(uuid.uuid4()))
        self.name = getattr(agent_instance, 'name', 'unknown_agent')

        # 替换 out 方法为 SSE 版本
        agent_instance.out = self.sse_out

        logger.info(f"创建 SSEAgentWrapper: {self.name}, UUID: {self.uuid}")

    def sse_out(self, content):
        """
        SSE 版本的 out 方法
        将输出发送到 SSE 队列而不是打印
        """
        if self.sse_queue is not None:
            try:
                # 确保包含 agent 信息
                if 'ai_uuid' not in content:
                    content['ai_uuid'] = self.uuid
                if 'ai_name' not in content:
                    content['ai_name'] = self.name

                # 发送到 SSE 队列
                self.sse_queue.put(content)

                # 记录日志
                if content.get("tool_name"):
                    logger.info(f"调用工具: {content.get('tool_name')}")
                elif content.get("message") and not content.get("task"):
                    # 只记录长度，避免日志过长
                    msg = content.get("message", "")
                    if msg and msg.strip():
                        logger.info(f"AI回复长度: {len(msg)} 字符")
            except Exception as e:
                logger.error(f"发送到 SSE 队列失败: {e}")
                logger.error(f"失败的内容: {content}")
        else:
            # 如果没有 SSE 队列，使用原始输出
            self.original_out(content)

    def conversation_with_tool(self, message=None):
        """代理 conversation_with_tool 方法"""
        try:
            return self.agent.conversation_with_tool(message)
        except Exception as e:
            logger.error(f"对话执行错误: {e}")
            logger.error(traceback.format_exc())

            # 发送错误信息到 SSE
            if self.sse_queue:
                self.sse_queue.put({
                    "type": "error",
                    "message": f"对话执行错误: {str(e)}",
                    "ai_uuid": self.uuid,
                    "ai_name": self.name
                })
            raise


# ==================== Agent 服务器管理器 ====================
class AgentServer:
    """管理 Agent 实例和 SSE 队列"""

    def __init__(self):
        self.agent_instances = {}
        self.user_queues = {}
        logger.info("AgentServer 初始化完成")

    def get_or_create_agent(self, uid: str, agent_name: str = "scheduling_agent"):
        """
        获取或创建用户的 Agent 实例

        Args:
            uid: 用户ID
            agent_name: Agent 名称

        Returns:
            SSEAgentWrapper 实例或 None
        """
        agent_key = f"{uid}_{agent_name}"

        if agent_key not in self.agent_instances:
            # 创建 SSE 队列
            if uid not in self.user_queues:
                self.user_queues[uid] = queue.Queue()
                logger.info(f"为用户 {uid} 创建 SSE 队列")

            q = self.user_queues[uid]

            try:
                # 从 Dumplings.agent_list 获取 Agent 实例（已经是实例化的对象）
                agent_instance = Dumplings.agent_list.get(agent_name)
                if not agent_instance:
                    logger.error(f"未找到 Agent: {agent_name}")
                    return None

                # 创建 Agent 的深拷贝，避免状态共享
                # 注意：这里需要根据实际情况决定是否需要深拷贝
                # 如果 Agent 有复杂状态，可能需要深拷贝
                try:
                    # 尝试深拷贝
                    agent_copy = copy.deepcopy(agent_instance)
                except Exception as copy_error:
                    logger.warning(f"深拷贝 Agent 失败，使用原始实例: {copy_error}")
                    # 如果深拷贝失败，使用原始实例但重置状态
                    agent_copy = agent_instance
                    # 重置对话历史
                    if hasattr(agent_copy, 'history'):
                        # 保留系统提示，但清空对话历史
                        original_prompt = getattr(agent_copy, 'prompt', '') + f", 你的uuid {agent_copy.uuid}"
                        agent_copy.history = [{"role": "system", "content": original_prompt}]

                # 创建 SSE 包装器
                sse_agent = SSEAgentWrapper(agent_copy, sse_queue=q)
                self.agent_instances[agent_key] = sse_agent
                logger.info(f"为 {uid} 创建 {agent_name} 的 SSE 包装器")

            except Exception as e:
                logger.error(f"创建 Agent 包装器失败: {e}")
                logger.error(traceback.format_exc())
                return None

        return self.agent_instances[agent_key]

    def process_message(self, uid: str, message: str, agent_name: str = "scheduling_agent"):
        """
        处理用户消息

        Args:
            uid: 用户ID
            message: 用户消息
            agent_name: Agent 名称

        Returns:
            bool: 处理是否成功
        """
        try:
            logger.info(f"处理消息: 用户={uid}, Agent={agent_name}, 消息={message}")

            # 获取 Agent
            agent_wrapper = self.get_or_create_agent(uid, agent_name)
            if not agent_wrapper:
                # 发送错误信息到用户队列
                if uid in self.user_queues:
                    self.user_queues[uid].put({
                        "type": "error",
                        "message": f"无法创建或找到 {agent_name} Agent"
                    })
                return False

            # 在新线程中运行对话
            def run_conversation():
                try:
                    logger.info(f"开始对话: {message}")
                    result = agent_wrapper.conversation_with_tool(message)
                    logger.info(f"对话完成: {message}")

                    # 如果需要，可以发送完成消息
                    if uid in self.user_queues:
                        self.user_queues[uid].put({
                            "type": "completion",
                            "message": "对话已完成",
                            "result_type": str(type(result))
                        })

                    return result
                except Exception as e:
                    logger.error(f"对话执行错误: {e}")
                    logger.error(traceback.format_exc())

                    if uid in self.user_queues:
                        self.user_queues[uid].put({
                            "type": "error",
                            "message": f"对话执行错误: {str(e)}"
                        })

            thread = threading.Thread(target=run_conversation)
            thread.daemon = True
            thread.start()

            return True

        except Exception as e:
            logger.error(f"处理消息错误: {e}")
            logger.error(traceback.format_exc())
            return False


# ==================== 创建 Flask 应用和 AgentServer ====================
app = Flask(__name__)
agent_server = AgentServer()


# ==================== 主页 ====================
@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agent 对话系统</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; }
            #messages { border: 1px solid #ddd; padding: 15px; height: 500px; overflow-y: auto; margin-bottom: 15px; 
                       border-radius: 5px; background: #f9f9f9; }
            .user { color: #0066cc; margin: 8px 0; padding: 8px 12px; background: #e6f2ff; border-radius: 10px; 
                   border-left: 4px solid #0066cc; }
            .ai { color: #008000; margin: 8px 0; padding: 8px 12px; background: #e6ffe6; border-radius: 10px;
                 border-left: 4px solid #008000; white-space: pre-wrap; word-wrap: break-word; }
            .tool { color: #cc6600; margin: 8px 0; padding: 8px 12px; background: #fff2e6; border-radius: 10px;
                   border-left: 4px solid #cc6600; }
            .error { color: #cc0000; margin: 8px 0; padding: 8px 12px; background: #ffe6e6; border-radius: 10px;
                    border-left: 4px solid #cc0000; }
            .info { color: #666; margin: 8px 0; padding: 8px 12px; background: #f0f0f0; border-radius: 10px;
                   border-left: 4px solid #666; }
            .input-group { display: flex; gap: 10px; margin-bottom: 15px; }
            input { flex: 1; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; }
            input:focus { outline: none; border-color: #0066cc; }
            button { padding: 12px 20px; background: #0066cc; color: white; border: none; 
                     border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; }
            button:hover { background: #0052a3; }
            button:active { transform: translateY(1px); }
            .agent-buttons { display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
            .agent-btn { background: #666; }
            .agent-btn.active { background: #0066cc; }
            .status { color: #666; font-style: italic; margin-top: 10px; padding: 8px; background: #f0f0f0; 
                     border-radius: 5px; }
            #uid-display { font-weight: bold; color: #0066cc; }
            .message-header { font-size: 12px; color: #888; margin-bottom: 2px; }
        </style>
    </head>
    <body>
        <h1>🤖 Agent 对话系统</h1>

        <div class="status">
            用户ID: <span id="uid-display"></span> | 
            当前Agent: <span id="agent-display">scheduling_agent</span>
        </div>

        <div class="agent-buttons">
            <button class="agent-btn active" onclick="switchAgent('scheduling_agent')">📅 调度 Agent</button>
            <button class="agent-btn" onclick="switchAgent('time_agent')">⏰ 时间 Agent</button>
            <button onclick="clearMessages()" style="background: #999;">🗑️ 清空对话</button>
            <button onclick="testConnection()" style="background: #28a745;">🔗 测试连接</button>
        </div>

        <div id="messages">
            <div class="info">欢迎使用 Agent 对话系统！请选择 Agent 并开始对话。</div>
        </div>

        <div class="input-group">
            <input type="text" id="input" placeholder="输入消息..." autocomplete="off">
            <button onclick="sendMessage()">发送</button>
        </div>

        <script>
            let uid = localStorage.getItem('agent_user_id') || ('user_' + Date.now());
            let currentAgent = 'scheduling_agent';
            let eventSource = null;

            // 显示用户ID和当前Agent
            document.getElementById('uid-display').textContent = uid;
            localStorage.setItem('agent_user_id', uid);

            // 连接 SSE
            function connectSSE() {
                if (eventSource) {
                    eventSource.close();
                }

                eventSource = new EventSource('/stream?uid=' + uid);

                eventSource.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        displayMessage(data);
                    } catch (e) {
                        console.error('解析消息失败:', e, '原始数据:', event.data);
                        addErrorMessage('解析消息失败: ' + e.message);
                    }
                };

                eventSource.onerror = function(error) {
                    console.log('SSE连接错误:', error);
                    addErrorMessage('SSE连接错误，尝试重新连接...');
                    setTimeout(connectSSE, 3000);
                };
            }

            // 显示消息
            function displayMessage(data) {
                const messagesDiv = document.getElementById('messages');

                // 创建消息容器
                const msgDiv = document.createElement('div');

                // 根据消息类型设置样式
                if (data.type === 'error') {
                    msgDiv.className = 'error';
                    msgDiv.innerHTML = `<div class="message-header">❌ 错误</div><strong>${data.message || '未知错误'}</strong>`;
                } else if (data.tool_name) {
                    msgDiv.className = 'tool';
                    msgDiv.innerHTML = `<div class="message-header">🛠️ 工具调用</div>
                                       <strong>${data.tool_name}</strong>`;
                    if (data.tool_parameter) {
                        msgDiv.innerHTML += `<br><small>参数: ${JSON.stringify(data.tool_parameter)}</small>`;
                    }
                    if (data.ai_name) {
                        msgDiv.innerHTML += `<br><small>来自: ${data.ai_name} (${data.ai_uuid})</small>`;
                    }
                } else if (data.message && !data.task) {
                    msgDiv.className = 'ai';
                    let agentInfo = data.ai_name ? `${data.ai_name}` : currentAgent;
                    msgDiv.innerHTML = `<div class="message-header">🤖 ${agentInfo}</div>${data.message}`;
                } else if (data.task) {
                    msgDiv.className = 'info';
                    msgDiv.textContent = '✅ 任务完成';
                } else if (data.type === 'connect') {
                    msgDiv.className = 'info';
                    msgDiv.textContent = `🔗 ${data.message}`;
                } else if (data.type === 'completion') {
                    msgDiv.className = 'info';
                    msgDiv.textContent = `✅ ${data.message}`;
                } else {
                    msgDiv.className = 'info';
                    msgDiv.textContent = JSON.stringify(data);
                }

                messagesDiv.appendChild(msgDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }

            // 添加错误消息
            function addErrorMessage(text) {
                const messagesDiv = document.getElementById('messages');
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error';
                errorDiv.innerHTML = `<div class="message-header">❌ 系统错误</div>${text}`;
                messagesDiv.appendChild(errorDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }

            // 发送消息
            function sendMessage() {
                const input = document.getElementById('input');
                const message = input.value.trim();

                if (!message) {
                    alert('请输入消息');
                    return;
                }

                // 显示用户消息
                const messagesDiv = document.getElementById('messages');
                const userMsg = document.createElement('div');
                userMsg.className = 'user';
                userMsg.innerHTML = `<div class="message-header">👤 你</div>${message}`;
                messagesDiv.appendChild(userMsg);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;

                input.value = '';
                input.focus();

                // 发送到服务器
                fetch('/ask', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        uid: uid,
                        message: message,
                        agent: currentAgent
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        addErrorMessage('发送失败: ' + data.error);
                    } else {
                        console.log('发送成功:', data);
                    }
                })
                .catch(err => {
                    console.error('发送失败:', err);
                    addErrorMessage('发送失败: ' + err.message);
                });
            }

            // 切换 Agent
            function switchAgent(agentName) {
                currentAgent = agentName;
                document.getElementById('agent-display').textContent = agentName;

                // 更新按钮状态
                document.querySelectorAll('.agent-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                event.target.classList.add('active');

                // 显示切换消息
                const messagesDiv = document.getElementById('messages');
                const switchMsg = document.createElement('div');
                switchMsg.className = 'info';
                switchMsg.textContent = `已切换到 ${agentName}`;
                messagesDiv.appendChild(switchMsg);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }

            // 清空对话
            function clearMessages() {
                if (confirm('确定要清空所有消息吗？')) {
                    document.getElementById('messages').innerHTML = 
                        '<div class="info">对话已清空</div>';
                }
            }

            // 测试连接
            function testConnection() {
                fetch('/health')
                    .then(response => response.json())
                    .then(data => {
                        const messagesDiv = document.getElementById('messages');
                        const testMsg = document.createElement('div');
                        testMsg.className = 'info';
                        testMsg.innerHTML = `<div class="message-header">🔗 连接测试</div>
                                           <strong>状态:</strong> ${data.status}<br>
                                           <strong>Agent实例:</strong> ${data.agent_instances}<br>
                                           <strong>用户队列:</strong> ${data.user_queues}`;
                        messagesDiv.appendChild(testMsg);
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    })
                    .catch(err => {
                        addErrorMessage('连接测试失败: ' + err.message);
                    });
            }

            // 回车发送消息
            document.getElementById('input').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });

            // 初始化 SSE 连接
            connectSSE();

            // 页面关闭时断开连接
            window.addEventListener('beforeunload', function() {
                if (eventSource) {
                    eventSource.close();
                }
            });
        </script>
    </body>
    </html>
    """
    return html


# ==================== SSE 流式响应端点 ====================
@app.route('/stream')
def stream():
    uid = request.args.get('uid')
    if not uid:
        return Response(
            json.dumps({"type": "error", "message": "缺少用户ID"}),
            status=400,
            mimetype="application/json"
        )

    logger.info(f"用户 {uid} 连接到 SSE 流")

    # 确保用户队列存在
    if uid not in agent_server.user_queues:
        agent_server.user_queues[uid] = queue.Queue()

    def generate():
        q = agent_server.user_queues[uid]

        try:
            # 发送连接成功消息
            yield f"data: {json.dumps({'type': 'connect', 'message': 'SSE连接成功', 'uid': uid})}\n\n"

            last_heartbeat = time.time()

            while True:
                try:
                    # 从队列获取消息
                    message = q.get(timeout=30)
                    yield f"data: {json.dumps(message)}\n\n"
                    last_heartbeat = time.time()

                except queue.Empty:
                    # 发送心跳保持连接
                    current_time = time.time()
                    if current_time - last_heartbeat > 15:
                        yield ": heartbeat\n\n"
                        last_heartbeat = current_time

        except Exception as e:
            logger.error(f"SSE 生成器错误: {e}")
            logger.error(traceback.format_exc())
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


# ==================== 处理用户消息 ====================
@app.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.json
        uid = data.get('uid')
        message = data.get('message')
        agent_name = data.get('agent', 'scheduling_agent')

        if not uid or not message:
            return jsonify({'error': '缺少必要参数'}), 400

        logger.info(f"处理请求: 用户={uid}, Agent={agent_name}, 消息={message}")

        # 处理消息
        success = agent_server.process_message(uid, message, agent_name)

        if success:
            return jsonify({'status': 'success', 'message': '已开始处理'})
        else:
            return jsonify({'error': '处理失败，请检查日志'}), 500

    except Exception as e:
        logger.error(f"处理请求错误: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# ==================== 健康检查 ====================
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'agent_instances': len(agent_server.agent_instances),
        'user_queues': len(agent_server.user_queues),
        'timestamp': time.time()
    })


# ==================== 调试信息 ====================
@app.route('/debug')
def debug():
    info = {
        'agent_instances': list(agent_server.agent_instances.keys()),
        'user_queues': list(agent_server.user_queues.keys()),
        'server_time': time.time()
    }
    return jsonify(info)


# ==================== 主程序 ====================
def main():
    """主函数 - 整合所有功能"""

    # 检查依赖
    try:
        import lxml
        from bs4 import BeautifulSoup
        logger.info("✓ 依赖检查通过: lxml, beautifulsoup4")
    except ImportError as e:
        logger.error(f"✗ 缺少依赖: {e}")
        print("请安装依赖: pip install lxml beautifulsoup4")
        return

    # 创建必要的目录
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/app.log", "w") as f:
            f.write("")  # 清空日志文件
    except Exception as e:
        logger.warning(f"创建日志目录失败: {e}")

    # 检查 API 密钥
    api_key = os.getenv("API_KEY")
    if not api_key:
        logger.warning("未设置 API_KEY 环境变量，请检查 .env 文件")

    logger.info("=" * 60)
    logger.info("Agent SSE 服务器启动")
    logger.info("=" * 60)

    # 注册 Dumplings Agent（保持与原 main.py 相同的逻辑）
    try:
        # 注册工具
        @Dumplings.tool_registry.register_tool(
            allowed_agents=["8841cd45eef54217bc8122cafebe5fd6", "time_agent"],
            name="get_time"
        )
        def get_time(xml: str) -> str:
            current_time = time.strftime("%H:%M:%S", time.localtime())
            logger.info(f"调用 get_time 工具，返回: {current_time}")
            return f"当前时间: {current_time}"

        logger.info("✓ 工具注册成功")

        # 注册调度 Agent - 直接使用原有逻辑
        @Dumplings.register_agent(uuid.uuid4().hex, "scheduling_agent")
        class scheduling_agent(Dumplings.BaseAgent):
            prompt = f"你是一个名为汤圆Agent的AGI，你可以用<ask_for_help><agent_id>id</agent_id><message>message</message></ask_for_help>的方式与其他Agent通讯, 你可以使用<attempt_completion>标签直接退出对话（你不可再次获得任何信息）， 它的语法为<attempt_completion><report_content>放入你想播报的内容，或留空</report_content></attempt_completion>"
            api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            model_name = "deepseek-v3.2-exp"
            api_key = os.getenv("API_KEY")

            def __init__(self):
                super().__init__()

        logger.info("✓ 调度 Agent 注册成功")

        # 注册时间 Agent
        @Dumplings.register_agent("8841cd45eef54217bc8122cafebe5fd6", "time_agent")
        class time_agent(Dumplings.BaseAgent):
            prompt = "你是一个名为汤圆Agent的AGI的子agent名为时间管理者，你可以用<ask_for_help><agent_id>id</agent_id><message>message</message></ask_for_help>的方式与其他Agent通讯, 你还有get_time可以查询时间（直接<get_time></get_time>即可）"
            api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            model_name = "deepseek-v3.2-exp"
            api_key = os.getenv("API_KEY")

            def __init__(self):
                super().__init__()

        logger.info("✓ 时间 Agent 注册成功")

        # 测试 Agent 连接 - 直接使用 Dumplings.agent_list 中的实例
        logger.info("测试 Agent 连接...")
        try:
            if "scheduling_agent" in Dumplings.agent_list:
                logger.info("✓ Agent 连接测试通过")
                logger.info(f"Agent列表: {list(Dumplings.agent_list.keys())}")
            else:
                logger.error("✗ 未找到 scheduling_agent")
        except Exception as e:
            logger.error(f"✗ Agent 连接测试失败: {e}")

    except Exception as e:
        logger.error(f"Dumplings 初始化失败: {e}")
        logger.error(traceback.format_exc())
        print("请确保 Dumplings 库已正确安装并可用")
        return

    # 启动信息
    logger.info(f"访问地址: http://localhost:5000")
    logger.info(f"API 密钥: {'已设置' if api_key else '未设置'}")
    logger.info(f"SSE 端点: /stream?uid=<用户ID>")
    logger.info(f"消息端点: POST /ask")
    logger.info(f"健康检查: /health")
    logger.info("按 Ctrl+C 停止服务器")
    logger.info("=" * 60)

    # 启动 Flask 服务器
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        logger.info("服务器停止")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()