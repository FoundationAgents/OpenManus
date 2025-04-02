// DOM元素
const chatInput = document.getElementById('chat-input');
const chatForm = document.getElementById('chat-form');
const chatMessages = document.getElementById('chat-messages');
const sendButton = document.getElementById('send-button');
const quickActionButtons = document.querySelectorAll('.quick-action-button');
const newChatButton = document.getElementById('new-chat-button');
const historyList = document.getElementById('history-list');
const noHistoryMessage = document.getElementById('no-history-message');
const clearHistoryButton = document.getElementById('clear-history-button');
const refreshFilesButton = document.getElementById('refresh-files-button');
const filesList = document.getElementById('files-list');
const noFilesMessage = document.getElementById('no-files-message');
const openFolderButton = document.getElementById('open-folder-button');

// 设置
let sessionId = null;
let websocket = null;
let isProcessing = false;
let messageHistory = [];
let currentThoughtId = null;
let lastLogId = 0;
let taskHistory = []; // 存储任务历史记录

// 初始化WebSocket连接
async function initWebSocket() {
  if (websocket) {
    try {
      // 确保旧的连接彻底关闭
      if (websocket.readyState === WebSocket.OPEN || websocket.readyState === WebSocket.CONNECTING) {
        console.log('关闭旧的WebSocket连接');
        websocket.onclose = null; // 移除旧的onclose处理器以避免触发重连
        websocket.close();
      }
    } catch (e) {
      console.error('关闭旧WebSocket连接时出错:', e);
    }
    // 等待一小段时间确保连接彻底关闭
    await new Promise(resolve => setTimeout(resolve, 500));
    websocket = null;
  }

  // 如果没有会话ID，创建一个新的
  if (!sessionId) {
    try {
      const response = await fetch('/new-session');
      const data = await response.json();
      sessionId = data.session_id;
      console.log('创建了新的会话ID:', sessionId);

      // 添加系统消息
      addSystemMessage('新会话已创建');
    } catch (error) {
      console.error('创建会话ID失败:', error);
      addSystemMessage('创建会话失败，请刷新页面重试');
      return;
    }
  }

  // 连接WebSocket
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}`;

  try {
    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('WebSocket连接已建立');
      addSystemMessage('已连接到OpenManus');

      // 确保在连接建立后启用所有控件
      enableUserControls();
    };

    websocket.onclose = (event) => {
      console.log('WebSocket连接已关闭, 代码:', event.code, '原因:', event.reason);
      // 只有在非手动关闭的情况下才尝试重新连接
      if (!event.wasClean) {
        addSystemMessage('连接已断开，正在尝试重新连接...');

        // 禁用控件直到重新连接
        disableUserControls('连接已断开');

        // 尝试重新连接
        setTimeout(() => {
          initWebSocket();
        }, 3000);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket错误:', error);
      addSystemMessage('连接错误，正在尝试重新连接...');

      // 禁用控件直到重新连接
      disableUserControls('连接错误');
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (e) {
        console.error('解析消息时出错:', e);
      }
    };
  } catch (error) {
    console.error('创建WebSocket连接时出错:', error);
    addSystemMessage('无法建立连接，请刷新页面重试');
    disableUserControls('连接失败');
  }
}

// 处理WebSocket消息
function handleWebSocketMessage(data) {
  console.log('收到消息:', data);

  switch (data.status) {
    case 'processing':
      isProcessing = true;
      addLoadingIndicator();
      disableUserControls('正在处理中');
      break;

    case 'complete':
      isProcessing = false;
      removeLoadingIndicator();
      // 在完成时标记最后一个思考消息为完成状态
      markThinkingAsComplete();
      addAssistantMessage(data.result);

      // 完成任务，保存到历史
      const lastMessage = messageHistory.find(msg => msg.role === 'user');
      if (lastMessage) {
        // 将任务添加到历史记录并保存
        addTaskToHistory(lastMessage.content, data.result);
      }

      // 重新启用控件
      enableUserControls();
      break;

    case 'log':
      // 显示所有日志信息作为独立气泡
      addSingleLogMessage(data.message);
      break;

    case 'thinking':
      // 为每条思考创建独立的消息气泡
      addNewThinkingMessage(data.message, data.id);
      break;

    case 'error':
      isProcessing = false;
      removeLoadingIndicator();
      addErrorMessage(data.message);
      // 重新启用控件
      enableUserControls();
      break;

    default:
      console.warn('未知消息类型:', data);
  }
}

// 启用所有用户控件
function enableUserControls() {
  // 启用聊天输入框
  chatInput.disabled = false;
  chatInput.placeholder = '输入您的指令...';

  // 启用发送按钮
  sendButton.disabled = false;

  // 启用新对话按钮
  if (newChatButton) {
    newChatButton.disabled = false;
    newChatButton.classList.remove('disabled-button');
    newChatButton.title = '开始新对话';
  }

  // 启用快速操作按钮
  quickActionButtons.forEach(button => {
    button.disabled = false;
    button.classList.remove('disabled-button');
  });
}

// 禁用所有用户控件
function disableUserControls(reason) {
  // 禁用聊天输入框
  chatInput.disabled = true;
  chatInput.placeholder = reason || '请等待当前任务完成...';

  // 禁用发送按钮
  sendButton.disabled = true;

  // 禁用新对话按钮
  if (newChatButton) {
    newChatButton.disabled = true;
    newChatButton.classList.add('disabled-button');
    newChatButton.title = '请等待当前任务完成后再开始新对话';
  }

  // 禁用快速操作按钮
  quickActionButtons.forEach(button => {
    button.disabled = true;
    button.classList.add('disabled-button');
  });
}

// 发送消息到服务器
function sendMessage(message) {
  if (!websocket || websocket.readyState !== WebSocket.OPEN) {
    addSystemMessage('连接未建立，正在尝试重新连接...');
    initWebSocket();
    return;
  }

  if (isProcessing) {
    addSystemMessage('正在处理上一个请求，请稍候...');
    return;
  }

  try {
    // 重置当前思考ID
    currentThoughtId = null;
    lastLogId = 0;

    // 添加用户消息到聊天界面
    addUserMessage(message);

    // 发送消息到服务器
    websocket.send(JSON.stringify({
      prompt: message
    }));

    // 清空输入框
    chatInput.value = '';

    // 调整输入框高度
    adjustTextareaHeight();

    // 禁用控件直到处理完成
    disableUserControls('正在处理中');
  } catch (e) {
    console.error('发送消息时出错:', e);
    addSystemMessage('发送消息失败，请刷新页面重试');
  }
}

// 添加用户消息
function addUserMessage(message) {
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message user-message';

  const messageContent = document.createElement('div');
  messageContent.className = 'message-content';
  messageContent.textContent = message;

  messageDiv.appendChild(messageContent);
  chatMessages.appendChild(messageDiv);

  // 添加时间
  const timeSpan = document.createElement('div');
  timeSpan.className = 'message-time';
  timeSpan.textContent = getCurrentTime();
  messageDiv.appendChild(timeSpan);

  // 保存到历史
  messageHistory.push({
    role: 'user',
    content: message,
    timestamp: new Date()
  });

  // 滚动到底部
  scrollToBottom();
}

// 添加助手消息
function addAssistantMessage(message) {
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message assistant-message';

  const messageContent = document.createElement('div');
  messageContent.className = 'message-content markdown-content';

  // 处理消息中的代码块
  const formattedMessage = formatMessage(message);
  messageContent.innerHTML = formattedMessage;

  messageDiv.appendChild(messageContent);
  chatMessages.appendChild(messageDiv);

  // 添加时间
  const timeSpan = document.createElement('div');
  timeSpan.className = 'message-time';
  timeSpan.textContent = getCurrentTime();
  messageDiv.appendChild(timeSpan);

  // 保存到历史
  messageHistory.push({
    role: 'assistant',
    content: message,
    timestamp: new Date()
  });

  // 滚动到底部
  scrollToBottom();

  // 为代码块添加复制按钮
  addCopyButtonsToCodeBlocks();
}

// 添加系统消息
function addSystemMessage(message) {
  const messageDiv = document.createElement('div');
  messageDiv.className = 'system-message';

  const messageSpan = document.createElement('span');
  messageSpan.textContent = message;

  messageDiv.appendChild(messageSpan);
  chatMessages.appendChild(messageDiv);

  // 滚动到底部
  scrollToBottom();
}

// 添加独立的日志消息气泡
function addSingleLogMessage(message) {
  lastLogId++;
  const logId = lastLogId;

  // 创建一个新的日志气泡
  const logDiv = document.createElement('div');
  logDiv.className = 'message log-message';
  logDiv.id = `log-message-${logId}`;

  const messageContent = document.createElement('div');
  messageContent.className = 'message-content';

  const logHeader = document.createElement('div');
  logHeader.className = 'log-header';

  // 添加日志标题和切换按钮
  const titleSpan = document.createElement('span');

  // 检查是否包含执行步骤信息
  const stepPattern = /Executing step (\d+)\/(\d+)/;
  const match = message.match(stepPattern);

  if (match) {
    // 如果包含步骤信息，在标题中显示步骤
    const stepCurrent = match[1];
    const stepTotal = match[2];
    titleSpan.innerHTML = `<span class="log-icon step-icon">🔍</span> 执行步骤 ${stepCurrent}/${stepTotal}:`;
  } else if (message.includes("Token usage:")) {
    // Token使用信息
    titleSpan.innerHTML = '<span class="log-icon token-icon">📊</span> Token使用:';
  } else if (message.includes("Activating tool:")) {
    // 工具激活信息
    titleSpan.innerHTML = '<span class="log-icon tool-icon">🔧</span> 激活工具:';
  } else {
    // 通用系统日志
    titleSpan.innerHTML = '<span class="log-icon">🔍</span> 系统日志:';
  }

  logHeader.appendChild(titleSpan);

  const toggleButton = document.createElement('button');
  toggleButton.className = 'log-toggle';
  toggleButton.textContent = '隐藏';
  toggleButton.onclick = function () {
    const logBody = this.parentNode.parentNode.querySelector('.log-body');
    if (logBody) {
      const isHidden = logBody.style.display === 'none';
      logBody.style.display = isHidden ? 'block' : 'none';
      this.textContent = isHidden ? '隐藏' : '显示';
    }
  };
  logHeader.appendChild(toggleButton);

  messageContent.appendChild(logHeader);

  const logBody = document.createElement('div');
  logBody.className = 'log-body';

  // 处理多行日志
  const logLines = message.split('\n');

  logLines.forEach((line, index) => {
    if (index > 0) {
      // 在日志行之间添加分隔
      const separator = document.createElement('div');
      separator.className = 'log-separator';
      logBody.appendChild(separator);
    }

    // 添加日志行
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    logEntry.textContent = line;
    logBody.appendChild(logEntry);
  });

  messageContent.appendChild(logBody);
  logDiv.appendChild(messageContent);

  // 如果有正在加载的指示器，插入到它前面
  const loadingIndicator = document.getElementById('loading-indicator');
  if (loadingIndicator) {
    chatMessages.insertBefore(logDiv, loadingIndicator);
  } else {
    chatMessages.appendChild(logDiv);
  }

  // 添加时间
  const timeSpan = document.createElement('div');
  timeSpan.className = 'message-time';
  timeSpan.textContent = getCurrentTime();
  logDiv.appendChild(timeSpan);

  // 滚动到底部
  scrollToBottom();

  return logId;
}

// 添加错误消息
function addErrorMessage(message) {
  const errorDiv = document.createElement('div');
  errorDiv.className = 'error-message';
  errorDiv.textContent = message;

  chatMessages.appendChild(errorDiv);

  // 滚动到底部
  scrollToBottom();
}

// 添加加载指示器
function addLoadingIndicator() {
  // 移除现有的加载指示器
  removeLoadingIndicator();

  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'loading';
  loadingDiv.id = 'loading-indicator';

  const loadingMessage = document.createElement('div');
  loadingMessage.className = 'loading-message';
  loadingMessage.textContent = '思考中';
  loadingDiv.appendChild(loadingMessage);

  const loadingDots = document.createElement('div');
  loadingDots.className = 'loading-dots';

  for (let i = 0; i < 3; i++) {
    const dot = document.createElement('span');
    loadingDots.appendChild(dot);
  }

  loadingDiv.appendChild(loadingDots);
  chatMessages.appendChild(loadingDiv);

  // 滚动到底部
  scrollToBottom();
}

// 更新加载指示器
function updateLoadingIndicator(message) {
  const loadingIndicator = document.getElementById('loading-indicator');
  if (loadingIndicator) {
    const loadingMessage = loadingIndicator.querySelector('.loading-message');
    if (loadingMessage) {
      loadingMessage.textContent = message;
    }

    // 滚动到底部
    scrollToBottom();
  }
}

// 移除加载指示器
function removeLoadingIndicator() {
  const loadingIndicator = document.getElementById('loading-indicator');
  if (loadingIndicator) {
    loadingIndicator.remove();
  }
}

// 获取当前时间
function getCurrentTime() {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  const seconds = now.getSeconds().toString().padStart(2, '0');
  return `${hours}:${minutes}:${seconds}`;
}

// 滚动到底部
function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 格式化消息（处理代码块等）
function formatMessage(message) {
  // 替换代码块
  let formattedMessage = message.replace(/```([\w]*)\n([\s\S]*?)```/g, function (match, language, code) {
    const lang = language || 'text';
    return `<div class="code-block">
              <span class="code-language">${lang}</span>
              <pre><code class="${lang}">${escapeHtml(code)}</code></pre>
            </div>`;
  });

  // 替换换行符为<br>
  formattedMessage = formattedMessage.replace(/\n/g, '<br>');

  return formattedMessage;
}

// 为代码块添加复制按钮
function addCopyButtonsToCodeBlocks() {
  const codeBlocks = document.querySelectorAll('.code-block');

  codeBlocks.forEach(block => {
    // 避免重复添加按钮
    if (block.querySelector('.copy-button')) {
      return;
    }

    const copyButton = document.createElement('button');
    copyButton.className = 'copy-button';
    copyButton.textContent = '复制';

    copyButton.addEventListener('click', () => {
      const code = block.querySelector('code').textContent;
      navigator.clipboard.writeText(code)
        .then(() => {
          copyButton.textContent = '已复制!';
          setTimeout(() => {
            copyButton.textContent = '复制';
          }, 2000);
        })
        .catch(err => {
          console.error('复制失败:', err);
          copyButton.textContent = '复制失败';
          setTimeout(() => {
            copyButton.textContent = '复制';
          }, 2000);
        });
    });

    block.appendChild(copyButton);
  });
}

// HTML转义
function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// 调整文本输入框高度
function adjustTextareaHeight() {
  chatInput.style.height = 'auto';
  chatInput.style.height = (chatInput.scrollHeight) + 'px';
}

// 创建新的聊天会话
async function createNewChat() {
  // 停止当前处理
  isProcessing = false;

  try {
    // 确保旧的连接彻底关闭
    if (websocket) {
      console.log('关闭当前WebSocket连接');

      // 确保优雅关闭
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.onclose = null; // 移除旧的onclose处理器以避免触发重连
        websocket.close(1000, "用户创建了新对话");
      }

      // 等待连接关闭
      await new Promise(resolve => setTimeout(resolve, 500));
      websocket = null;
    }

    // 清空会话ID，强制创建新的会话
    sessionId = null;

    // 清空消息历史
    messageHistory = [];

    // 清空聊天界面
    chatMessages.innerHTML = '';

    // 移除加载指示器
    removeLoadingIndicator();

    // 添加系统消息
    addSystemMessage('正在创建新对话...');

    // 重新初始化WebSocket连接
    await initWebSocket();
  } catch (e) {
    console.error('创建新对话时出错:', e);
    addSystemMessage('创建新对话时出错，请刷新页面重试');
  }
}

// 添加快速操作提示
function addQuickPrompt(promptText) {
  chatInput.value = promptText;
  adjustTextareaHeight();
  chatInput.focus();
}

// 事件监听器
document.addEventListener('DOMContentLoaded', () => {
  // 初始化WebSocket连接
  initWebSocket();

  // 加载历史记录
  loadTaskHistory();

  // 加载文件列表
  loadWorkspaceFiles();

  // 表单提交
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();

    // 如果正在处理，不允许提交
    if (isProcessing) {
      addSystemMessage('请等待当前任务完成');
      return;
    }

    const message = chatInput.value.trim();
    if (message) {
      sendMessage(message);
    }
  });

  // 按键监听
  chatInput.addEventListener('keydown', (e) => {
    // Ctrl+Enter 发送消息
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault();

      // 如果正在处理，不允许发送
      if (isProcessing) {
        addSystemMessage('请等待当前任务完成');
        return;
      }

      const message = chatInput.value.trim();
      if (message) {
        sendMessage(message);
      }
    }

    // 自动调整高度
    setTimeout(adjustTextareaHeight, 0);
  });

  // 快速操作按钮
  quickActionButtons.forEach(button => {
    button.addEventListener('click', () => {
      // 如果正在处理，不允许使用快速操作
      if (isProcessing) {
        addSystemMessage('请等待当前任务完成');
        return;
      }

      const promptText = button.dataset.prompt;
      addQuickPrompt(promptText);
    });
  });

  // 新聊天按钮
  if (newChatButton) {
    newChatButton.addEventListener('click', () => {
      // 判断按钮是否被禁用
      if (newChatButton.classList.contains('disabled-button') || isProcessing) {
        addSystemMessage('请等待当前任务完成后再开始新对话');
        return;
      }
      createNewChat();
    });
  }

  // 清空历史按钮
  if (clearHistoryButton) {
    clearHistoryButton.addEventListener('click', clearTaskHistory);
  }

  // 刷新文件列表按钮
  if (refreshFilesButton) {
    refreshFilesButton.addEventListener('click', loadWorkspaceFiles);
  }

  // 打开文件夹按钮
  if (openFolderButton) {
    openFolderButton.addEventListener('click', openWorkspaceFolder);
  }
});

// 移动端菜单切换
function toggleSidebar() {
  const sidebar = document.querySelector('.info-sidebar');
  if (sidebar) {
    sidebar.classList.toggle('mobile-visible');
  }
}

// 标记思考消息为完成状态
function markThinkingAsComplete() {
  // 查找所有思考消息并标记为完成
  const thinkingMessages = document.querySelectorAll('.thinking-message:not(.thinking-complete)');
  thinkingMessages.forEach(message => {
    message.classList.add('thinking-complete');
  });
}

// 添加新的思考消息（每条思考都是独立的气泡）
function addNewThinkingMessage(message, thoughtId) {
  // 创建一个新的思考气泡
  const thinkingDiv = document.createElement('div');
  thinkingDiv.className = 'message assistant-message thinking-message';
  thinkingDiv.id = `thinking-message-${thoughtId}`;

  const messageContent = document.createElement('div');
  messageContent.className = 'message-content';

  const thinkingHeader = document.createElement('div');
  thinkingHeader.className = 'thinking-header';

  // 添加思考标题和切换按钮
  const titleSpan = document.createElement('span');
  titleSpan.innerHTML = '<span class="thinking-icon">✨</span> 思考过程:';
  thinkingHeader.appendChild(titleSpan);

  const toggleButton = document.createElement('button');
  toggleButton.className = 'thinking-toggle';
  toggleButton.textContent = '隐藏';
  toggleButton.onclick = function () {
    const thinkingBody = this.parentNode.parentNode.querySelector('.thinking-body');
    if (thinkingBody) {
      const isHidden = thinkingBody.style.display === 'none';
      thinkingBody.style.display = isHidden ? 'block' : 'none';
      this.textContent = isHidden ? '隐藏' : '显示';
    }
  };
  thinkingHeader.appendChild(toggleButton);

  messageContent.appendChild(thinkingHeader);

  const thinkingBody = document.createElement('div');
  thinkingBody.className = 'thinking-body';

  // 处理消息中的代码块
  const formattedMessage = formatMessage(message);
  thinkingBody.innerHTML = formattedMessage;

  messageContent.appendChild(thinkingBody);
  thinkingDiv.appendChild(messageContent);

  // 如果有正在加载的指示器，插入到它前面
  const loadingIndicator = document.getElementById('loading-indicator');
  if (loadingIndicator) {
    chatMessages.insertBefore(thinkingDiv, loadingIndicator);
  } else {
    chatMessages.appendChild(thinkingDiv);
  }

  // 添加时间
  const timeSpan = document.createElement('div');
  timeSpan.className = 'message-time';
  timeSpan.textContent = getCurrentTime();
  thinkingDiv.appendChild(timeSpan);

  // 为代码块添加复制按钮
  addCopyButtonsToCodeBlocks();

  // 滚动到底部
  scrollToBottom();
}

// 加载任务历史
function loadTaskHistory() {
  // 从localStorage加载历史记录
  const savedHistory = localStorage.getItem('openmanus_task_history');
  if (savedHistory) {
    try {
      taskHistory = JSON.parse(savedHistory);
      updateHistoryDisplay();
      console.log('从本地存储加载了任务历史:', taskHistory.length, '条记录');
    } catch (e) {
      console.error('加载历史记录失败:', e);
      taskHistory = [];
    }
  } else {
    console.log('没有找到保存的历史记录');
  }
}

// 保存任务历史到本地存储
function saveTaskHistory() {
  try {
    // 限制历史记录数量，防止localStorage溢出
    if (taskHistory.length > 50) {
      taskHistory = taskHistory.slice(-50); // 只保留最近50条
    }

    localStorage.setItem('openmanus_task_history', JSON.stringify(taskHistory));
    console.log('已保存任务历史到本地存储');
  } catch (e) {
    console.error('保存历史记录失败:', e);
  }
}

// 更新历史显示
function updateHistoryDisplay() {
  if (!historyList || !noHistoryMessage) return;

  // 清空当前历史列表
  historyList.innerHTML = '';

  if (taskHistory.length === 0) {
    // 显示无历史记录消息
    noHistoryMessage.style.display = 'block';
    return;
  }

  // 隐藏无历史记录消息
  noHistoryMessage.style.display = 'none';

  // 显示最近的10条历史记录
  const recentHistory = [...taskHistory].reverse().slice(0, 10);

  recentHistory.forEach((task, index) => {
    const historyItem = document.createElement('div');
    historyItem.className = 'history-item';
    historyItem.dataset.index = taskHistory.length - 1 - index; // 保存原始索引

    // 提示文本，限制长度
    const promptPreview = task.prompt.length > 30
      ? task.prompt.substring(0, 30) + '...'
      : task.prompt;

    // 格式化时间
    const timestamp = task.timestamp ? new Date(task.timestamp) : new Date();
    const formattedTime = formatHistoryDate(timestamp);

    historyItem.innerHTML = `
      <div class="history-prompt">${promptPreview}</div>
      <div class="history-time">${formattedTime}</div>
    `;

    // 点击历史记录项目，显示历史对话
    historyItem.addEventListener('click', () => {
      const index = parseInt(historyItem.dataset.index);
      if (isProcessing) {
        addSystemMessage('请等待当前任务完成后再查看历史对话');
        return;
      }
      showHistoryDialog(index);
    });

    historyList.appendChild(historyItem);
  });
}

// 格式化历史记录日期
function formatHistoryDate(date) {
  if (!date || !(date instanceof Date)) return '未知时间';

  const now = new Date();
  const diff = now - date;
  const day = 24 * 60 * 60 * 1000;

  // 如果是今天
  if (diff < day && now.getDate() === date.getDate()) {
    return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
  }

  // 如果是昨天
  if (diff < 2 * day && now.getDate() - date.getDate() === 1) {
    return `昨天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
  }

  // 其他时间
  return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
}

// 显示历史对话详情对话框
function showHistoryDialog(index) {
  const task = taskHistory[index];
  if (!task) return;

  // 如果对话框已存在，移除它
  const existingDialog = document.getElementById('history-dialog');
  if (existingDialog) {
    existingDialog.remove();
  }

  // 创建对话框
  const dialog = document.createElement('div');
  dialog.id = 'history-dialog';
  dialog.className = 'history-dialog';

  // 对话框内容
  dialog.innerHTML = `
    <div class="dialog-content">
      <div class="dialog-header">
        <h3>历史对话详情</h3>
        <button class="dialog-close-button">×</button>
      </div>
      <div class="dialog-body">
        <div class="dialog-section">
          <h4>问题:</h4>
          <div class="dialog-prompt">${escapeHtml(task.prompt)}</div>
        </div>
        <div class="dialog-section">
          <h4>回复:</h4>
          <div class="dialog-response markdown-content">${formatMessage(task.response)}</div>
        </div>
        <div class="dialog-time">
          ${formatHistoryDate(new Date(task.timestamp))}
        </div>
      </div>
      <div class="dialog-footer">
        <button class="dialog-action-button" id="reuse-prompt-button">重新使用这个问题</button>
        <button class="dialog-action-button" id="delete-history-button">删除此记录</button>
      </div>
    </div>
  `;

  // 添加到页面
  document.body.appendChild(dialog);

  // 添加事件
  const closeButton = dialog.querySelector('.dialog-close-button');
  if (closeButton) {
    closeButton.addEventListener('click', () => {
      dialog.remove();
    });
  }

  // 点击对话框外部关闭
  dialog.addEventListener('click', (e) => {
    if (e.target === dialog) {
      dialog.remove();
    }
  });

  // 重新使用问题
  const reuseButton = dialog.querySelector('#reuse-prompt-button');
  if (reuseButton) {
    reuseButton.addEventListener('click', () => {
      addQuickPrompt(task.prompt);
      dialog.remove();
    });
  }

  // 删除历史
  const deleteButton = dialog.querySelector('#delete-history-button');
  if (deleteButton) {
    deleteButton.addEventListener('click', () => {
      taskHistory.splice(index, 1);
      saveTaskHistory();
      updateHistoryDisplay();
      dialog.remove();
      addSystemMessage('已删除该历史记录');
    });
  }

  // 为对话框中的代码块添加复制按钮
  const codeBlocks = dialog.querySelectorAll('.code-block');
  if (codeBlocks.length > 0) {
    addCopyButtonsToCodeBlocks();
  }
}

// 清空任务历史
function clearTaskHistory() {
  if (taskHistory.length === 0) {
    addSystemMessage('历史记录已经为空');
    return;
  }

  // 显示确认对话框
  if (confirm('确定要清空所有历史记录吗？此操作无法撤销。')) {
    taskHistory = [];
    saveTaskHistory();
    updateHistoryDisplay();
    addSystemMessage('已清空所有历史记录');
  }
}

// 收到完成任务的消息时更新历史记录
function addTaskToHistory(prompt, response) {
  const task = {
    prompt,
    response,
    timestamp: new Date(),
    sessionId
  };

  taskHistory.push(task);
  saveTaskHistory();
  updateHistoryDisplay();
}

// 加载workspace文件夹中的文件列表
async function loadWorkspaceFiles() {
  try {
    // 添加旋转效果到刷新按钮
    if (refreshFilesButton) {
      refreshFilesButton.classList.add('rotating');
    }

    const response = await fetch('/workspace-files');
    const data = await response.json();

    // 移除旋转效果
    if (refreshFilesButton) {
      refreshFilesButton.classList.remove('rotating');
    }

    updateFilesList(data.files);
  } catch (error) {
    console.error('加载文件列表失败:', error);

    // 移除旋转效果
    if (refreshFilesButton) {
      refreshFilesButton.classList.remove('rotating');
    }

    // 显示错误信息
    if (filesList) {
      filesList.innerHTML = '<div class="file-error">加载文件列表失败</div>';
    }

    // 显示无文件消息
    if (noFilesMessage) {
      noFilesMessage.style.display = 'block';
    }
  }
}

// 更新文件列表显示
function updateFilesList(files) {
  if (!filesList || !noFilesMessage) return;

  // 清空当前文件列表
  filesList.innerHTML = '';

  if (!files || files.length === 0) {
    // 显示无文件消息
    noFilesMessage.style.display = 'block';
    return;
  }

  // 隐藏无文件消息
  noFilesMessage.style.display = 'none';

  // 按文件名排序
  const sortedFiles = [...files].sort((a, b) => a.name.localeCompare(b.name));

  // 显示文件列表
  sortedFiles.forEach(file => {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    fileItem.dataset.path = file.path;

    // 根据文件扩展名选择图标
    const extension = file.name.split('.').pop().toLowerCase();
    let iconClass = 'fas fa-file';

    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg'].includes(extension)) {
      iconClass = 'fas fa-file-image';
    } else if (['txt', 'md', 'log'].includes(extension)) {
      iconClass = 'fas fa-file-alt';
    } else if (['pdf'].includes(extension)) {
      iconClass = 'fas fa-file-pdf';
    } else if (['doc', 'docx'].includes(extension)) {
      iconClass = 'fas fa-file-word';
    } else if (['xls', 'xlsx'].includes(extension)) {
      iconClass = 'fas fa-file-excel';
    } else if (['ppt', 'pptx'].includes(extension)) {
      iconClass = 'fas fa-file-powerpoint';
    } else if (['js', 'py', 'java', 'c', 'cpp', 'html', 'css'].includes(extension)) {
      iconClass = 'fas fa-file-code';
    }

    // 格式化文件大小
    const fileSize = formatFileSize(file.size);

    fileItem.innerHTML = `
      <div class="file-icon"><i class="${iconClass}"></i></div>
      <div class="file-name">${file.name}</div>
      <div class="file-size">${fileSize}</div>
    `;

    // 点击文件项目，显示文件内容
    fileItem.addEventListener('click', () => {
      openWorkspaceFile(file.path);
    });

    filesList.appendChild(fileItem);
  });
}

// 格式化文件大小
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 打开workspace文件
async function openWorkspaceFile(filePath) {
  try {
    // 获取文件内容
    const response = await fetch(`/workspace-file/${encodeURIComponent(filePath)}`);
    const data = await response.json();

    if (data.status === 'error') {
      console.error('获取文件内容失败:', data.message);
      addSystemMessage(`获取文件内容失败: ${data.message}`);
      return;
    }

    // 显示文件内容对话框
    showFileDialog(data.name, data.content);
  } catch (error) {
    console.error('打开文件失败:', error);
    addSystemMessage('打开文件失败，请稍后重试');
  }
}

// 显示文件内容对话框
function showFileDialog(fileName, fileContent) {
  // 如果对话框已存在，移除它
  const existingDialog = document.getElementById('file-dialog');
  if (existingDialog) {
    existingDialog.remove();
  }

  // 创建对话框
  const dialog = document.createElement('div');
  dialog.id = 'file-dialog';
  dialog.className = 'file-dialog';

  // 检测文件类型
  const extension = fileName.split('.').pop().toLowerCase();
  let contentDisplay = fileContent;

  // 检查是否为可能的图片类型
  if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg'].includes(extension)) {
    contentDisplay = `<img src="/workspace/${fileName}" alt="${fileName}" style="max-width: 100%; max-height: 70vh;">`;
  } else {
    // 对纯文本文件，保留空格和换行，但进行HTML转义
    contentDisplay = `<pre class="file-content">${escapeHtml(fileContent)}</pre>`;
  }

  // 对话框内容
  dialog.innerHTML = `
    <div class="file-dialog-content">
      <div class="file-dialog-header">
        <div class="file-dialog-title">${fileName}</div>
        <button class="file-dialog-close">×</button>
      </div>
      <div class="file-dialog-body">
        ${contentDisplay}
      </div>
    </div>
  `;

  // 添加到页面
  document.body.appendChild(dialog);

  // 添加事件
  const closeButton = dialog.querySelector('.file-dialog-close');
  if (closeButton) {
    closeButton.addEventListener('click', () => {
      dialog.remove();
    });
  }

  // 点击对话框外部关闭
  dialog.addEventListener('click', (e) => {
    if (e.target === dialog) {
      dialog.remove();
    }
  });
}

// 打开workspace文件夹
async function openWorkspaceFolder() {
  try {
    const response = await fetch('/open-workspace-folder');
    const data = await response.json();

    if (data.status === 'error') {
      console.error('打开文件夹失败:', data.message);
      addSystemMessage(`打开文件夹失败: ${data.message}`);
      return;
    }

    // 显示成功消息
    addSystemMessage('已打开workspace文件夹');
  } catch (error) {
    console.error('打开文件夹失败:', error);
    addSystemMessage('打开文件夹失败，请稍后重试');
  }
}

// 添加CSS类: 旋转效果
if (!document.getElementById('rotating-style')) {
  const style = document.createElement('style');
  style.id = 'rotating-style';
  style.textContent = `
    @keyframes rotating {
      from {
        transform: rotate(0deg);
      }
      to {
        transform: rotate(360deg);
      }
    }
    .rotating {
      animation: rotating 1s linear infinite;
    }
  `;
  document.head.appendChild(style);
}
