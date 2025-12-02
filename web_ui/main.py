import streamlit as st
import time
from datetime import datetime

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
        font-family: sans-serif;
    }

    .container {
        width: 100%;
        max-width: 1200px;
        margin: 0 auto;
        background-color: white;
        border: 2px solid #000;
        overflow: hidden;
    }

    .header {
        background-color: white;
        padding: 20px;
        border-bottom: 2px solid #000;
        text-align: center;
    }

    .header h1 {
        font-size: 2rem;
        margin-bottom: 8px;
    }

    .input-section {
        padding: 15px;
        border-bottom: 2px solid #000;
    }

    .user-input-box {
        border: 2px solid #000;
        padding: 10px;
    }

    .conversation-section {
        padding: 15px;
        min-height: 500px;
    }

    .single-conversation {
        display: flex;
        flex-direction: column;
    }

    .dual-conversation {
        display: flex;
        gap: 15px;
    }

    .ai-box {
        flex: 1;
        border: 2px solid #000;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        height: 450px;
    }

    .ai-header {
        background-color: #fff;
        color: #000;
        padding: 10px;
        display: flex;
        align-items: center;
        border-bottom: 2px solid #000;
    }

    .ai-avatar {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        background-color: #000;
        display: flex;
        justify-content: center;
        align-items: center;
        margin-right: 10px;
        font-weight: bold;
        color: #fff;
    }

    .ai-name {
        font-weight: bold;
        font-size: 1rem;
    }

    .ai-conversation {
        flex: 1;
        padding: 10px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
    }

    .message {
        margin-bottom: 10px;
        padding: 8px 12px;
        border-radius: 5px;
        max-width: 90%;
        animation: fadeIn 0.3s;
        font-size: 0.9rem;
        word-wrap: break-word;
    }

    .ai-message {
        background-color: #f0f0f0;
        align-self: flex-start;
        border-left: 4px solid #000;
    }

    .user-message {
        background-color: #000;
        color: white;
        align-self: flex-end;
        border-right: 4px solid #007bff;
    }

    .system-message {
        background-color: #fff;
        border: 1px solid #ccc;
        text-align: center;
        max-width: 95%;
        margin: 10px auto;
        font-style: italic;
        color: #666;
        border-left: 4px solid #ff6b6b;
    }

    .tool-message {
        background-color: #fff;
        border: 1px dashed #000;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 0.8rem;
        color: #333;
        border-left: 4px solid #ffd166;
    }

    .collaboration-indicator {
        background-color: #f0f0f0;
        padding: 8px 12px;
        border-radius: 5px;
        margin: 10px 0;
        text-align: center;
        font-size: 0.9rem;
        color: #000;
        border-left: 4px solid #000;
    }

    .typing-indicator {
        display: flex;
        align-items: center;
        margin-top: 5px;
        padding-left: 10px;
    }

    .typing-dots {
        display: flex;
        margin-left: 10px;
    }

    .typing-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: #000;
        margin: 0 2px;
        animation: typing 1.4s infinite ease-in-out;
    }

    .typing-dot:nth-child(1) {
        animation-delay: -0.32s;
    }

    .typing-dot:nth-child(2) {
        animation-delay: -0.16s;
    }

    /* 动画 */
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

    @keyframes typing {
        0%, 80%, 100% { 
            transform: scale(0.8); 
            opacity: 0.5; 
        }
        40% { 
            transform: scale(1); 
            opacity: 1; 
        }
    }

    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 确保滚动条样式 */
    .ai-conversation::-webkit-scrollbar {
        width: 6px;
    }

    .ai-conversation::-webkit-scrollbar-track {
        background: #f0f0f0;
    }

    .ai-conversation::-webkit-scrollbar-thumb {
        background: #000;
        border-radius: 3px;
    }

    @media (max-width: 768px) {
        .dual-conversation {
            flex-direction: column;
        }
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

# 模拟 Agent 对话流程
if st.session_state.is_processing:
    # 根据当前状态模拟对话
    if st.session_state.current_agent == "scheduling_agent":
        # 第一步：调度 Agent 回复
        time.sleep(1.5)
        st.session_state.agent1_messages.append({
            "role": "ai",
            "content": "我理解您的问题，让我为您分析一下。",
            "timestamp": datetime.now()
        })
        st.session_state.current_agent = "calling_ai2"
        st.rerun()

    elif st.session_state.current_agent == "calling_ai2":
        # 调度 Agent 召唤时间Agent
        time.sleep(1)
        st.session_state.agent1_messages.append({
            "role": "ai",
            "content": "让我召唤时间Agent来提供更专业的意见。",
            "timestamp": datetime.now()
        })

        # 切换到双列模式
        st.session_state.show_dual = True

        st.session_state.current_agent = "time_agent_thinking"
        st.rerun()

    elif st.session_state.current_agent == "time_agent_thinking":
        # 时间 Agent 开始处理
        time.sleep(1.5)
        st.session_state.agent2_messages.append({
            "role": "ai",
            "content": "感谢调度Agent的召唤。我正在查询当前时间...",
            "timestamp": datetime.now()
        })
        st.session_state.current_agent = "time_agent_tool"
        st.rerun()

    elif st.session_state.current_agent == "time_agent_tool":
        # 时间 Agent 调用工具
        time.sleep(1)
        st.session_state.agent2_messages.append({
            "role": "tool",
            "content": "调用工具：get_time",
            "timestamp": datetime.now()
        })
        st.session_state.current_agent = "time_agent_result"
        st.rerun()

    elif st.session_state.current_agent == "time_agent_result":
        # 时间 Agent 返回结果
        time.sleep(1.5)
        st.session_state.agent2_messages.append({
            "role": "ai",
            "content": "✅ 查询成功！当前时间是：11:03",
            "timestamp": datetime.now()
        })
        st.session_state.current_agent = "scheduling_summary"
        st.rerun()

    elif st.session_state.current_agent == "scheduling_summary":
        # 调度 Agent 总结
        time.sleep(1)
        st.session_state.agent1_messages.append({
            "role": "ai",
            "content": "感谢时间Agent的补充。基于我们的讨论，当前时间是11:03。",
            "timestamp": datetime.now()
        })
        st.session_state.current_agent = "completion"
        st.rerun()

    elif st.session_state.current_agent == "completion":
        # 调度 Agent 标记任务完成
        time.sleep(0.5)
        st.session_state.agent1_messages.append({
            "role": "tool",
            "content": "🏁 标记任务完成",
            "timestamp": datetime.now()
        })

        st.session_state.is_processing = False
        st.session_state.current_agent = None
        st.rerun()

# 状态栏
st.markdown("---")
col_status1, col_status2, col_status3 = st.columns([1, 1, 1])
with col_status1:
    status_text = "🟢 就绪" if not st.session_state.is_processing else "🟡 处理中..."
    st.caption(f"{status_text}")
with col_status2:
    st.caption(f"📊 调度Agent消息: {len(st.session_state.agent1_messages)}")
with col_status3:
    st.caption(f"📊 时间Agent消息: {len(st.session_state.agent2_messages)}")

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