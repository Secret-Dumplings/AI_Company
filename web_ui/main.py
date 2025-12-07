import streamlit as st
import time
from datetime import datetime
from typing import Generator

# 页面配置
st.set_page_config(
    page_title="AI协作对话系统 - 流式输出",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS - 优化流式输出样式（保持不变）
st.html("""
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    .stApp {
        background-color: #f5f5f5 !important;
        font-family: 'Segoe UI', 'Roboto', sans-serif !important;
        color-scheme: light dark;
    }

    .container {
        width: 100%;
        max-width: 1200px;
        margin: 0 auto;
        background-color: #ffffff;
        border: 2px solid #1a1a1a;
        overflow: hidden;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .header {
        background-color: #ffffff;
        padding: 20px;
        border-bottom: 2px solid #1a1a1a;
        text-align: center;
    }

    .header h1 {
        font-size: 2.2rem;
        margin-bottom: 8px;
        color: #000000;
        font-weight: 700;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    .header p {
        color: #2c3e50;
        font-size: 1.1rem;
        margin-top: 8px;
        font-weight: 500;
        letter-spacing: 0.3px;
        opacity: 0.9;
    }

    .header h1::after {
        content: '';
        display: block;
        width: 60px;
        height: 3px;
        background: linear-gradient(90deg, #1a1a1a, #007bff);
        margin: 8px auto 0;
        border-radius: 2px;
    }

    .input-section {
        padding: 20px;
        border-bottom: 2px solid #1a1a1a;
        background-color: #fafafa;
    }

    .user-input-box {
        border: 2px solid #1a1a1a;
        padding: 12px 15px;
        background-color: #ffffff;
        color: #000000;
        font-size: 1rem;
        font-weight: 500;
        border-radius: 6px;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }

    .user-input-box:focus {
        outline: none;
        border-color: #007bff;
        box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
    }

    .conversation-section {
        padding: 20px;
        min-height: 500px;
        background-color: #ffffff;
    }

    .single-conversation {
        display: flex;
        flex-direction: column;
    }

    .dual-conversation {
        display: flex;
        gap: 20px;
    }

    .ai-box {
        flex: 1;
        border: 2px solid #1a1a1a;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        height: 500px;
        background-color: #ffffff;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
    }

    .ai-header {
        background-color: #ffffff;
        color: #000000;
        padding: 15px;
        display: flex;
        align-items: center;
        border-bottom: 2px solid #1a1a1a;
        position: relative;
        background: linear-gradient(90deg, #ffffff 0%, #f8f9fa 100%);
    }

    .ai-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, #007bff 0%, #0056b3 100%);
    }

    .ai-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: linear-gradient(135deg, #1a1a1a 0%, #007bff 100%);
        display: flex;
        justify-content: center;
        align-items: center;
        margin-right: 12px;
        font-weight: bold;
        color: #ffffff;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    .ai-name {
        font-weight: 700;
        font-size: 1.1rem;
        color: #000000;
        letter-spacing: 0.5px;
    }

    .ai-conversation {
        flex: 1;
        padding: 15px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        background-color: #ffffff;
        background-image: 
            linear-gradient(to right, #f8f9fa 1px, transparent 1px),
            linear-gradient(to bottom, #f8f9fa 1px, transparent 1px);
        background-size: 20px 20px;
    }

    .message {
        margin-bottom: 12px;
        padding: 12px 16px;
        border-radius: 8px;
        max-width: 85%;
        animation: messageAppear 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
        font-size: 0.95rem;
        line-height: 1.5;
        word-wrap: break-word;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
        transition: transform 0.2s ease;
        font-weight: 500;
    }

    .message:hover {
        transform: translateY(-1px);
    }

    .ai-message {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        color: #000000;
        align-self: flex-start;
        border-left: 4px solid #007bff;
        box-shadow: 0 2px 8px rgba(0, 123, 255, 0.1);
    }

    .user-message {
        background: linear-gradient(135deg, #1a1a1a 0%, #343a40 100%);
        color: #ffffff;
        align-self: flex-end;
        border-right: 4px solid #28a745;
        box-shadow: 0 2px 8px rgba(40, 167, 69, 0.2);
    }

    .system-message {
        background: linear-gradient(135deg, #fff5f5 0%, #ffeaea 100%);
        border: 1px solid #dc3545;
        text-align: center;
        max-width: 90%;
        margin: 15px auto;
        font-style: italic;
        color: #c82333;
        border-left: 4px solid #dc3545;
        font-weight: 600;
        padding: 10px 20px;
        box-shadow: 0 2px 8px rgba(220, 53, 69, 0.1);
    }

    .tool-message {
        background: linear-gradient(135deg, #fff8e6 0%, #fff2d6 100%);
        border: 1px solid #d4a017;
        font-family: 'SF Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 0.85rem;
        color: #5a4b30;
        border-left: 4px solid #d4a017;
        padding: 10px 14px;
        box-shadow: 0 2px 8px rgba(212, 160, 23, 0.1);
    }

    .collaboration-indicator {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 10px 16px;
        border-radius: 8px;
        margin: 12px auto;
        text-align: center;
        font-size: 0.9rem;
        color: #0d47a1;
        border-left: 4px solid #2196f3;
        max-width: 80%;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(33, 150, 243, 0.1);
    }

    .typing-indicator {
        display: flex;
        align-items: center;
        margin-top: 8px;
        padding-left: 10px;
        color: #000000;
        font-weight: 500;
    }

    .typing-dots {
        display: flex;
        margin-left: 12px;
    }

    .typing-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
        margin: 0 3px;
        animation: typingAnimation 1.4s infinite ease-in-out;
        box-shadow: 0 2px 4px rgba(0, 123, 255, 0.3);
    }

    .typing-dot:nth-child(1) {
        animation-delay: -0.32s;
    }

    .typing-dot:nth-child(2) {
        animation-delay: -0.16s;
    }

    .streaming-cursor {
        display: inline-block;
        width: 2px;
        height: 1.2em;
        background-color: #007bff;
        margin-left: 2px;
        animation: blink 1s infinite;
        vertical-align: text-bottom;
    }

    .streaming-message {
        position: relative;
        border-left: 4px solid #007bff !important;
        border-right: none !important;
    }

    @keyframes messageAppear {
        from { 
            opacity: 0; 
            transform: translateY(10px) scale(0.95); 
        }
        to { 
            opacity: 1; 
            transform: translateY(0) scale(1); 
        }
    }

    @keyframes typingAnimation {
        0%, 60%, 100% { 
            opacity: 0.4; 
            transform: scale(0.8) translateY(0);
        }
        30% { 
            opacity: 1; 
            transform: scale(1.2) translateY(-3px);
        }
    }

    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    .ai-conversation::-webkit-scrollbar {
        width: 8px;
    }

    .ai-conversation::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }

    .ai-conversation::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #007bff 0%, #0056b3 100%);
        border-radius: 4px;
    }

    .ai-conversation::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #0056b3 0%, #003d82 100%);
    }

    @media (max-width: 768px) {
        .dual-conversation {
            flex-direction: column;
            gap: 15px;
        }

        .ai-box {
            height: 400px;
        }

        .message {
            max-width: 92%;
            padding: 10px 14px;
            font-size: 0.9rem;
        }

        .header h1 {
            font-size: 1.8rem;
        }
    }
</style>
""")


# ===========================================
# 流式输出生成器函数
# ===========================================
def stream_text_generator(text: str, delay_per_char: float = 0.03) -> Generator[str, None, None]:
    """模拟API流式响应，逐个字符生成文本"""
    for char in text:
        yield char
        time.sleep(delay_per_char)


# ===========================================
# 初始化会话状态
# ===========================================
def init_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.agent1_messages = []
        st.session_state.agent2_messages = []
        st.session_state.is_processing = False
        st.session_state.current_agent = None
        st.session_state.show_dual = False

        # 流式输出相关状态
        st.session_state.streaming_active = False
        st.session_state.streaming_agent = None
        st.session_state.streaming_message_index = None
        st.session_state.streaming_content = ""
        st.session_state.streaming_generator = None

        # 用户输入存储
        st.session_state.user_input_buffer = ""

        # 新增：清空输入框标志
        st.session_state.should_clear_input = False

        # 添加初始消息
        st.session_state.agent1_messages.append({
            "role": "ai",
            "content": "您好！我是调度Agent。我可以处理您的问题，并在需要时召唤时间Agent提供专业支持。",
            "timestamp": datetime.now(),
            "is_streaming": False
        })


init_session_state()


# ===========================================
# 核心修复：前置状态检查与清理
# ===========================================
def check_and_clear_widgets():
    """
    此函数必须在任何输入小部件被渲染前调用。
    检查session_state中的标志，并在需要时安全地清空小部件的值。
    """
    # 检查是否需要清空主输入框
    if st.session_state.get('should_clear_input', False):
        # 此时user_input_widget还未被当前脚本执行周期实例化，可以安全修改
        if 'user_input_widget' in st.session_state:
            st.session_state.user_input_widget = ""
        st.session_state.should_clear_input = False


# 调用清空检查函数（在渲染任何小部件之前）
check_and_clear_widgets()

# ===========================================
# 页面结构
# ===========================================
st.html("""
<div class="container">
    <div class="header">
        <h1>🤖 AI协作对话系统</h1>
        <p>实时流式输出演示 - 单个字符级别</p>
    </div>
""")

# 对话显示占位符
conversation_placeholder = st.empty()


# 构建对话HTML
def build_conversation_html():
    html = '<div class="conversation-section">'

    if not st.session_state.show_dual:
        # 单列模式
        html += '''
        <div class="single-conversation">
            <div class="ai-box">
                <div class="ai-header">
                    <div class="ai-avatar">AI1</div>
                    <div class="ai-name">调度 Agent</div>
                </div>
                <div class="ai-conversation">
        '''

        for idx, msg in enumerate(st.session_state.agent1_messages):
            if msg["role"] == "user":
                html += f'''
                <div class="message user-message">
                    <div class="message-text">{msg["content"]}</div>
                </div>
                '''
            elif msg["role"] == "ai":
                is_streaming = msg.get("is_streaming", False)
                message_class = "message ai-message"
                if is_streaming:
                    message_class += " streaming-message"

                html += f'''
                <div class="{message_class}">
                    <div class="message-text">
                        {msg["content"]}
                        {'''<span class="streaming-cursor"></span>''' if is_streaming else ''}
                    </div>
                </div>
                '''
            elif msg["role"] == "system":
                html += f'''
                <div class="message system-message">
                    <div class="message-text">{msg["content"]}</div>
                </div>
                '''
            elif msg["role"] == "tool":
                html += f'''
                <div class="message tool-message">
                    <div class="message-text">{msg["content"]}</div>
                </div>
                '''

        if (st.session_state.is_processing and
                st.session_state.current_agent == "scheduling_agent" and
                not st.session_state.streaming_active):
            html += '''
            <div class="typing-indicator">
                <div class="ai-avatar" style="width:25px;height:25px;font-size:0.8rem;">AI1</div>
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
            '''

        html += '</div></div></div>'
    else:
        # 双列模式
        html += '<div class="dual-conversation">'

        # 左侧列 - 调度Agent
        html += '''
        <div class="ai-box">
            <div class="ai-header">
                <div class="ai-avatar">AI1</div>
                <div class="ai-name">调度 Agent</div>
            </div>
            <div class="ai-conversation">
        '''

        for idx, msg in enumerate(st.session_state.agent1_messages):
            if msg["role"] == "user":
                html += f'''
                <div class="message user-message">
                    <div class="message-text">{msg["content"]}</div>
                </div>
                '''
            elif msg["role"] == "ai":
                is_streaming = msg.get("is_streaming", False) and st.session_state.streaming_agent == "agent1"
                message_class = "message ai-message"
                if is_streaming:
                    message_class += " streaming-message"

                html += f'''
                <div class="{message_class}">
                    <div class="message-text">
                        {msg["content"]}
                        {'''<span class="streaming-cursor"></span>''' if is_streaming else ''}
                    </div>
                </div>
                '''
            elif msg["role"] == "system":
                html += f'''
                <div class="message system-message">
                    <div class="message-text">{msg["content"]}</div>
                </div>
                '''
            elif msg["role"] == "tool":
                html += f'''
                <div class="message tool-message">
                    <div class="message-text">{msg["content"]}</div>
                </div>
                '''

        html += '</div></div>'  # 关闭左侧

        # 右侧列 - 时间Agent
        html += '''
        <div class="ai-box">
            <div class="ai-header">
                <div class="ai-avatar">AI2</div>
                <div class="ai-name">时间 Agent</div>
            </div>
            <div class="ai-conversation">
        '''

        for idx, msg in enumerate(st.session_state.agent2_messages):
            if msg["role"] == "ai":
                is_streaming = msg.get("is_streaming", False) and st.session_state.streaming_agent == "agent2"
                message_class = "message ai-message"
                if is_streaming:
                    message_class += " streaming-message"

                html += f'''
                <div class="{message_class}">
                    <div class="message-text">
                        {msg["content"]}
                        {'''<span class="streaming-cursor"></span>''' if is_streaming else ''}
                    </div>
                </div>
                '''
            elif msg["role"] == "system":
                html += f'''
                <div class="message system-message">
                    <div class="message-text">{msg["content"]}</div>
                </div>
                '''
            elif msg["role"] == "tool":
                html += f'''
                <div class="message tool-message">
                    <div class="message-text">{msg["content"]}</div>
                </div>
                '''

        html += '</div></div></div>'  # 关闭右侧和双列模式

    html += '</div>'
    return html


# 显示对话
conversation_placeholder.html(build_conversation_html())

# ===========================================
# 输入区域
# ===========================================
st.html('<div class="input-section">')
st.html('<div class="user-input-box">')

# 渲染输入框（此时已通过前置检查安全清空）
user_input = st.text_area(
    "输入指令",
    height=100,
    key="user_input_widget",
    label_visibility="collapsed",
    placeholder="输入您的问题或指令...（支持：时间查询、天气信息、问题解答）",
    disabled=st.session_state.is_processing or st.session_state.streaming_active
)

st.html('</div>')

# 按钮区域
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn1:
    clear_button = st.button(
        "清空对话",
        use_container_width=True,
        disabled=st.session_state.is_processing or st.session_state.streaming_active
    )
with col_btn3:
    send_button = st.button(
        "发送消息" if not st.session_state.is_processing else "处理中...",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.is_processing or st.session_state.streaming_active
    )

st.html('</div>')  # 关闭input-section
st.html('</div>')  # 关闭容器

# ===========================================
# 按钮事件处理
# ===========================================
# 处理清空对话
if clear_button and not st.session_state.is_processing:
    st.session_state.agent1_messages = [{
        "role": "ai",
        "content": "您好！我是调度Agent。我可以处理您的问题，并在需要时召唤时间Agent提供专业支持。",
        "timestamp": datetime.now(),
        "is_streaming": False
    }]
    st.session_state.agent2_messages = []
    st.session_state.show_dual = False
    st.session_state.is_processing = False
    st.session_state.current_agent = None
    st.session_state.streaming_active = False
    st.session_state.streaming_content = ""
    st.session_state.streaming_generator = None
    st.session_state.user_input_buffer = ""

    # 核心修复：设置清空标志，而不是直接修改widget状态
    st.session_state.should_clear_input = True

    st.rerun()

# 处理发送消息
if send_button and user_input and not st.session_state.is_processing:
    # 存储用户输入到缓冲区
    st.session_state.user_input_buffer = user_input.strip()

    # 添加用户消息
    st.session_state.agent1_messages.append({
        "role": "user",
        "content": st.session_state.user_input_buffer,
        "timestamp": datetime.now(),
        "is_streaming": False
    })

    # 设置为处理中
    st.session_state.is_processing = True
    st.session_state.current_agent = "scheduling_agent"

    # 核心修复：设置清空标志，而不是直接修改widget状态
    st.session_state.should_clear_input = True

    st.rerun()


# ===========================================
# 流式输出处理函数
# ===========================================
def process_streaming_chunk():
    """处理单个字符的流式输出"""
    if (st.session_state.streaming_active and
            st.session_state.streaming_generator is not None):
        try:
            char = next(st.session_state.streaming_generator)
            st.session_state.streaming_content += char

            if st.session_state.streaming_agent == "agent1":
                if st.session_state.streaming_message_index < len(st.session_state.agent1_messages):
                    st.session_state.agent1_messages[st.session_state.streaming_message_index]["content"] = \
                        st.session_state.streaming_content
                    st.session_state.agent1_messages[st.session_state.streaming_message_index]["is_streaming"] = True
            elif st.session_state.streaming_agent == "agent2":
                if st.session_state.streaming_message_index < len(st.session_state.agent2_messages):
                    st.session_state.agent2_messages[st.session_state.streaming_message_index]["content"] = \
                        st.session_state.streaming_content
                    st.session_state.agent2_messages[st.session_state.streaming_message_index]["is_streaming"] = True

            return True
        except StopIteration:
            st.session_state.streaming_active = False
            st.session_state.streaming_generator = None

            if st.session_state.streaming_agent == "agent1":
                if st.session_state.streaming_message_index < len(st.session_state.agent1_messages):
                    st.session_state.agent1_messages[st.session_state.streaming_message_index]["is_streaming"] = False
            elif st.session_state.streaming_agent == "agent2":
                if st.session_state.streaming_message_index < len(st.session_state.agent2_messages):
                    st.session_state.agent2_messages[st.session_state.streaming_message_index]["is_streaming"] = False

            return False
    return False


# ===========================================
# 模拟对话流程
# ===========================================
if st.session_state.is_processing:
    if st.session_state.current_agent == "scheduling_agent":
        if not st.session_state.streaming_active:
            st.session_state.agent1_messages.append({
                "role": "ai",
                "content": "",
                "timestamp": datetime.now(),
                "is_streaming": True
            })

            prompt = st.session_state.user_input_buffer
            full_response = f"我理解您的需求：'{prompt}'。让我为您分析并准备回答。首先，我需要思考这个问题..."

            st.session_state.streaming_active = True
            st.session_state.streaming_agent = "agent1"
            st.session_state.streaming_message_index = len(st.session_state.agent1_messages) - 1
            st.session_state.streaming_content = ""
            st.session_state.streaming_generator = stream_text_generator(full_response, delay_per_char=0.02)

        if process_streaming_chunk():
            st.rerun()
        else:
            st.session_state.current_agent = "calling_ai2"
            st.rerun()

    elif st.session_state.current_agent == "calling_ai2":
        if not st.session_state.streaming_active:
            st.session_state.agent1_messages.append({
                "role": "ai",
                "content": "",
                "timestamp": datetime.now(),
                "is_streaming": True
            })

            full_response = "这个问题涉及到时间相关的内容，让我召唤时间Agent来提供更专业的意见。正在连接时间Agent..."

            st.session_state.streaming_active = True
            st.session_state.streaming_agent = "agent1"
            st.session_state.streaming_message_index = len(st.session_state.agent1_messages) - 1
            st.session_state.streaming_content = ""
            st.session_state.streaming_generator = stream_text_generator(full_response, delay_per_char=0.015)

        if process_streaming_chunk():
            st.rerun()
        else:
            st.session_state.show_dual = True
            st.session_state.current_agent = "time_agent_thinking"
            st.rerun()

    elif st.session_state.current_agent == "time_agent_thinking":
        if not st.session_state.streaming_active:
            st.session_state.agent2_messages.append({
                "role": "ai",
                "content": "",
                "timestamp": datetime.now(),
                "is_streaming": True
            })

            full_response = "感谢调度Agent的召唤。我正在查询相关的时间信息..."

            st.session_state.streaming_active = True
            st.session_state.streaming_agent = "agent2"
            st.session_state.streaming_message_index = len(st.session_state.agent2_messages) - 1
            st.session_state.streaming_content = ""
            st.session_state.streaming_generator = stream_text_generator(full_response, delay_per_char=0.01)

        if process_streaming_chunk():
            st.rerun()
        else:
            st.session_state.current_agent = "time_agent_tool"
            st.rerun()

    elif st.session_state.current_agent == "time_agent_tool":
        st.session_state.agent2_messages.append({
            "role": "tool",
            "content": "调用工具：get_time",
            "timestamp": datetime.now(),
            "is_streaming": False
        })
        st.session_state.current_agent = "time_agent_result"
        st.rerun()

    elif st.session_state.current_agent == "time_agent_result":
        if not st.session_state.streaming_active:
            st.session_state.agent2_messages.append({
                "role": "ai",
                "content": "",
                "timestamp": datetime.now(),
                "is_streaming": True
            })

            current_time = datetime.now().strftime("%H:%M:%S")
            full_response = f"✅ 查询成功！当前系统时间是：{current_time}。"

            st.session_state.streaming_active = True
            st.session_state.streaming_agent = "agent2"
            st.session_state.streaming_message_index = len(st.session_state.agent2_messages) - 1
            st.session_state.streaming_content = ""
            st.session_state.streaming_generator = stream_text_generator(full_response, delay_per_char=0.008)

        if process_streaming_chunk():
            st.rerun()
        else:
            st.session_state.current_agent = "scheduling_summary"
            st.rerun()

    elif st.session_state.current_agent == "scheduling_summary":
        if not st.session_state.streaming_active:
            st.session_state.agent1_messages.append({
                "role": "ai",
                "content": "",
                "timestamp": datetime.now(),
                "is_streaming": True
            })

            current_time = datetime.now().strftime("%H:%M")
            full_response = f"感谢时间Agent的补充。基于我们的讨论，当前时间是{current_time}。我可以基于这个时间为您安排日程或提供其他时间相关的建议。"

            st.session_state.streaming_active = True
            st.session_state.streaming_agent = "agent1"
            st.session_state.streaming_message_index = len(st.session_state.agent1_messages) - 1
            st.session_state.streaming_content = ""
            st.session_state.streaming_generator = stream_text_generator(full_response, delay_per_char=0.02)

        if process_streaming_chunk():
            st.rerun()
        else:
            st.session_state.current_agent = "completion"
            st.rerun()

    elif st.session_state.current_agent == "completion":
        st.session_state.agent1_messages.append({
            "role": "tool",
            "content": "🏁 任务完成 - 协作对话结束",
            "timestamp": datetime.now(),
            "is_streaming": False
        })
        st.session_state.is_processing = False
        st.session_state.current_agent = None
        st.rerun()

# ===========================================
# 状态栏
# ===========================================
st.html(f"""
    <div style="display: flex; justify-content: space-around; color: white; font-weight: bold; margin-top: 20px; padding: 10px; background: #1a1a1a; border-radius: 8px;">
        <div style="color: #4ade80; padding: 8px 15px; background: rgba(74, 222, 128, 0.15); border-radius: 8px; border: 1px solid #4ade80;">
            {'🟢 就绪' if not st.session_state.is_processing else '🟡 处理中'}
        </div>
        <div style="color: #60a5fa; padding: 8px 15px; background: rgba(96, 165, 250, 0.15); border-radius: 8px; border: 1px solid #60a5fa;">
            📊 总消息: {len(st.session_state.agent1_messages) + len(st.session_state.agent2_messages)}
        </div>
        <div style="color: #f87171; padding: 8px 15px; background: rgba(248, 113, 113, 0.15); border-radius: 8px; border: 1px solid #f87171;">
            ⚡ 流式状态: {'活跃' if st.session_state.streaming_active else '空闲'}
        </div>
        <div style="color: #d946ef; padding: 8px 15px; background: rgba(217, 70, 239, 0.15); border-radius: 8px; border: 1px solid #d946ef;">
            🎯 当前Agent: {st.session_state.current_agent or '无'}
        </div>
    </div>
""")

# ===========================================
# JavaScript自动滚动
# ===========================================
st.html("""
<script>
    function scrollToBottom() {
        const conversationContainers = document.querySelectorAll('.ai-conversation');
        conversationContainers.forEach(container => {
            container.scrollTop = container.scrollHeight;
        });
    }

    window.onload = scrollToBottom;

    const observer = new MutationObserver(function(mutations) {
        scrollToBottom();
    });

    observer.observe(document.body, { childList: true, subtree: true });
</script>
""")