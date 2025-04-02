// 立即执行函数表达式
(function () {
    // DOM元素
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const newChatButton = document.getElementById('new-chat-button');
    const historyList = document.getElementById('history-list');
    const filesList = document.getElementById('files-list');
    const refreshFilesButton = document.getElementById('refresh-files-button');
    const sidebar = document.getElementById('sidebar');
    const sidebarOpen = document.getElementById('sidebar-open');
    const sidebarClose = document.getElementById('sidebar-close');
    const loader = document.getElementById('loader');
    const connectionStatus = document.getElementById('connection-status');
    const statusIndicator = connectionStatus ? connectionStatus.querySelector('.status-indicator') : null;
    const statusText = connectionStatus ? connectionStatus.querySelector('.status-text') : null;
    const scrollBottomBtn = document.getElementById('scroll-bottom');

    // 全局变量
    let socket = null;
    let sessionId = localStorage.getItem('currentSessionId') || null;
    let chatHistory = JSON.parse(localStorage.getItem('chatHistory')) || [];
    let currentChatMessages = JSON.parse(localStorage.getItem('currentChatMessages')) || []; // 当前对话的消息历史
    let isProcessing = false;
    let currentAssistantMessage = null; // 当前助手消息元素
    let currentLogGroup = null; // 当前日志组
    let currentStepId = 0; // 当前步骤ID
    let messageIdCounter = 1; // 消息ID计数器

    // DOM加载完成后初始化应用
    document.addEventListener('DOMContentLoaded', function () {
        console.log('DOM加载完成，开始初始化应用...');
        initialize();

        // 监听窗口调整大小，更新文本区域高度
        window.addEventListener('resize', adjustTextareaHeight);
    });

    // 更新连接状态指示器
    function updateConnectionStatus(status) {
        if (!statusIndicator || !statusText) {
            console.warn('连接状态指示器元素未找到');
            return;
        }

        statusIndicator.classList.remove('connecting', 'disconnected');

        switch (status) {
            case 'connected':
                statusIndicator.style.backgroundColor = 'var(--success-color)';
                statusText.textContent = '已连接';
                break;
            case 'connecting':
                statusIndicator.classList.add('connecting');
                statusText.textContent = '连接中...';
                break;
            case 'disconnected':
                statusIndicator.classList.add('disconnected');
                statusText.textContent = '已断开';
                break;
            case 'error':
                statusIndicator.classList.add('disconnected');
                statusText.textContent = '连接错误';
                break;
            default:
                statusIndicator.style.backgroundColor = 'var(--warning-color)';
                statusText.textContent = '未知状态';
        }
    }

    // 自动调整输入框高度
    function adjustTextareaHeight() {
        if (!chatInput) {
            return;
        }

        chatInput.style.height = 'auto';
        chatInput.style.height = (chatInput.scrollHeight) + 'px';

        // 高度限制
        if (chatInput.scrollHeight > 150) {
            chatInput.style.overflowY = 'auto';
        } else {
            chatInput.style.overflowY = 'hidden';
        }
    }

    // 滚动消息区域到底部
    function scrollToBottom(smooth = true) {
        if (!chatMessages) {
            console.warn('未找到聊天消息区域元素，无法滚动到底部');
            return;
        }

        chatMessages.scrollTo({
            top: chatMessages.scrollHeight,
            behavior: smooth ? 'smooth' : 'auto'
        });
    }

    // 切换回到底部按钮显示
    function toggleScrollBottomBtn() {
        const isScrolledToBottom = chatMessages.scrollHeight - chatMessages.clientHeight <= chatMessages.scrollTop + 50;
        if (isScrolledToBottom) {
            scrollBottomBtn.classList.remove('visible');
        } else {
            scrollBottomBtn.classList.add('visible');
        }
    }

    // 生成唯一消息ID
    function generateMessageId() {
        return `msg-${Date.now()}-${messageIdCounter++}`;
    }

    // 添加消息到聊天区域
    function addMessage(content, sender, isThinking = false) {
        const messageId = generateMessageId();

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        messageDiv.id = messageId;

        // 创建头像
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = sender === 'user' ? '<i class="ri-user-3-line"></i>' : '<i class="ri-robot-line"></i>';

        // 创建消息内容
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // 创建消息包装器
        const messageContentWrapper = document.createElement('div');
        messageContentWrapper.className = 'message-content-wrapper';

        // 支持Markdown格式的消息内容
        if (sender === 'assistant' && typeof content === 'string') {
            contentDiv.innerHTML = formatMessage(content);
        } else {
            contentDiv.textContent = content;
        }

        // 创建时间
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';

        const now = new Date();
        timeDiv.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // 组装消息
        messageDiv.appendChild(avatarDiv);
        messageContentWrapper.appendChild(contentDiv);
        messageContentWrapper.appendChild(timeDiv);
        messageDiv.appendChild(messageContentWrapper);

        // 如果是思考中的消息，添加思考动画
        if (isThinking) {
            contentDiv.classList.add('typing-animation');
        }

        // 添加到聊天区域
        chatMessages.appendChild(messageDiv);

        // 滚动到底部
        scrollToBottom();

        // 如果不是思考状态，保存消息到当前对话历史
        if (!isThinking) {
            // 保存消息到当前对话历史
            currentChatMessages.push({
                content: content,
                sender: sender,
                time: now.toISOString(),
                id: messageId
            });

            // 保存到localStorage
            localStorage.setItem('currentChatMessages', JSON.stringify(currentChatMessages));

            // 保存到会话历史
            saveCurrentChatHistory();
        }

        // 如果是用户消息，存储到历史记录中
        if (sender === 'user') {
            addToHistory(content);
        }

        // 如果是助手消息并且不是思考状态，更新当前助手消息引用
        if (sender === 'assistant' && !isThinking) {
            currentAssistantMessage = messageDiv;
        }

        return { element: messageDiv, contentElement: contentDiv, id: messageId };
    }

    // 添加或更新思考内容
    function addOrUpdateThinking(content) {
        // 创建新的思考消息
        const messageObj = addMessage(content, 'assistant', true);
        return messageObj;
    }

    // 添加日志消息
    function addLogMessage(message, type = 'default') {
        // 如果没有当前日志组，创建一个
        if (!currentLogGroup) {
            createLogGroup();
        }

        const logContent = currentLogGroup.querySelector('.log-group-content');

        const logMessage = document.createElement('div');
        logMessage.className = `log-message log-${type}`;

        // 根据日志类型进行格式化
        if (type === 'thinking') {
            // 思考内容可能是markdown
            logMessage.innerHTML = formatMessage(message);
        } else {
            // 其他日志保持原始格式
            logMessage.textContent = message;
        }

        logContent.appendChild(logMessage);

        // 展开日志组
        expandLogGroup(currentLogGroup);

        // 滚动到底部
        scrollToBottom();

        return logMessage;
    }

    // 创建日志组
    function createLogGroup() {
        // 创建新的日志组
        currentStepId++;

        const logGroup = document.createElement('div');
        logGroup.className = 'log-group';
        logGroup.id = `log-group-${currentStepId}`;

        const logGroupHeader = document.createElement('div');
        logGroupHeader.className = 'log-group-header';
        logGroupHeader.innerHTML = `
            <span>执行步骤 ${currentStepId}</span>
            <i class="ri-arrow-right-s-line log-group-toggle"></i>
        `;

        const logGroupContent = document.createElement('div');
        logGroupContent.className = 'log-group-content';

        logGroup.appendChild(logGroupHeader);
        logGroup.appendChild(logGroupContent);

        // 点击标题切换展开/折叠
        logGroupHeader.addEventListener('click', function () {
            toggleLogGroup(logGroup);
        });

        // 添加到聊天区域
        chatMessages.appendChild(logGroup);

        // 更新当前日志组
        currentLogGroup = logGroup;

        return logGroup;
    }

    // 展开日志组
    function expandLogGroup(logGroup) {
        logGroup.classList.add('expanded');
    }

    // 折叠日志组
    function collapseLogGroup(logGroup) {
        logGroup.classList.remove('expanded');
    }

    // 切换日志组展开/折叠状态
    function toggleLogGroup(logGroup) {
        logGroup.classList.toggle('expanded');
    }

    // 解析日志消息类型
    function parseLogType(message) {
        if (message.includes('Executing step')) {
            return 'step';
        } else if (message.includes('Token usage:')) {
            return 'token';
        } else if (message.includes('Activating tool:')) {
            return 'tool';
        } else if (message.includes('Manus\'s thoughts:')) {
            return 'thinking';
        } else if (message.includes('completed its mission!')) {
            return 'result';
        } else {
            return 'default';
        }
    }

    // 提取思考内容
    function extractThoughts(message) {
        if (message.includes('✨ Manus\'s thoughts:')) {
            let thoughts = message.split('✨ Manus\'s thoughts:')[1].trim();

            // 如果包含tool_call，只保留前面的内容
            if (thoughts.includes('<tool_call>')) {
                thoughts = thoughts.split('<tool_call>')[0].trim();
            }

            return thoughts;
        }
        return '';
    }

    // 简单的Markdown格式化（支持代码块和链接）
    function formatMessage(text) {
        // 转义HTML特殊字符
        text = text.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // 代码块 (```code```)
        text = text.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

        // 内联代码 (`code`)
        text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

        // 链接 ([text](url))
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

        // 粗体 (**text**)
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // 斜体 (*text*)
        text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // 换行符转换为<br>
        text = text.replace(/\n/g, '<br>');

        return text;
    }

    // 将用户消息添加到历史记录
    function addToHistory(message) {
        const now = new Date();
        const today = new Date().setHours(0, 0, 0, 0);
        const yesterday = today - 86400000;

        let timeLabel;
        if (now.getTime() >= today) {
            timeLabel = '今天 ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else if (now.getTime() >= yesterday) {
            timeLabel = '昨天 ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else {
            timeLabel = now.toLocaleDateString([], { month: '2-digit', day: '2-digit' }) + ' ' +
                now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }

        // 创建新的历史记录项
        const historyItem = {
            id: sessionId,
            prompt: message,
            time: timeLabel,
            timestamp: now.getTime()
        };

        // 添加到历史记录数组
        chatHistory.unshift(historyItem);

        // 只保留最近的20条记录
        if (chatHistory.length > 20) {
            chatHistory = chatHistory.slice(0, 20);
        }

        // 保存到localStorage
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));

        // 更新历史记录UI
        updateHistoryUI();
    }

    // 清空所有历史记录
    function clearAllHistory() {
        if (chatHistory.length === 0) {
            return;
        }

        if (confirm('确定要清空所有历史记录吗？此操作无法撤销。')) {
            // 清空历史记录数组
            chatHistory = [];
            localStorage.setItem('chatHistory', JSON.stringify(chatHistory));

            // 清空所有会话历史
            chatHistory.forEach(item => {
                const sessionHistoryKey = `chat_history_${item.id}`;
                localStorage.removeItem(sessionHistoryKey);
            });

            // 获取所有localStorage中以chat_history_开头的键
            Object.keys(localStorage).forEach(key => {
                if (key.startsWith('chat_history_')) {
                    localStorage.removeItem(key);
                }
            });

            updateHistoryUI();

            // 显示提示消息
            const systemMessage = document.createElement('div');
            systemMessage.className = 'system-message';
            systemMessage.innerHTML = '<span>已清空所有历史记录</span>';
            chatMessages.appendChild(systemMessage);
            scrollToBottom();
        }
    }

    // 删除单条历史记录
    function deleteHistoryItem(index) {
        // 获取要删除的会话ID
        const sessionId = chatHistory[index].id;

        // 删除对应会话的历史数据
        const sessionHistoryKey = `chat_history_${sessionId}`;
        localStorage.removeItem(sessionHistoryKey);

        // 从历史记录数组中删除
        chatHistory.splice(index, 1);
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));

        // 更新UI
        updateHistoryUI();
    }

    // 更新历史记录UI
    function updateHistoryUI() {
        if (!historyList) {
            console.warn('未找到历史记录列表元素，无法更新历史UI');
            return;
        }

        // 清空列表
        historyList.innerHTML = '';

        if (chatHistory.length === 0) {
            const noHistory = document.createElement('div');
            noHistory.className = 'no-history';
            noHistory.textContent = '暂无历史记录';
            historyList.appendChild(noHistory);
        } else {
            chatHistory.forEach((item, index) => {
                const historyItem = document.createElement('div');
                historyItem.className = 'history-item';

                // 如果是当前会话，高亮显示
                if (item.id === sessionId) {
                    historyItem.style.borderLeftColor = 'var(--primary-color)';
                    historyItem.style.backgroundColor = 'var(--primary-light)';
                }

                const promptDiv = document.createElement('div');
                promptDiv.className = 'history-prompt';
                promptDiv.textContent = item.prompt;

                const timeDiv = document.createElement('div');
                timeDiv.className = 'history-time';
                timeDiv.textContent = item.time;

                // 添加删除按钮
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'history-delete-btn';
                deleteBtn.innerHTML = '<i class="ri-close-line"></i>';
                deleteBtn.title = '删除此记录';

                // 点击删除按钮删除该条历史记录
                deleteBtn.addEventListener('click', function (e) {
                    e.stopPropagation(); // 阻止事件冒泡
                    deleteHistoryItem(index);
                });

                historyItem.appendChild(promptDiv);
                historyItem.appendChild(timeDiv);
                historyItem.appendChild(deleteBtn);

                // 点击历史记录项加载对话
                historyItem.addEventListener('click', function () {
                    if (item.id !== sessionId) {
                        // 如果点击的不是当前会话，加载该会话
                        loadSession(item.id);
                    } else {
                        // 否则只是填充输入框
                        if (chatInput) {
                            chatInput.value = item.prompt;
                            adjustTextareaHeight();
                        }
                    }
                });

                historyList.appendChild(historyItem);
            });
        }
    }

    // 创建新的会话
    async function createNewSession() {
        try {
            const response = await fetch('/new-session');
            const data = await response.json();

            if (data.session_id) {
                sessionId = data.session_id;
                localStorage.setItem('currentSessionId', sessionId);
                return sessionId;
            } else {
                throw new Error('未能获取会话ID');
            }
        } catch (error) {
            console.error('创建会话失败:', error);

            // 如果API失败，生成一个客户端ID
            sessionId = 'client-' + Date.now();
            localStorage.setItem('currentSessionId', sessionId);
            return sessionId;
        }
    }

    // 加载会话
    async function loadSession(id) {
        try {
            console.log(`正在加载会话: ${id}`);

            // 关闭当前WebSocket连接
            closeWebSocket();

            // 更新当前会话ID
            sessionId = id;
            localStorage.setItem('currentSessionId', sessionId);

            // 尝试加载该会话之前的消息历史
            const sessionHistoryKey = `chat_history_${id}`;
            const savedSessionHistory = localStorage.getItem(sessionHistoryKey);

            // 清空当前消息区域
            chatMessages.innerHTML = '';

            // 添加欢迎消息
            const systemMessage = document.createElement('div');
            systemMessage.className = 'system-message';
            const span = document.createElement('span');

            if (savedSessionHistory) {
                try {
                    const messageHistory = JSON.parse(savedSessionHistory);

                    span.textContent = '已加载历史对话';
                    systemMessage.appendChild(span);
                    chatMessages.appendChild(systemMessage);

                    // 加载历史消息
                    messageHistory.forEach(msg => {
                        addMessage(msg.content, msg.sender);
                    });

                    // 更新当前对话历史
                    currentChatMessages = messageHistory;
                    localStorage.setItem('currentChatMessages', JSON.stringify(currentChatMessages));
                } catch (error) {
                    console.error('加载历史对话失败:', error);
                    // 如果加载失败，清空历史
                    currentChatMessages = [];
                    localStorage.setItem('currentChatMessages', JSON.stringify(currentChatMessages));

                    span.textContent = '对话已开始，请输入您的问题';
                    systemMessage.appendChild(span);
                    chatMessages.appendChild(systemMessage);
                }
            } else {
                span.textContent = '对话已开始，请输入您的问题';
                systemMessage.appendChild(span);
                chatMessages.appendChild(systemMessage);

                // 重置当前对话历史
                currentChatMessages = [];
                localStorage.setItem('currentChatMessages', JSON.stringify(currentChatMessages));
            }

            // 更新历史记录UI高亮
            updateHistoryUI();

            // 创建新的WebSocket连接
            connectWebSocket();

            console.log(`会话加载完成: ${id}`);
        } catch (error) {
            console.error('加载会话时出错:', error);
            showError('加载历史会话失败，请刷新页面重试');
        }
    }

    // 创建并连接WebSocket
    function connectWebSocket() {
        // 如果已经有一个活跃的连接，且状态正常，则不重新创建
        if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
            console.log('WebSocket连接已存在，无需重新创建');
            return;
        }

        // 更新连接状态
        try {
            updateConnectionStatus('connecting');
        } catch (e) {
            console.error('更新连接状态失败:', e);
        }

        // 关闭已存在的连接
        closeWebSocket();

        try {
            // 创建新的WebSocket连接
            const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            const wsUrl = `${protocol}${window.location.host}/ws/${sessionId}`;

            console.log(`正在连接到: ${wsUrl}`);
            socket = new WebSocket(wsUrl);

            // 连接打开事件
            socket.onopen = function (e) {
                console.log('WebSocket连接已建立');

                // 更新连接状态
                try {
                    updateConnectionStatus('connected');
                } catch (err) {
                    console.error('更新连接状态失败:', err);
                }

                // 重置重连次数和延迟
                socket.reconnectAttempt = 0;
            };

            // 收到消息事件
            socket.onmessage = function (event) {
                try {
                    const data = JSON.parse(event.data);
                    handleWebSocketMessage(data);
                } catch (error) {
                    console.error('解析WebSocket消息时出错:', error);
                }
            };

            // 连接关闭事件
            socket.onclose = function (event) {
                // 更新连接状态
                try {
                    updateConnectionStatus('disconnected');
                } catch (err) {
                    console.error('更新连接状态失败:', err);
                }

                if (event.wasClean) {
                    console.log(`WebSocket连接已关闭, 代码=${event.code} 原因=${event.reason}`);
                } else {
                    // 例如服务器进程被杀死或网络中断
                    console.error('WebSocket连接中断');

                    // 如果当前不在处理中，则尝试重新连接
                    if (!isProcessing) {
                        // 计算重连延迟（指数退避）
                        socket.reconnectAttempt = (socket.reconnectAttempt || 0) + 1;
                        const delay = Math.min(30000, Math.pow(1.5, socket.reconnectAttempt) * 1000);

                        console.log(`将在 ${delay}ms 后尝试重新连接 (尝试 #${socket.reconnectAttempt})`);

                        setTimeout(() => {
                            // 如果尝试次数过多，显示错误
                            if (socket.reconnectAttempt > 5) {
                                showError('连接多次失败，请刷新页面重试');
                            } else {
                                connectWebSocket();
                            }
                        }, delay);
                    }
                }
            };

            // 连接错误事件
            socket.onerror = function (error) {
                console.error('WebSocket错误:', error);
                try {
                    updateConnectionStatus('error');
                } catch (err) {
                    console.error('更新连接状态失败:', err);
                }
            };
        } catch (error) {
            console.error('创建WebSocket连接失败:', error);
            showError('无法创建WebSocket连接，请刷新页面重试');
        }
    }

    // 关闭WebSocket连接
    function closeWebSocket() {
        if (socket) {
            // 移除事件处理器以避免重连
            socket.onclose = null;

            if (socket.readyState !== WebSocket.CLOSED && socket.readyState !== WebSocket.CLOSING) {
                socket.close();
            }
        }
    }

    // 处理WebSocket消息
    function handleWebSocketMessage(data) {
        const status = data.status;

        switch (status) {
            case 'processing':
                isProcessing = true;
                showLoader(true);

                // 重置当前消息引用
                currentAssistantMessage = null;

                // 重置当前日志组
                currentLogGroup = null;
                break;

            case 'thinking':
                // 处理思考内容 - 不再覆盖，而是添加新消息
                const thinkingContent = data.message;
                addOrUpdateThinking(thinkingContent);

                // 添加到日志
                if (thinkingContent && thinkingContent.length > 10) {
                    addLogMessage(thinkingContent, 'thinking');
                }
                break;

            case 'log':
                // 解析日志类型
                const logType = parseLogType(data.message);

                // 处理日志信息
                if (logType === 'step') {
                    // 新步骤，创建新的日志组
                    currentLogGroup = createLogGroup();
                }

                if (logType === 'thinking') {
                    // 提取思考内容
                    const thoughts = extractThoughts(data.message);
                    if (thoughts && thoughts.length > 10) {
                        addLogMessage(thoughts, 'thinking');
                    }
                } else {
                    // 添加普通日志
                    addLogMessage(data.message, logType);
                }
                break;

            case 'complete':
                isProcessing = false;
                showLoader(false);

                // 添加最终回答
                if (!currentAssistantMessage) {
                    addMessage(data.result, 'assistant');
                } else {
                    // 更新现有消息内容（可能是之前的thinking消息）
                    const contentDiv = currentAssistantMessage.querySelector('.message-content');
                    contentDiv.innerHTML = formatMessage(data.result);
                    contentDiv.classList.remove('typing-animation');

                    // 更新当前会话历史中的最后一条消息
                    if (currentChatMessages.length > 0 && currentChatMessages[currentChatMessages.length - 1].sender === 'assistant') {
                        currentChatMessages[currentChatMessages.length - 1].content = data.result;
                        localStorage.setItem('currentChatMessages', JSON.stringify(currentChatMessages));
                        saveCurrentChatHistory();
                    }
                }

                // 重置状态
                currentAssistantMessage = null;
                currentLogGroup = null;
                break;

            case 'error':
                isProcessing = false;
                showLoader(false);

                showError(data.message);

                // 重置状态
                currentAssistantMessage = null;
                currentLogGroup = null;
                break;

            default:
                console.warn('未知的WebSocket消息类型:', status);
        }
    }

    // 发送消息到服务器
    function sendMessage(message) {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            showError('WebSocket连接已断开，正在尝试重新连接...');

            // 更新连接状态
            try {
                updateConnectionStatus('connecting');
            } catch (e) {
                console.error('更新连接状态失败:', e);
            }

            // 重置重连次数
            if (socket) {
                socket.reconnectAttempt = 0;
            }

            connectWebSocket();

            // 稍后重试发送
            setTimeout(() => {
                if (socket && socket.readyState === WebSocket.OPEN) {
                    try {
                        socket.send(JSON.stringify({ prompt: message }));
                    } catch (e) {
                        console.error('发送消息失败:', e);
                        showError('发送消息失败，请重试');
                    }
                } else if (socket && socket.readyState === WebSocket.CONNECTING) {
                    // 如果仍在连接中，再等待一段时间
                    setTimeout(() => {
                        if (socket && socket.readyState === WebSocket.OPEN) {
                            try {
                                socket.send(JSON.stringify({ prompt: message }));
                            } catch (e) {
                                console.error('发送消息失败:', e);
                                showError('发送消息失败，请重试');
                            }
                        } else {
                            showError('连接服务器失败，请刷新页面后重试');
                        }
                    }, 2000);
                } else {
                    showError('无法连接到服务器，请刷新页面重试');
                }
            }, 1000);

            return;
        }

        // 发送消息
        try {
            socket.send(JSON.stringify({ prompt: message }));
        } catch (error) {
            console.error('发送消息失败:', error);
            showError('发送消息失败，请重试');

            // 更新连接状态
            try {
                updateConnectionStatus('error');
            } catch (e) {
                console.error('更新连接状态失败:', e);
            }

            // 重新连接
            connectWebSocket();
        }
    }

    // 显示或隐藏加载指示器
    function showLoader(show) {
        if (show) {
            loader.style.display = 'block';
        } else {
            loader.style.display = 'none';
        }
    }

    // 显示错误消息
    function showError(message) {
        const systemMessage = document.createElement('div');
        systemMessage.className = 'system-message';
        const span = document.createElement('span');
        span.style.color = 'var(--error-color)';
        span.textContent = message;
        systemMessage.appendChild(span);
        chatMessages.appendChild(systemMessage);
        scrollToBottom();
    }

    // 开始新对话
    async function startNewChat() {
        // 清空聊天区域
        chatMessages.innerHTML = '';

        // 重置状态
        currentAssistantMessage = null;
        currentLogGroup = null;
        currentStepId = 0;

        // 重置当前对话历史
        currentChatMessages = [];
        localStorage.setItem('currentChatMessages', JSON.stringify(currentChatMessages));

        // 添加欢迎消息
        const systemMessage = document.createElement('div');
        systemMessage.className = 'system-message';
        const span = document.createElement('span');
        span.textContent = '对话已开始，请输入您的问题';
        systemMessage.appendChild(span);
        chatMessages.appendChild(systemMessage);

        // 清空输入框
        chatInput.value = '';
        adjustTextareaHeight();

        // 聚焦输入框
        chatInput.focus();

        // 创建新的会话
        if (!sessionId) {
            await createNewSession();
        }

        // 连接WebSocket
        connectWebSocket();
    }

    // 获取并显示输出文件列表
    async function fetchWorkspaceFiles() {
        try {
            const response = await fetch('/workspace-files');
            const data = await response.json();

            // 清空列表
            filesList.innerHTML = '';

            if (data.files && data.files.length > 0) {
                data.files.forEach(file => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';

                    // 根据文件类型选择图标
                    let iconClass = 'ri-file-text-line';
                    const extension = file.name.split('.').pop().toLowerCase();

                    switch (extension) {
                        case 'pdf':
                            iconClass = 'ri-file-pdf-line';
                            break;
                        case 'xlsx':
                        case 'xls':
                        case 'csv':
                            iconClass = 'ri-file-excel-line';
                            break;
                        case 'pptx':
                        case 'ppt':
                            iconClass = 'ri-file-ppt-line';
                            break;
                        case 'docx':
                        case 'doc':
                            iconClass = 'ri-file-word-line';
                            break;
                        case 'jpg':
                        case 'jpeg':
                        case 'png':
                        case 'gif':
                            iconClass = 'ri-image-line';
                            break;
                        case 'mp4':
                        case 'avi':
                        case 'mov':
                            iconClass = 'ri-video-line';
                            break;
                        case 'mp3':
                        case 'wav':
                            iconClass = 'ri-music-line';
                            break;
                        case 'zip':
                        case 'rar':
                        case '7z':
                            iconClass = 'ri-file-zip-line';
                            break;
                    }

                    const iconDiv = document.createElement('i');
                    iconDiv.className = `file-icon ${iconClass}`;

                    const nameDiv = document.createElement('div');
                    nameDiv.className = 'file-name';
                    nameDiv.textContent = file.name;

                    // 格式化文件大小
                    let fileSize = '';
                    if (file.size < 1024) {
                        fileSize = file.size + ' B';
                    } else if (file.size < 1024 * 1024) {
                        fileSize = (file.size / 1024).toFixed(1) + ' KB';
                    } else {
                        fileSize = (file.size / (1024 * 1024)).toFixed(1) + ' MB';
                    }

                    const sizeDiv = document.createElement('div');
                    sizeDiv.className = 'file-size';
                    sizeDiv.textContent = fileSize;

                    fileItem.appendChild(iconDiv);
                    fileItem.appendChild(nameDiv);
                    fileItem.appendChild(sizeDiv);

                    // 点击文件项处理
                    fileItem.addEventListener('click', () => {
                        // 对于文本文件，获取并显示内容
                        // 对于其他文件，打开链接
                        const textExtensions = ['txt', 'json', 'csv', 'md', 'py', 'js', 'html', 'css', 'xml', 'log'];

                        if (textExtensions.includes(extension)) {
                            fetchAndShowFileContent(file.path);
                        } else {
                            window.open(`/workspace/${file.path}`, '_blank');
                        }
                    });

                    filesList.appendChild(fileItem);
                });
            } else {
                const noFiles = document.createElement('div');
                noFiles.className = 'no-files';
                noFiles.textContent = '暂无文件';
                filesList.appendChild(noFiles);
            }
        } catch (error) {
            console.error('获取文件列表失败:', error);

            const errorElement = document.createElement('div');
            errorElement.className = 'no-files';
            errorElement.textContent = '获取文件列表失败';
            errorElement.style.color = 'var(--error-color)';
            filesList.appendChild(errorElement);
        }
    }

    // 获取并显示文件内容
    async function fetchAndShowFileContent(filePath) {
        try {
            const response = await fetch(`/workspace-file/${filePath}`);
            const data = await response.json();

            if (data.status === 'success') {
                // 显示文件内容（可以在聊天中显示，或者弹出模态框）
                const content = data.content;

                // 将文件内容添加到聊天中
                const systemMessage = document.createElement('div');
                systemMessage.className = 'system-message';

                const fileSpan = document.createElement('span');
                fileSpan.textContent = `文件 ${data.name} 内容：`;
                systemMessage.appendChild(fileSpan);

                chatMessages.appendChild(systemMessage);

                // 添加文件内容作为助手消息
                addMessage("```\n" + content + "\n```", 'assistant');
            } else {
                showError(`获取文件失败: ${data.message}`);
            }
        } catch (error) {
            console.error('获取文件内容失败:', error);
            showError('获取文件内容失败，请重试');
        }
    }

    // 打开输出文件夹
    async function openWorkspaceFolder() {
        try {
            const response = await fetch('/open-workspace-folder');
            const data = await response.json();

            if (data.status !== 'success') {
                showError(`打开文件夹失败: ${data.message}`);
            }
        } catch (error) {
            console.error('打开文件夹失败:', error);
            showError('打开文件夹失败，请手动打开');
        }
    }

    // 检查是否是移动设备
    function isMobileDevice() {
        return window.innerWidth <= 768;
    }

    // 初始化
    async function initialize() {
        try {
            console.log('初始化应用...');

            // 首先检查DOM元素是否正确获取
            if (!chatForm) console.warn('未找到聊天表单元素 (chat-form)');
            if (!chatInput) console.warn('未找到聊天输入框元素 (chat-input)');
            if (!chatMessages) console.warn('未找到聊天消息区域元素 (chat-messages)');
            if (!newChatButton) console.warn('未找到新建对话按钮元素 (new-chat-button)');
            if (!historyList) console.warn('未找到历史记录列表元素 (history-list)');
            if (!connectionStatus) console.warn('未找到连接状态元素 (connection-status)');
            if (!statusIndicator) console.warn('未找到状态指示器元素 (.status-indicator)');
            if (!statusText) console.warn('未找到状态文本元素 (.status-text)');

            // 添加旋转动画CSS
            const style = document.createElement('style');
            style.textContent = `
                @keyframes rotating {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                .rotating {
                    animation: rotating 1s linear infinite;
                }
            `;
            document.head.appendChild(style);

            // 初始化WebSocket连接
            const savedSessionId = localStorage.getItem('currentSessionId');
            if (savedSessionId) {
                sessionId = savedSessionId;
            } else {
                await createNewSession();
            }

            // 绑定清空历史记录按钮事件
            const clearHistoryButton = document.getElementById('clear-history-button');
            if (clearHistoryButton) {
                console.log('绑定清空历史记录按钮事件');

                // 确保按钮可见
                clearHistoryButton.style.display = 'inline-flex';
                clearHistoryButton.innerHTML = '<i class="ri-delete-bin-line"></i>';

                clearHistoryButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    clearAllHistory();
                });
            } else {
                console.error('未找到清空历史记录按钮，尝试创建一个');

                // 如果按钮不存在，尝试创建一个
                const historyHeader = document.querySelector('.chat-history h3');

                if (historyHeader) {
                    const newClearButton = document.createElement('button');
                    newClearButton.id = 'clear-history-button';
                    newClearButton.className = 'history-action-button';
                    newClearButton.title = '清空历史记录';
                    newClearButton.innerHTML = '<i class="ri-delete-bin-line"></i>';

                    newClearButton.addEventListener('click', function (e) {
                        e.preventDefault();
                        e.stopPropagation();
                        clearAllHistory();
                    });

                    historyHeader.appendChild(newClearButton);
                    console.log('已创建清空历史记录按钮');
                }
            }

            // 聊天表单提交事件
            if (chatForm) {
                chatForm.addEventListener('submit', function (e) {
                    e.preventDefault();
                    if (!chatInput) {
                        console.error('未找到聊天输入框元素，无法提交消息');
                        return;
                    }

                    const message = chatInput.value.trim();

                    if (message && !isProcessing) {
                        // 保存用户输入
                        const userMessage = message;

                        // 清空输入框
                        chatInput.value = '';
                        adjustTextareaHeight();

                        // 确保有会话ID
                        (async function () {
                            // 如果没有会话ID，创建一个新的
                            if (!sessionId) {
                                await createNewSession();
                                await startNewChat();
                            }

                            // 添加用户消息
                            addMessage(userMessage, 'user');

                            // 发送消息到服务器
                            sendMessage(userMessage);

                            // 更新历史记录UI
                            updateHistoryUI();
                        })();
                    }
                });
            }

            // 新对话按钮点击事件
            if (newChatButton) {
                newChatButton.addEventListener('click', async function () {
                    try {
                        // 如果正在处理，先询问用户
                        if (isProcessing) {
                            if (!confirm('当前有正在进行的对话，确定要开始新对话吗？')) {
                                return;
                            }
                        }

                        // 关闭当前WebSocket连接
                        closeWebSocket();

                        // 重置会话ID
                        sessionId = null;
                        localStorage.removeItem('currentSessionId');

                        // 创建新的会话ID
                        await createNewSession();

                        // 开始新对话
                        await startNewChat();

                        // 更新历史记录UI
                        updateHistoryUI();

                        // 重新连接WebSocket
                        connectWebSocket();

                        console.log('新对话已创建，会话ID:', sessionId);
                    } catch (error) {
                        console.error('创建新对话失败:', error);
                        showError('创建新对话失败，请刷新页面重试');
                    }
                });
            }

            // 侧边栏按钮事件
            if (sidebarOpen) {
                sidebarOpen.addEventListener('click', function () {
                    if (sidebar) sidebar.classList.remove('collapsed');
                });
            }

            if (sidebarClose) {
                sidebarClose.addEventListener('click', function () {
                    if (sidebar) sidebar.classList.add('collapsed');
                });
            }

            // 刷新文件列表按钮点击事件
            if (refreshFilesButton) {
                refreshFilesButton.addEventListener('click', function () {
                    const refreshIcon = refreshFilesButton.querySelector('i');
                    if (refreshIcon) refreshIcon.classList.add('rotating');

                    // 获取文件列表
                    fetchWorkspaceFiles().finally(() => {
                        // 无论成功失败，都停止旋转图标
                        setTimeout(() => {
                            if (refreshIcon) refreshIcon.classList.remove('rotating');
                        }, 500);
                    });
                });
            }

            // 输入框事件
            if (chatInput) {
                chatInput.addEventListener('input', adjustTextareaHeight);
                chatInput.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        if (chatForm) chatForm.dispatchEvent(new Event('submit'));
                    }
                });
            }

            // 滚动事件
            if (chatMessages) {
                chatMessages.addEventListener('scroll', toggleScrollBottomBtn);
            }

            if (scrollBottomBtn) {
                scrollBottomBtn.addEventListener('click', () => scrollToBottom());
            }

            // 适应移动设备
            if (isMobileDevice()) {
                document.body.classList.add('mobile-device');
            }

            // 从文件目录获取文件列表
            await fetchWorkspaceFiles();

            // 初始化历史记录UI
            updateHistoryUI();

            // 调整文本区域高度
            adjustTextareaHeight();

            // 连接WebSocket
            connectWebSocket();

            console.log('应用初始化完成');
        } catch (error) {
            console.error('初始化失败:', error);
            showError('初始化应用失败，请刷新页面重试');
        }
    }

    // 监听窗口调整大小
    window.addEventListener('resize', function () {
        // 在移动设备上自动折叠侧边栏
        if (isMobileDevice()) {
            sidebar.classList.add('collapsed');
        }
    });

    // 监听窗口关闭事件，清理WebSocket连接
    window.addEventListener('beforeunload', function () {
        closeWebSocket();
    });

    // 网络状态监听
    window.addEventListener('online', function () {
        // 如果网络恢复，重新连接
        if (socket && socket.readyState !== WebSocket.OPEN) {
            console.log('网络已恢复，重新连接...');
            connectWebSocket();
        }
    });

    window.addEventListener('offline', function () {
        // 如果网络断开，更新状态
        updateConnectionStatus('disconnected');
        showError('网络连接已断开，请检查您的网络连接');
    });

    // 保存当前对话历史到本地存储
    function saveCurrentChatHistory() {
        if (sessionId && currentChatMessages.length > 0) {
            const sessionHistoryKey = `chat_history_${sessionId}`;
            localStorage.setItem(sessionHistoryKey, JSON.stringify(currentChatMessages));
        }
    }
})();
