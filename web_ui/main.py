import streamlit as st
import time
from datetime import datetime
from typing import Generator

# 页面配置
st.set_page_config(
    page_title="AI协作对话系统",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 使用第一版的完整CSS样式
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

    /* 流式输出光标效果 */
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

    /* 增强动画效果 */
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

    @keyframes fadeIn {
        from { 
            opacity: 0; 
            transform: translateY(5px); 
        }
        to { 
            opacity: 1; 
            transform: translateY(0); 
        }
    }

    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* 优化滚动条 */
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

    /* 响应式设计改进 */
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

    @media (max-width: 480px) {
        .container {
            margin: 0;
            border-radius: 0;
            border: none;
            box-shadow: none;
        }

        .conversation-section,
        .input-section {
            padding: 15px 12px;
        }
    }

    /* 增强对比度的辅助类 */
    .high-contrast {
        --text-primary: #000000 !important;
        --text-secondary: #1a1a1a !important;
        --bg-primary: #ffffff !important;
        --bg-secondary: #f8f9fa !important;
    }

    /* 改进字体可读性 */
    .message, .ai-name, .typing-indicator, .collaboration-indicator {
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        text-rendering: optimizeLegibility;
    }

    /* 添加微妙的背景图案增强深度感 */
    .ai-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: 
            radial-gradient(circle at 20% 80%, rgba(0, 123, 255, 0.03) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(108, 117, 125, 0.02) 0%, transparent 50%);
        pointer-events: none;
        z-index: 1;
    }

    /* 确保内容在背景之上 */
    .ai-header, .ai-conversation {
        position: relative;
        z-index: 2;
    }

    /* 打印样式优化 */
    @media print {
        .container {
            border: none;
            box-shadow: none;
        }

        .ai-box {
            height: auto;
            page-break-inside: avoid;
        }

        .message {
            background: #ffffff !important;
            color: #000000 !important;
            box-shadow: none !important;
            border: 1px solid #ddd !important;
        }
    }
</style>
""")


# ===========================================
# 流式输出生成器函数（来自第二版）
# ===========================================
def stream_text_generator(text: str, delay_per_char: float = 0.03) -> Generator[str, None, None]:
    """模拟API流式响应，逐个字符生成文本"""
    for char in text:
        yield char
        time.sleep(delay_per_char)


# ===========================================
# 初始化会话状态（合并两版优点）
# ===========================================
def init_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.agent1_messages = []
        st.session_state.agent2_messages = []
        st.session_state.is_processing = False
        st.session_state.current_agent = None
        st.session_state.show_dual = False

        # 来自第二版的流式输出相关状态
        st.session_state.streaming_active = False
        st.session_state.streaming_agent = None
        st.session_state.streaming_message_index = None
        st.session_state.streaming_content = ""
        st.session_state.streaming_generator = None

        # 来自第二版的输入处理
        st.session_state.user_input_buffer = ""
        st.session_state.should_clear_input = False

        # 新增：消息容器管理（解决闪屏的关键）
        st.session_state.message_containers = {}
        st.session_state.typing_containers = {}
        st.session_state.collaboration_container = None

        # 添加初始消息（来自第一版）
        st.session_state.agent1_messages.append({
            "role": "ai",
            "content": "您好！我是调度Agent。我可以处理您的问题，并在需要时召唤时间Agent提供专业支持。",
            "timestamp": datetime.now(),
            "is_streaming": False
        })


init_session_state()


# ===========================================
# 核心修复：前置状态检查与清理（来自第二版）
# ===========================================
def check_and_clear_widgets():
    """在渲染任何输入小部件前安全地清空小部件的值"""
    if st.session_state.get('should_clear_input', False):
        if 'user_input_widget' in st.session_state:
            st.session_state.user_input_widget = ""
        st.session_state.should_clear_input = False


# 调用清空检查函数
check_and_clear_widgets()

# ===========================================
# 页面结构（来自第一版，保持完整格式）
# ===========================================
st.html("""
<div class="container">
    <div class="header">
        <h1>🤖 AI协作对话系统</h1>
        <p>调度Agent与时间Agent的协作对话</p>
    </div>
""")

# 对话显示区域
conversation_placeholder = st.empty()


# ===========================================
# 局部更新函数（解决闪屏的核心）
# ===========================================
def update_message_content(agent: str, message_index: int, content: str,
                           role: str = "ai", is_streaming: bool = False):
    """局部更新单个消息内容，避免全局刷新"""
    message_id = f"{agent}-msg-{message_index}"

    if message_id not in st.session_state.message_containers:
        st.session_state.message_containers[message_id] = st.empty()

    # 根据消息类型确定样式（来自第一版的完整格式）
    if role == "user":
        message_class = "message user-message"
    elif role == "ai":
        message_class = "message ai-message"
        if is_streaming:
            message_class += " streaming-message"
    elif role == "system":
        message_class = "message system-message"
    elif role == "tool":
        message_class = "message tool-message"
    else:
        message_class = "message"

    # 构建HTML（保持第一版的完整格式）
    html_content = f'''
    <div class="{message_class}">
        <div class="message-text">
            {content}
            {'<span class="streaming-cursor"></span>' if (is_streaming and role == "ai") else ''}
        </div>
    </div>
    '''

    # 局部更新
    st.session_state.message_containers[message_id].html(html_content)


def update_typing_indicator(agent: str, show: bool = True):
    """更新打字指示器"""
    indicator_id = f"typing-{agent}"

    if indicator_id not in st.session_state.typing_containers:
        st.session_state.typing_containers[indicator_id] = st.empty()

    if show:
        avatar_text = "AI1" if agent == "agent1" else "AI2"
        html_content = f'''
        <div class="typing-indicator">
            <div class="ai-avatar" style="width:25px;height:25px;font-size:0.8rem;">{avatar_text}</div>
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
        '''
        st.session_state.typing_containers[indicator_id].html(html_content)
    else:
        st.session_state.typing_containers[indicator_id].empty()


def update_collaboration_indicator(show: bool = True, text: str = ""):
    """更新协作指示器"""
    if st.session_state.collaboration_container is None:
        st.session_state.collaboration_container = st.empty()

    if show and text:
        html_content = f'''
        <div class="collaboration-indicator">
            {text}
        </div>
        '''
        st.session_state.collaboration_container.html(html_content)
    else:
        st.session_state.collaboration_container.empty()


# ===========================================
# 构建对话HTML（保持第一版结构，但使用局部更新）
# ===========================================
def build_conversation_html():
    """初始渲染对话结构，后续通过局部更新"""
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

        # 渲染静态消息（用户消息和已完成的消息）
        for idx, msg in enumerate(st.session_state.agent1_messages):
            message_id = f"agent1-msg-{idx}"
            if message_id not in st.session_state.message_containers:
                st.session_state.message_containers[message_id] = st.empty()

            # 只渲染非流式消息，流式消息通过局部更新
            if not msg.get("is_streaming", False):
                update_message_content("agent1", idx, msg["content"], msg["role"], False)

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

        # 渲染调度Agent的静态消息
        for idx, msg in enumerate(st.session_state.agent1_messages):
            message_id = f"agent1-msg-{idx}"
            if message_id not in st.session_state.message_containers:
                st.session_state.message_containers[message_id] = st.empty()

            if not msg.get("is_streaming", False):
                update_message_content("agent1", idx, msg["content"], msg["role"], False)

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

        # 渲染时间Agent的静态消息
        for idx, msg in enumerate(st.session_state.agent2_messages):
            message_id = f"agent2-msg-{idx}"
            if message_id not in st.session_state.message_containers:
                st.session_state.message_containers[message_id] = st.empty()

            if not msg.get("is_streaming", False):
                update_message_content("agent2", idx, msg["content"], msg["role"], False)

        html += '</div></div></div>'  # 关闭右侧和双列模式

    html += '</div>'  # 关闭conversation-section
    return html


# 初始渲染对话结构
conversation_placeholder.html(build_conversation_html())

# ===========================================
# 输入区域（来自第一版）
# ===========================================
st.html('<div class="input-section">')
st.html('<div class="user-input-box">')

user_input = st.text_area(
    "输入指令",
    height=100,
    key="user_input_widget",  # 使用第二版的key
    label_visibility="collapsed",
    placeholder="输入您的问题或指令...",
    disabled=st.session_state.is_processing
)

st.html('</div>')

# 按钮区域
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn1:
    clear_button = st.button(
        "清空对话",
        use_container_width=True,
        disabled=st.session_state.is_processing
    )
with col_btn3:
    send_button = st.button(
        "发送消息" if not st.session_state.is_processing else "处理中...",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.is_processing
    )

st.html('</div>')  # 关闭input-section
st.html('</div>')  # 关闭容器

# ===========================================
# 按钮事件处理（合并两版）
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
    st.session_state.message_containers = {}
    st.session_state.typing_containers = {}
    st.session_state.collaboration_container = None

    st.session_state.should_clear_input = True
    st.rerun()

# 处理发送消息
if send_button and user_input.strip() and not st.session_state.is_processing:
    # 添加用户消息
    st.session_state.user_input_buffer = user_input.strip()
    st.session_state.agent1_messages.append({
        "role": "user",
        "content": st.session_state.user_input_buffer,
        "timestamp": datetime.now(),
        "is_streaming": False
    })

    # 显示用户消息
    msg_idx = len(st.session_state.agent1_messages) - 1
    update_message_content("agent1", msg_idx, st.session_state.user_input_buffer, "user", False)

    st.session_state.is_processing = True
    st.session_state.current_agent = "scheduling_agent"
    st.session_state.should_clear_input = True
    st.rerun()


# ===========================================
# 流式输出处理函数（来自第二版，增强版）
# ===========================================
def process_streaming_chunk():
    """处理单个字符的流式输出，使用局部更新"""
    if (st.session_state.streaming_active and
            st.session_state.streaming_generator is not None):
        try:
            # 获取下一个字符
            char = next(st.session_state.streaming_generator)
            st.session_state.streaming_content += char

            # 确定消息角色
            if st.session_state.streaming_agent == "agent1":
                messages = st.session_state.agent1_messages
                role = messages[st.session_state.streaming_message_index].get("role", "ai")
            else:
                messages = st.session_state.agent2_messages
                role = messages[st.session_state.streaming_message_index].get("role", "ai")

            # 局部更新消息显示
            update_message_content(
                agent=st.session_state.streaming_agent,
                message_index=st.session_state.streaming_message_index,
                content=st.session_state.streaming_content,
                role=role,
                is_streaming=True
            )

            # 更新session状态
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
            # 流式输出完成
            st.session_state.streaming_active = False
            st.session_state.streaming_generator = None

            # 确定消息角色
            if st.session_state.streaming_agent == "agent1":
                messages = st.session_state.agent1_messages
                role = messages[st.session_state.streaming_message_index].get("role", "ai")
            else:
                messages = st.session_state.agent2_messages
                role = messages[st.session_state.streaming_message_index].get("role", "ai")

            # 更新消息为非流式状态
            if st.session_state.streaming_agent == "agent1":
                if st.session_state.streaming_message_index < len(st.session_state.agent1_messages):
                    st.session_state.agent1_messages[st.session_state.streaming_message_index]["is_streaming"] = False
            elif st.session_state.streaming_agent == "agent2":
                if st.session_state.streaming_message_index < len(st.session_state.agent2_messages):
                    st.session_state.agent2_messages[st.session_state.streaming_message_index]["is_streaming"] = False

            # 更新显示，移除光标
            update_message_content(
                agent=st.session_state.streaming_agent,
                message_index=st.session_state.streaming_message_index,
                content=st.session_state.streaming_content,
                role=role,
                is_streaming=False
            )

            return False
    return False


# ===========================================
# 模拟对话流程（合并两版）
# ===========================================
if st.session_state.is_processing:
    # 显示/隐藏指示器
    if st.session_state.current_agent == "scheduling_agent" and not st.session_state.streaming_active:
        update_typing_indicator("agent1", True)
    elif st.session_state.current_agent == "calling_ai2":
        update_collaboration_indicator(True, "调度Agent正在召唤时间Agent参与讨论...")
    else:
        update_typing_indicator("agent1", False)
        update_collaboration_indicator(False)

    if st.session_state.current_agent == "time_agent_thinking" and not st.session_state.streaming_active:
        update_typing_indicator("agent2", True)
    elif st.session_state.current_agent in ["time_agent_result", "time_agent_tool"]:
        update_typing_indicator("agent2", False)

    # 状态处理
    if st.session_state.current_agent == "scheduling_agent":
        if not st.session_state.streaming_active:
            # 创建新的AI消息
            new_message = {
                "role": "ai",
                "content": "",
                "timestamp": datetime.now(),
                "is_streaming": True
            }
            st.session_state.agent1_messages.append(new_message)

            prompt = st.session_state.user_input_buffer
            full_response = f"我理解您的问题，让我为您分析一下。"

            st.session_state.streaming_active = True
            st.session_state.streaming_agent = "agent1"
            st.session_state.streaming_message_index = len(st.session_state.agent1_messages) - 1
            st.session_state.streaming_content = ""
            st.session_state.streaming_generator = stream_text_generator(full_response, delay_per_char=0.03)

            # 清除打字指示器
            update_typing_indicator("agent1", False)

        if process_streaming_chunk():
            time.sleep(0.03)
            st.rerun()
        else:
            st.session_state.current_agent = "calling_ai2"
            st.rerun()

    elif st.session_state.current_agent == "calling_ai2":
        if not st.session_state.streaming_active:
            new_message = {
                "role": "ai",
                "content": "",
                "timestamp": datetime.now(),
                "is_streaming": True
            }
            st.session_state.agent1_messages.append(new_message)

            full_response = "让我召唤时间Agent来提供更专业的意见。"

            st.session_state.streaming_active = True
            st.session_state.streaming_agent = "agent1"
            st.session_state.streaming_message_index = len(st.session_state.agent1_messages) - 1
            st.session_state.streaming_content = ""
            st.session_state.streaming_generator = stream_text_generator(full_response, delay_per_char=0.025)

            # 清除协作指示器
            update_collaboration_indicator(False)

        if process_streaming_chunk():
            time.sleep(0.025)
            st.rerun()
        else:
            st.session_state.show_dual = True
            st.session_state.current_agent = "time_agent_thinking"
            st.rerun()

    elif st.session_state.current_agent == "time_agent_thinking":
        if not st.session_state.streaming_active:
            new_message = {
                "role": "ai",
                "content": "",
                "timestamp": datetime.now(),
                "is_streaming": True
            }
            st.session_state.agent2_messages.append(new_message)

            full_response = "感谢调度Agent的召唤。我正在查询当前时间..."

            st.session_state.streaming_active = True
            st.session_state.streaming_agent = "agent2"
            st.session_state.streaming_message_index = len(st.session_state.agent2_messages) - 1
            st.session_state.streaming_content = ""
            st.session_state.streaming_generator = stream_text_generator(full_response, delay_per_char=0.02)

            # 清除打字指示器
            update_typing_indicator("agent2", False)

        if process_streaming_chunk():
            time.sleep(0.02)
            st.rerun()
        else:
            st.session_state.current_agent = "time_agent_tool"
            st.rerun()

    elif st.session_state.current_agent == "time_agent_tool":
        tool_message = {
            "role": "tool",
            "content": "调用工具：get_time",
            "timestamp": datetime.now(),
            "is_streaming": False
        }
        st.session_state.agent2_messages.append(tool_message)

        # 显示工具消息
        msg_idx = len(st.session_state.agent2_messages) - 1
        update_message_content("agent2", msg_idx, "调用工具：get_time", "tool", False)

        st.session_state.current_agent = "time_agent_result"
        time.sleep(1)
        st.rerun()

    elif st.session_state.current_agent == "time_agent_result":
        if not st.session_state.streaming_active:
            new_message = {
                "role": "ai",
                "content": "",
                "timestamp": datetime.now(),
                "is_streaming": True
            }
            st.session_state.agent2_messages.append(new_message)

            current_time = datetime.now().strftime("%H:%M")
            full_response = f"✅ 查询成功！当前时间是：{current_time}"

            st.session_state.streaming_active = True
            st.session_state.streaming_agent = "agent2"
            st.session_state.streaming_message_index = len(st.session_state.agent2_messages) - 1
            st.session_state.streaming_content = ""
            st.session_state.streaming_generator = stream_text_generator(full_response, delay_per_char=0.015)

        if process_streaming_chunk():
            time.sleep(0.015)
            st.rerun()
        else:
            st.session_state.current_agent = "scheduling_summary"
            st.rerun()

    elif st.session_state.current_agent == "scheduling_summary":
        if not st.session_state.streaming_active:
            new_message = {
                "role": "ai",
                "content": "",
                "timestamp": datetime.now(),
                "is_streaming": True
            }
            st.session_state.agent1_messages.append(new_message)

            current_time = datetime.now().strftime("%H:%M")
            full_response = f"感谢时间Agent的补充。基于我们的讨论，当前时间是{current_time}。"

            st.session_state.streaming_active = True
            st.session_state.streaming_agent = "agent1"
            st.session_state.streaming_message_index = len(st.session_state.agent1_messages) - 1
            st.session_state.streaming_content = ""
            st.session_state.streaming_generator = stream_text_generator(full_response, delay_per_char=0.025)

        if process_streaming_chunk():
            time.sleep(0.025)
            st.rerun()
        else:
            st.session_state.current_agent = "completion"
            st.rerun()

    elif st.session_state.current_agent == "completion":
        tool_message = {
            "role": "tool",
            "content": "🏁 标记任务完成",
            "timestamp": datetime.now(),
            "is_streaming": False
        }
        st.session_state.agent1_messages.append(tool_message)

        # 显示完成消息
        msg_idx = len(st.session_state.agent1_messages) - 1
        update_message_content("agent1", msg_idx, "🏁 标记任务完成", "tool", False)

        st.session_state.is_processing = False
        st.session_state.current_agent = None
        time.sleep(0.5)
        st.rerun()

# ===========================================
# 状态栏（来自第一版，增强版）
# ===========================================
st.html(f"""
    <div style="display: flex; justify-content: space-around; color: white; font-weight: bold; margin-top: 20px; padding: 10px; background: #1a1a1a; border-radius: 8px;">
        <div style="color: #4ade80; padding: 8px 15px; background: rgba(74, 222, 128, 0.15); border-radius: 8px; border: 1px solid #4ade80;">
            {'🟢 就绪' if not st.session_state.is_processing else '🟡 处理中'}
        </div>
        <div style="color: #60a5fa; padding: 8px 15px; background: rgba(96, 165, 250, 0.15); border-radius: 8px; border: 1px solid #60a5fa;">
            📊 调度Agent消息: {len(st.session_state.agent1_messages)}
        </div>
        <div style="color: #60a5fa; padding: 8px 15px; background: rgba(96, 165, 250, 0.15); border-radius: 8px; border: 1px solid #60a5fa;">
            📊 时间Agent消息: {len(st.session_state.agent2_messages)}
        </div>
        <div style="color: #f87171; padding: 8px 15px; background: rgba(248, 113, 113, 0.15); border-radius: 8px; border: 1px solid #f87171;">
            ⚡ 流式状态: {'活跃' if st.session_state.streaming_active else '空闲'}
        </div>
    </div>
""")

# ===========================================
# JavaScript自动滚动（增强版）
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

    // 监听消息更新，自动滚动
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                const addedNodes = Array.from(mutation.addedNodes);
                const containsMessage = addedNodes.some(node => {
                    return node.classList && node.classList.contains('message');
                });

                if (containsMessage) {
                    scrollToBottom();
                }
            }
        });
    });

    // 观察对话容器
    const conversationContainers = document.querySelectorAll('.ai-conversation');
    conversationContainers.forEach(container => {
        observer.observe(container, { childList: true, subtree: true });
    });
</script>
""")