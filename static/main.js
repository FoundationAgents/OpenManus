// 加载页面控制函数
function initLoadingScreen() {
    const loadingScreen = document.querySelector('.loading-screen');
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.querySelector('.progress-text .digital-glitch');
    const loadingMessage = document.querySelector('.loading-message');
    
    if (!loadingScreen || !progressBar || !progressText) return;
    
    // 检查是否是从站内导航回来的
    const referrer = document.referrer;
    const currentHost = window.location.host;
    
    // 如果是从同一站点的其他页面返回的，不显示加载动画
    if (referrer && referrer.includes(currentHost) && !isPageReload()) {
        loadingScreen.classList.add('hidden');
        loadingScreen.style.display = 'none';
        return;
    }
    
    const messages = [
        "Initializing system components...",
        "Connecting to neural network...",
        "Loading AI modules...",
        "Calibrating response patterns...",
        "Starting quantum processors..."
    ];
    
    let progress = 0;
    const totalDuration = 5000; // 5秒钟完成加载
    const interval = 30; // 每30ms更新一次
    const steps = totalDuration / interval;
    const increment = 100 / steps;
    
    // 随机更新消息
    let messageIndex = 0;
    
    const updateProgress = () => {
        progress += increment;
        
        // 添加一些随机性，模拟真实加载
        const randomFactor = Math.random() * 0.5;
        const adjustedProgress = Math.min(progress + randomFactor, 100);
        
        // 更新进度条宽度
        progressBar.style.width = `${adjustedProgress}%`;
        
        // 更新进度文本
        const displayProgress = Math.floor(adjustedProgress);
        progressText.textContent = `${displayProgress}%`;
        
        // 不同阶段显示不同消息
        if (displayProgress > messageIndex * 25 && messageIndex < messages.length) {
            loadingMessage.textContent = messages[messageIndex];
            messageIndex++;
            
            // 添加闪烁效果
            loadingScreen.style.filter = 'brightness(1.2)';
            setTimeout(() => {
                loadingScreen.style.filter = 'brightness(1)';
            }, 100);
        }
        
        // 模拟网络加载的变化
        if (displayProgress >= 99.5) {
            // 加载完成，隐藏加载屏幕
            setTimeout(() => {
                loadingScreen.classList.add('hidden');
                
                // 完全隐藏后从DOM中移除
                setTimeout(() => {
                    loadingScreen.style.display = 'none';
                }, 500);
            }, 200);
            return;
        }
        
        // 添加随机故障效果
        if (Math.random() < 0.1) {
            createGlitchEffect();
        }
        
        requestAnimationFrame(updateProgress);
    };
    
    // 创建故障效果
    const createGlitchEffect = () => {
        // 屏幕抖动
        loadingScreen.style.transform = `translate(${(Math.random() - 0.5) * 10}px, ${(Math.random() - 0.5) * 5}px)`;
        
        // 随机调整颜色和不透明度
        loadingScreen.style.filter = `hue-rotate(${Math.random() * 30}deg) brightness(${1 + Math.random() * 0.3})`;
        
        // 恢复正常
        setTimeout(() => {
            loadingScreen.style.transform = 'translate(0, 0)';
            loadingScreen.style.filter = 'none';
        }, 100);
    };
    
    // 开始更新进度
    setTimeout(() => {
        updateProgress();
    }, 300);
}

// 动态产生随机粒子
function createRandomParticle() {
    const container = document.querySelector('.particle-container');

    if (!container) return;

    setInterval(() => {
        const particle = document.createElement('div');
        particle.className = 'particle';

        // 随机位置
        particle.style.left = `${Math.random() * 100}%`;
        particle.style.top = '100%';

        // 随机大小
        const size = Math.random() * 2 + 1;
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;

        // 获取CSS变量
        const styles = getComputedStyle(document.documentElement);
        const colorOptions = [
            styles.getPropertyValue('--accent-green').trim(),
            styles.getPropertyValue('--accent-color-5').trim(),
            styles.getPropertyValue('--accent-blue').trim(),
            styles.getPropertyValue('--accent-color-1').trim()
        ];

        // 随机颜色
        const randomColor = colorOptions[Math.floor(Math.random() * colorOptions.length)];
        particle.style.backgroundColor = randomColor;
        particle.style.boxShadow = `0 0 5px ${randomColor}`;

        // 随机透明度
        particle.style.opacity = (Math.random() * 0.5 + 0.3).toString();

        // 添加到容器
        container.appendChild(particle);

        // 设置动画结束后移除元素
        setTimeout(() => {
            particle.remove();
        }, 5000);
    }, 600); // 每600ms创建一个新粒子
}

// 添加主题选项动画效果
function animateThemeOptions() {
    const themeOptions = document.querySelectorAll('.theme-option');
    themeOptions.forEach((option, index) => {
        // 直接显示元素，不使用动画过渡
        option.style.opacity = '1';
    });
}

// 页面加载完成后初始化效果
document.addEventListener('DOMContentLoaded', function() {
    // 初始化加载页面
    initLoadingScreen();
    
    // 初始化粒子效果
    createRandomParticle();

    // 初始化主题选项动画
    animateThemeOptions();
});

// 仅用于开发环境 - 清除会话状态
function resetVisitState() {
    // 清除会话状态相关变量
    sessionStorage.clear();
    console.log('Visit state has been reset. This will simulate a first-time visit on the next navigation.');
}

// 注释掉下面这行代码来禁用自动重置（仅开发环境使用）
// resetVisitState();

// 判断页面是否为刷新
function isPageReload() {
    // 如果页面表现性能数据可用，检查导航类型
    if (window.performance && window.performance.navigation) {
        return window.performance.navigation.type === 1; // 1表示页面刷新
    }
    
    // 对较新的浏览器使用Navigation Timing API
    if (window.performance && window.performance.getEntriesByType && window.performance.getEntriesByType('navigation').length) {
        return window.performance.getEntriesByType('navigation')[0].type === 'reload';
    }
    
    // 无法确定时，假设不是刷新
    return false;
}
