from flask import Flask, render_template, request, Response, jsonify, redirect, url_for, session
import json
import os
import sys
from threading import Thread
from queue import Queue
import time

# 添加当前目录到Python路径，确保可以导入Dumplings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
from dotenv import load_dotenv
import os

# 确保从正确的目录加载 .env 文件
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Debug: Print loaded environment variables
print(f"Loaded USERNAME: {os.getenv('USERNAME', 'NOT_SET')}")
print(f"Loaded PASSWORD: {'***' if os.getenv('PASSWORD') else 'NOT_SET'}")
print(f"Loaded SECRET_KEY: {'***' if os.getenv('SECRET_KEY') else 'NOT_SET'}")

# 导入Dumplings库
import Dumplings
import uuid

# 注册工具
@Dumplings.tool_registry.register_tool(
    allowed_agents=["8841cd45eef54217bc8122cafebe5fd6", "time_agent"],
    name="get_time"
)
def get_time(xml: str) -> str:
    """获取当前时间的工具"""
    # 这里可以替换为真实的获取时间逻辑
    return "11:03"

# 注册Agent
@Dumplings.register_agent(uuid.uuid4().hex, "scheduling_agent")
class scheduling_agent(Dumplings.BaseAgent):
    prompt = f"""你是一个名为汤圆Agent的AGI，你可以用<ask_for_help><agent_id>id</agent_id><message>message</message></ask_for_help>的方式与其他Agent通讯。

你可以使用以下工具：
- <list_agents></list_agents>: 获取所有可用的Agent列表及其UUID
- <attempt_completion><report_content>内容</report_content></attempt_completion>: 直接退出对话

当需要获取当前时间时，请先使用<list_agents></list_agents>查看可用的Agent，然后使用正确的UUID调用时间管理者。"""
    api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model_name = "deepseek-v3.2"
    api_key = os.getenv("API_KEY")
    def __init__(self):
        super().__init__()

@Dumplings.register_agent("8841cd45eef54217bc8122cafebe5fd6", "time_agent")
class time_agent(Dumplings.BaseAgent):
    prompt = """你是一个名为汤圆Agent的AGI的子agent名为时间管理者，你可以用<ask_for_help><agent_id>id</agent_id><message>message</message></ask_for_help>的方式与其他Agent通讯, 你还有get_time可以查询时间（直接<get_time></get_time>即可）。

当其他Agent向你询问时间时，请直接使用<get_time></get_time>工具获取当前时间并返回给用户。"""
    api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model_name = "deepseek-v3.2"
    api_key = os.getenv("API_KEY")
    def __init__(self):
        super().__init__()

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # 设置密钥用于会话加密
    app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

    print(f"Current working directory: {os.getcwd()}")
    print(f"App root path: {app.root_path}")
    print(f"Templates folder exists: {os.path.exists(os.path.join(app.root_path, 'templates'))}")
    print(f"Chat.html exists: {os.path.exists(os.path.join(app.root_path, 'templates', 'chat.html'))}")

    # 获取调度Agent实例
    schedule_agent = Dumplings.agent_list["scheduling_agent"]

    def verify_credentials(username, password):
        """
        验证用户凭据
        使用环境变量中的 USERNAME 和 PASSWORD
        如果未设置，则使用默认值 admin/123456
        """
        expected_username = os.getenv('USERNAME', 'admin')
        expected_password = os.getenv('PASSWORD', '123456')

        # Debug: Print what we're comparing
        print(f"Comparing: input_username='{username}', expected_username='{expected_username}'")
        print(f"Comparing: input_password='***', expected_password='***'")
        print(f"Username match: {username == expected_username}")
        print(f"Password match: {password == expected_password}")

        return username == expected_username and password == expected_password

    def login_required(f):
        """装饰器：确保用户已登录"""
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session or not session['logged_in']:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """登录路由"""
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            if not username or not password:
                return render_template('login.html', error='用户名和密码不能为空')

            if verify_credentials(username, password):
                # 登录成功 - 设置会话
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('home'))
            else:
                return render_template('login.html', error='用户名或密码不正确')

        # GET 请求 - 显示登录页面
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        """登出路由"""
        session.clear()
        return redirect(url_for('login'))

    def generate_dumplings_response(user_message, output_queue):
        """使用Dumplings Agent生成响应 - 通过劫持out方法"""
        try:
            # 临时替换所有agent的out方法
            for agent_name, agent in Dumplings.agent_list.items():
                if hasattr(agent, 'out'):
                    # 使用默认参数捕获当前的output_queue
                    def custom_out(content, queue=output_queue):
                        """自定义out方法，劫持pack的内容"""
                        if content.get("tool_name"):
                            # 工具调用 - 避免序列化函数参数
                            message = f"调用工具: {content.get('tool_name')}"
                            queue.put({"type": "system", "content": message})
                        elif not content.get("task"):
                            # 普通消息
                            message = content.get("message", "")
                            # 忽略空消息或只包含空白字符的消息
                            if not message or not message.strip():
                                return
                            ai_name = content.get("ai_name", "main_agent")
                            ai_uuid = content.get("ai_uuid", "")
                            other = content.get("other", False)

                            if other and "本次请求用量：" in message:
                                # 用量信息
                                queue.put({
                                    "type": "usage",
                                    "content": message
                                })
                            else:
                                # AI消息
                                # 根据ai_name或ai_uuid确定agent_id
                                if ai_name == "time_agent" or ai_uuid == "8841cd45eef54217bc8122cafebe5fd6":
                                    agent_id = "time_agent"
                                else:
                                    agent_id = "main_agent"

                                queue.put({
                                    "type": "agent_message",
                                    "agent_id": agent_id,
                                    "content": message
                                })
                    agent.out = custom_out

            # 调用Agent进行对话
            result = schedule_agent.conversation_with_tool(user_message)

            # 发送结束信号
            output_queue.put(None)

        except Exception as e:
            output_queue.put({"type": "error", "content": f"Error: {str(e)}"})
            output_queue.put(None)

    @app.route("/")
    def home():
        """主页面路由 - 需要登录才能访问"""
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login'))
        return render_template("chat.html")

    @app.route("/api/chat", methods=["POST"])
    def chat_api():
        """AI对话API端点，支持流式响应 - 需要登录才能访问"""
        # 验证用户是否已登录
        if 'logged_in' not in session or not session['logged_in']:
            return jsonify({"error": "Unauthorized"}), 401

        try:
            data = request.get_json()
            user_message = data.get("message", "").strip()

            if not user_message:
                return jsonify({"error": "Message cannot be empty"}), 400

            # 创建队列用于接收流式输出
            output_queue = Queue()

            # 在后台线程中运行Dumplings Agent
            thread = Thread(target=generate_dumplings_response, args=(user_message, output_queue))
            thread.daemon = True
            thread.start()

            def generate():
                while True:
                    try:
                        message = output_queue.get(timeout=30)  # 30秒超时
                        if message is None:
                            # 发送结束标记
                            yield f"data: {json.dumps({'type': 'end', 'content': ''})}\n\n"
                            break
                        else:
                            # 发送消息块
                            yield f"data: {json.dumps({'type': 'chunk', 'content': message})}\n\n"
                    except:
                        # 超时或其他错误
                        yield f"data: {json.dumps({'type': 'error', 'content': 'Timeout or error occurred'})}\n\n"
                        break

            return Response(generate(), mimetype="text/event-stream")

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)