import streamlit as st
import time
from datetime import datetime
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import Dumplings
import os
load_dotenv()


# ====Agent====
class agent(Dumplings.BaseAgent):
    def __init__(self):
        super().__init__()

    def out(self,content:str)->str:
        st.session_state.agent2_messages.append({
            "role": "tool",
            "content": "调用工具：get_time",
            "timestamp": datetime.now()
        })
        st.session_state.current_agent = "time_agent_result"


@Dumplings.tool_registry.register_tool(allowed_agents=["8841cd45eef54217bc8122cafebe5fd6", "time_agent"], name="get_time")
def get_time(xml:str) -> str:
    return "11:03"

@Dumplings.register_agent("main", "scheduling_agent")
class scheduling_agent(Dumplings.BaseAgent):
    prompt = f"你是一个名为汤圆Agent的AGI，你可以用<ask_for_help><agent_id>id</agent_id><message>message</message></ask_for_help>的方式与其他Agent通讯, 你可以使用<attempt_completion>标签退出对话， 它的语法为<attempt_completion><report_content>放入你想播报的内容，或留空</report_content></attempt_completion>"
    api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model_name = "deepseek-v3.2-exp"
    api_key = os.getenv("API_KEY")
    def __init__(self):
        super().__init__()

@Dumplings.register_agent("8841cd45eef54217bc8122cafebe5fd6", "time_agent")
class time_agent(Dumplings.BaseAgent):
    prompt = "你是一个名为汤圆Agent的AGI的子agent名为时间管理者，你可以用<ask_for_help><agent_id>id</agent_id><message>message</message></ask_for_help>的方式与其他Agent通讯, 你还有get_time可以查询时间（直接<get_time></get_time>即可）"
    api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model_name = "deepseek-v3.2-exp"
    api_key = os.getenv("API_KEY")
    def __init__(self):
        super().__init__()


# 页面配置
st.set_page_config(
    page_title="AI协作对话系统",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS - 类似上面HTML的简洁样式
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

    /* =========================================== */
    /* 状态栏样式 - 改为黑色 */
    /* =========================================== */
    
    /* 状态栏容器 */
    .st-emotion-cache-1qg05tj.e1f1d6gn1 {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        padding: 12px 20px !important;
        margin-top: 20px !important;
        border-radius: 8px !important;
        border: 2px solid #000000 !important;
    }

    /* 状态栏分隔线 */
    hr {
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, #1a1a1a, #007bff, #1a1a1a) !important;
        margin: 20px 0 !important;
        opacity: 0.8 !important;
    }

    /* 状态栏文本 */
    .st-caption {
        color: #ffffff !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        padding: 6px 12px !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 6px !important;
        border-left: 3px solid #007bff !important;
        margin: 2px 0 !important;
        transition: all 0.3s ease !important;
    }

    .st-caption:hover {
        background-color: rgba(255, 255, 255, 0.15) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 8px rgba(0, 123, 255, 0.2) !important;
    }

    /* 状态栏列 */
    .st-emotion-cache-keje6w.e1f1d6gn2 {
        background-color: #2c2c2c !important;
        border-radius: 8px !important;
        padding: 8px !important;
        margin: 4px !important;
        border: 1px solid #404040 !important;
    }

    /* 状态文本特定样式 */
    .st-caption:contains("🟢"),
    .st-caption:contains("🟡") {
        background: linear-gradient(135deg, rgba(0, 123, 255, 0.2), rgba(0, 123, 255, 0.1)) !important;
        border-left: 3px solid #28a745 !important;
    }

    .st-caption:contains("📊") {
        background: linear-gradient(135deg, rgba(108, 117, 125, 0.2), rgba(108, 117, 125, 0.1)) !important;
        border-left: 3px solid #6c757d !important;
    }

    /* 状态栏状态颜色 */
    .st-caption:contains("🟢") {
        color: #28a745 !important;
        font-weight: 600 !important;
    }

    .st-caption:contains("🟡") {
        color: #ffc107 !important;
        font-weight: 600 !important;
    }

    /* 确保状态栏在移动端也有良好显示 */
    @media (max-width: 768px) {
        .st-emotion-cache-1qg05tj.e1f1d6gn1 {
            padding: 10px 15px !important;
            margin: 15px 10px !important;
        }
        
        .st-caption {
            font-size: 0.85rem !important;
            padding: 5px 8px !important;
        }
    }

    /* 确保状态栏文字与背景的高对比度 */
    .st-caption {
        text-shadow: 0 1px 1px rgba(0, 0, 0, 0.3) !important;
    }
</style>
""")


# 初始化会话状态
def init_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.agent1_messages = []
        st.session_state.agent2_messages = []
        st.session_state.is_processing = False
        st.session_state.current_agent = None
        st.session_state.show_dual = False  # 初始不显示双列
        # 添加初始消息
        st.session_state.agent1_messages.append({
            "role": "ai",
            "content": "您好！我是调度Agent。我可以处理您的问题，并在需要时召唤时间Agent提供专业支持。",
            "timestamp": datetime.now()
        })


init_session_state()

# 页面结构
st.html("""
<div class="container">
    <div class="header">
        <h1>🤖 AI协作对话系统</h1>
        <p>调度Agent与时间Agent的协作对话</p>
    </div>
""")

# 使用一个空的占位符来确保每次更新都会重新渲染对话
conversation_placeholder = st.empty()


# 构建完整的对话HTML内容
def build_conversation_html():
    html = '<div class="conversation-section">'

    if not st.session_state.show_dual:
        # 单列模式 - 只显示调度Agent
        html += '''
        <div class="single-conversation">
            <div class="ai-box">
                <div class="ai-header">
                    <div class="ai-avatar">AI1</div>
                    <div class="ai-name">调度 Agent</div>
                </div>
                <div class="ai-conversation">
        '''

        # 调度Agent的消息
        for msg in st.session_state.agent1_messages:
            if msg["role"] == "user":
                html += f'''
                <div class="message user-message">
                    <div class="message-text">{msg["content"]}</div>
                </div>
                '''
            elif msg["role"] == "ai":
                html += f'''
                <div class="message ai-message">
                    <div class="message-text">{msg["content"]}</div>
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

        # 打字指示器
        if st.session_state.is_processing and st.session_state.current_agent == "scheduling_agent":
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

        html += '</div></div></div>'  # 关闭ai-conversation, ai-box和single-conversation

        # 协作指示器
        if st.session_state.is_processing and st.session_state.current_agent == "calling_ai2":
            html += '''
            <div class="collaboration-indicator">
                调度Agent正在召唤时间Agent参与讨论...
            </div>
            '''
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

        # 调度Agent的消息
        for msg in st.session_state.agent1_messages:
            if msg["role"] == "user":
                html += f'''
                <div class="message user-message">
                    <div class="message-text">{msg["content"]}</div>
                </div>
                '''
            elif msg["role"] == "ai":
                html += f'''
                <div class="message ai-message">
                    <div class="message-text">{msg["content"]}</div>
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

        # 打字指示器
        if st.session_state.is_processing and st.session_state.current_agent == "scheduling_agent":
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

        html += '</div></div>'  # 关闭ai-conversation和ai-box

        # 右侧列 - 时间Agent
        html += '''
        <div class="ai-box">
            <div class="ai-header">
                <div class="ai-avatar">AI2</div>
                <div class="ai-name">时间 Agent</div>
            </div>
            <div class="ai-conversation">
        '''

        # 时间Agent的消息
        for msg in st.session_state.agent2_messages:
            if msg["role"] == "ai":
                html += f'''
                <div class="message ai-message">
                    <div class="message-text">{msg["content"]}</div>
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

        # 打字指示器
        if st.session_state.is_processing and st.session_state.current_agent in ["time_agent_thinking",
                                                                                 "time_agent_result"]:
            html += '''
            <div class="typing-indicator">
                <div class="ai-avatar" style="width:25px;height:25px;font-size:0.8rem;">AI2</div>
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
            '''

        html += '</div></div></div>'  # 关闭ai-conversation, ai-box和dual-conversation

    html += '</div>'  # 关闭conversation-section
    return html


# 使用占位符显示对话内容，每次都会完全重新渲染
conversation_placeholder.html(build_conversation_html())

# 输入区域
st.html('<div class="input-section">')
st.html('<div class="user-input-box">')

# 修复：给text_area一个有效的label参数
user_input = st.text_area(
    "输入指令",  # 添加一个非空标签
    height=100,
    key="user_input",
    label_visibility="collapsed",  # 隐藏标签但保留可访问性
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

# 处理清空对话
if clear_button and not st.session_state.is_processing:
    st.session_state.agent1_messages = [{
        "role": "ai",
        "content": "您好！我是调度Agent。我可以处理您的问题，并在需要时召唤时间Agent提供专业支持。",
        "timestamp": datetime.now()
    }]
    st.session_state.agent2_messages = []
    st.session_state.show_dual = False  # 重置为单列模式
    st.session_state.is_processing = False
    st.session_state.current_agent = None
    st.rerun()

# 处理发送指令
if send_button and user_input.strip() and not st.session_state.is_processing:
    # 添加用户消息到调度 Agent
    st.session_state.agent1_messages.append({
        "role": "user",
        "content": user_input.strip(),
        "timestamp": datetime.now()
    })

    # 设置为处理中
    st.session_state.is_processing = True
    st.session_state.current_agent = "scheduling_agent"

    # 模拟 Agent 对话流程
    st.rerun()

def get_tool_name(xml: str) -> str:
    xml_pattern = re.compile(r'<(\w+)>.*?</\1>', flags=re.S)
    clean_pattern = re.compile(r'</?(out_text|thinking)>', flags=re.S)
    clean_content = clean_pattern.sub('', xml)
    xml_blocks = [m.group(0) for m in xml_pattern.finditer(clean_content)]
    for block in xml_blocks:
        soup = BeautifulSoup(block, "xml")
        root = soup.find()
        if root is None:
            raise ValueError("空 XML")
        tool_name = root.name
        return tool_name

# 模拟 Agent 对话流程
if st.session_state.is_processing:
    pass

# 替换原来的状态栏代码
st.html(f"""
    <div style="display: flex; justify-content: space-around; color: white; font-weight: bold;">
        <div style="color: #4ade80; padding: 8px 15px; background: rgba(74, 222, 128, 0.15); border-radius: 8px; border: 1px solid #4ade80;">
            🟢 就绪
        </div>
        <div style="color: #60a5fa; padding: 8px 15px; background: rgba(96, 165, 250, 0.15); border-radius: 8px; border: 1px solid #60a5fa;">
            📊 调度Agent消息: {len(st.session_state.agent1_messages)}
        </div>
        <div style="color: #60a5fa; padding: 8px 15px; background: rgba(96, 165, 250, 0.15); border-radius: 8px; border: 1px solid #60a5fa;">
            📊 时间Agent消息: {len(st.session_state.agent2_messages)}
        </div>
    </div>
""")

# 添加JavaScript自动滚动到底部
st.html("""
<script>
    // 页面加载完成后自动滚动到底部
    window.onload = function() {
        // 给所有对话容器添加自动滚动
        const conversationContainers = document.querySelectorAll('.ai-conversation');
        conversationContainers.forEach(container => {
            container.scrollTop = container.scrollHeight;
        });
    };

    // 监听Streamlit的页面更新
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            // 当对话内容更新时，滚动到底部
            const conversationContainers = document.querySelectorAll('.ai-conversation');
            conversationContainers.forEach(container => {
                container.scrollTop = container.scrollHeight;
            });
        });
    });

    // 观察整个文档的变化
    observer.observe(document.body, { childList: true, subtree: true });
</script>
""")