document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chatMessages');
    const chatForm = document.getElementById('chatForm');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');

    // 智能体信息映射
    const agentInfo = {
        'main_agent': {
            name: '汤圆Agent',
            initial: '汤',
            avatarClass: 'main-agent'
        },
        'time_agent': {
            name: '时间管理者',
            initial: '时',
            avatarClass: 'time-agent'
        },
        'scheduling_agent': {
            name: '调度助手',
            initial: '调',
            avatarClass: 'scheduling-agent'
        }
    };

    // 当前活跃的消息容器（用于流式内容）
    let currentMessageDiv = null;
    let currentMessageType = null;
    let currentAgentId = null;

    // 添加欢迎消息
    addMessage('您好！我是多智能体对话系统，有什么我可以帮您的吗？', 'ai', 'main_agent');

    // 处理表单提交
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const message = userInput.value.trim();
        if (!message) return;

        // 添加用户消息到聊天界面
        addMessage(message, 'user');
        userInput.value = '';
        sendButton.disabled = true;
        chatForm.classList.add('loading');

        try {
            // 显示打字指示器
            showTypingIndicator();

            // 重置当前消息状态
            currentMessageDiv = null;
            currentMessageType = null;
            currentAgentId = null;

            // 发送请求并处理流式响应
            await handleStreamingResponse(message);
        } catch (error) {
            console.error('Error:', error);
            // 移除打字指示器
            removeTypingIndicator();
            addMessage('抱歉，出现了一些问题。请稍后再试。', 'ai', 'main_agent');
        } finally {
            sendButton.disabled = false;
            chatForm.classList.remove('loading');
            userInput.focus();
        }
    });

    function addMessage(text, sender, agentId = null) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');

        if (sender === 'user') {
            messageDiv.classList.add('user-message');
            messageDiv.innerHTML = `
                <div class="message-content">${text}</div>
            `;
        } else if (sender === 'system') {
            messageDiv.classList.add('system-message');
            messageDiv.innerHTML = `
                <div class="message-content">${text}</div>
            `;
        } else if (sender === 'usage') {
            messageDiv.classList.add('usage-message');
            messageDiv.innerHTML = `
                <div class="message-content">${text}</div>
            `;
        } else {
            messageDiv.classList.add('ai-message');
            const agentData = agentInfo[agentId || 'main_agent'];
            messageDiv.innerHTML = `
                <div class="message-avatar ${agentData.avatarClass}">${agentData.initial}</div>
                <div class="message-content">${text}</div>
            `;
        }

        chatMessages.appendChild(messageDiv);
        scrollToBottom();

        // 返回消息容器，以便后续追加内容
        return messageDiv;
    }

    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;
        chatMessages.appendChild(typingDiv);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    function scrollToBottom() {
        chatMessages.scrollTo({
            top: chatMessages.scrollHeight,
            behavior: 'smooth'
        });
    }

    async function handleStreamingResponse(userMessage) {
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: userMessage })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // 处理SSE格式的数据
                const lines = buffer.split('\n\n');
                buffer = lines.pop() || ''; // 保留不完整的最后一行

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const dataStr = line.substring(6); // 移除'data: '前缀
                            const data = JSON.parse(dataStr);

                            if (data.type === 'chunk') {
                                const messageData = data.content;

                                // 移除打字指示器（当收到第一条实际消息时）
                                removeTypingIndicator();

                                if (typeof messageData === 'object' && messageData !== null) {
                                    // 根据消息类型和来源决定是否创建新消息框或追加到现有消息框
                                    const messageType = messageData.type;
                                    const agentId = messageData.agent_id || 'main_agent';

                                    if (messageType === 'agent_message') {
                                        // AI消息 - 检查是否是同一个agent的连续消息
                                        if (currentMessageType === 'agent_message' && currentAgentId === agentId) {
                                            // 追加到当前消息框
                                            const contentDiv = currentMessageDiv.querySelector('.message-content');
                                            contentDiv.textContent += messageData.content;
                                        } else {
                                            // 创建新的消息框
                                            currentMessageDiv = addMessage(messageData.content, 'ai', agentId);
                                            currentMessageType = 'agent_message';
                                            currentAgentId = agentId;
                                        }
                                    } else if (messageType === 'usage') {
                                        // 用量信息总是新消息框
                                        addMessage(messageData.content, 'usage');
                                        currentMessageDiv = null;
                                        currentMessageType = null;
                                        currentAgentId = null;
                                    } else if (messageType === 'system') {
                                        // 系统消息总是新消息框
                                        addMessage(messageData.content, 'system');
                                        currentMessageDiv = null;
                                        currentMessageType = null;
                                        currentAgentId = null;
                                    } else if (messageType === 'error') {
                                        addMessage(messageData.content, 'ai', 'main_agent');
                                        currentMessageDiv = null;
                                        currentMessageType = null;
                                        currentAgentId = null;
                                    }
                                } else {
                                    // 兼容旧格式 - 默认为主agent消息
                                    if (currentMessageType === 'agent_message' && currentAgentId === 'main_agent') {
                                        const contentDiv = currentMessageDiv.querySelector('.message-content');
                                        contentDiv.textContent += messageData;
                                    } else {
                                        currentMessageDiv = addMessage(messageData, 'ai', 'main_agent');
                                        currentMessageType = 'agent_message';
                                        currentAgentId = 'main_agent';
                                    }
                                }

                                scrollToBottom();
                            } else if (data.type === 'end') {
                                // 流结束
                                break;
                            }
                        } catch (parseError) {
                            console.error('Failed to parse SSE data:', parseError);
                            // 如果解析失败，当作普通文本处理
                            const content = line.substring(6);
                            if (currentMessageType === 'agent_message' && currentAgentId === 'main_agent') {
                                const contentDiv = currentMessageDiv.querySelector('.message-content');
                                contentDiv.textContent += content;
                            } else {
                                currentMessageDiv = addMessage(content, 'ai', 'main_agent');
                                currentMessageType = 'agent_message';
                                currentAgentId = 'main_agent';
                            }
                            scrollToBottom();
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Streaming error:', error);
            removeTypingIndicator();
            addMessage('抱歉，无法连接到AI服务。', 'ai', 'main_agent');
        }
    }

    // 初始焦点
    userInput.focus();

    // 回车发送消息（除了Shift+Enter）
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
});