// 加载页面控制函数
function initLoadingScreen() {
    const loadingScreen = document.querySelector('.loading-screen');
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.querySelector('.progress-text .digital-glitch');
    const loadingMessage = document.querySelector('.loading-message');
    const loadingText = document.querySelector('.loading-text');

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

    // 设置字符动画效果 - 恢复渐进显示效果
    const titleChars = document.querySelectorAll('.loading-title .char');
    titleChars.forEach((char, index) => {
        // 确保动画重置
        char.style.animation = 'none';
        char.offsetHeight; // 触发重排
        // 不指定动画参数，使用CSS中的定义
        char.style.animation = '';
    });

    // 动态加载点动画
    const loadingDots = document.querySelectorAll('.loading-dots .dot');
    loadingDots.forEach((dot, index) => {
        dot.style.animation = 'none';
        dot.offsetHeight; // 触发重排
        dot.style.animation = `dot-fade 1.4s infinite ${index * 0.2}s`;
    });

    const messages = [
        "Initializing system components...",
        "Connecting to neural network...",
        "Loading AI modules...",
        "Calibrating response patterns...",
        "Starting quantum processors..."
    ];

    let progress = 0;
    const totalDuration = 5000; // 3.5秒钟完成加载
    const interval = 30; // 每50ms更新一次
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

    // 开始更新进度 - 减少延迟，更快开始进度条显示
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
    themeOptions.forEach((option) => {
        // 只控制显示/隐藏，动画交给CSS处理
        option.style.opacity = '1';
    });
}

// 初始化视频播放器交互
function initVideoPlayer() {
    const video = document.getElementById('manus-video');
    const videoWrapper = document.querySelector('.manus-video-wrapper');
    const progressContainer = document.querySelector('.manus-video-wrapper .video-progress-container');
    const progressBar = document.querySelector('.manus-video-wrapper .video-progress-bar');
    const playBtn = document.getElementById('video-play-btn');
    const muteBtn = document.getElementById('video-mute-btn');
    const fullscreenBtn = document.getElementById('video-fullscreen-btn');

    if (!video || !videoWrapper) return;

    // 设置固定播放速率，确保播放速度一致
    video.playbackRate = 1.0;

    // 确保视频缓冲充足
    video.preload = "auto";

    // 处理视频缓冲，确保流畅播放
    let bufferingDetected = false;
    let lastPlayPos = 0;
    let currentPlayPos = 0;
    let checkBufferInterval = null;

    // 检测缓冲状态
    function checkBuffer() {
        currentPlayPos = video.currentTime;

        // 检测是否在缓冲（播放位置没有变化但视频没有暂停）
        const buffering = !video.paused && currentPlayPos === lastPlayPos && !video.ended;

        if (buffering && !bufferingDetected) {
            bufferingDetected = true;
            videoWrapper.classList.add('buffering');
        }

        if (!buffering && bufferingDetected) {
            bufferingDetected = false;
            videoWrapper.classList.remove('buffering');
        }

        lastPlayPos = currentPlayPos;
    }

    // 处理全屏变化事件
    document.addEventListener('fullscreenchange', function() {
        if (!document.fullscreenElement) {
            videoWrapper.classList.remove('fullscreen-active');

            // 退出全屏恢复样式
            videoWrapper.style.borderRadius = '8px';
            videoWrapper.style.boxShadow = '0 0 20px rgba(0, 128, 255, 0.5)';
            videoWrapper.style.margin = '20px auto 30px auto';
            video.style.objectFit = 'contain';
        }
    });

    // 确保视频比例正确
    function updateVideoSize() {
        // 仅在非全屏模式下调整尺寸
        if (document.fullscreenElement) return;

        // 设置视频元素样式
        video.style.width = '100%';
        video.style.height = '100%';
        video.style.objectFit = 'contain';
    }

    // 视频元数据加载后更新尺寸
    video.addEventListener('loadedmetadata', updateVideoSize);

    // 如果视频已经有元数据，立即更新尺寸
    if (video.readyState >= 1) {
        updateVideoSize();
    }

    // 使用requestAnimationFrame优化视频进度条更新
    let animationId = null;
    let lastProgress = 0;

    function updateProgressBar() {
        if (progressBar && !video.paused) {
            // 计算当前实际进度
            const currentProgress = (video.currentTime / video.duration) * 100;

            // 平滑插值，减少顿感
            const smoothProgress = lastProgress + (currentProgress - lastProgress) * 0.5;
            lastProgress = smoothProgress;

            // 使用transform3d强制启用GPU加速
            progressBar.style.width = `${smoothProgress}%`;
        }
        animationId = requestAnimationFrame(updateProgressBar);
    }

    // 开始播放时启动进度条更新
    video.addEventListener('play', function() {
        // 重置上次进度，确保平滑过渡
        lastProgress = (video.currentTime / video.duration) * 100;

        // 启动动画帧更新
        cancelAnimationFrame(animationId);
        animationId = requestAnimationFrame(updateProgressBar);
    });

    // 暂停时停止进度条更新，但更新最终位置
    video.addEventListener('pause', function() {
        cancelAnimationFrame(animationId);
        // 更新到准确位置
        if (progressBar) {
            lastProgress = (video.currentTime / video.duration) * 100;
            progressBar.style.width = `${lastProgress}%`;
        }
    });

    // 视频结束时停止进度条更新，但更新到100%
    video.addEventListener('ended', function() {
        cancelAnimationFrame(animationId);
        // 显示完成状态
        if (progressBar) {
            lastProgress = 100;
            progressBar.style.width = '100%';
        }
    });

    // 时间更新时同步位置（处理拖动视频的情况）
    video.addEventListener('timeupdate', function() {
        if (video.paused && progressBar) {
            lastProgress = (video.currentTime / video.duration) * 100;
            progressBar.style.width = `${lastProgress}%`;
        }
    });

    // 确保在页面不可见时停止更新
    document.addEventListener('visibilitychange', function() {
        if (document.hidden && animationId) {
            cancelAnimationFrame(animationId);
        } else if (!document.hidden && !video.paused) {
            animationId = requestAnimationFrame(updateProgressBar);
        }
    });

    // 尝试自动播放视频
    video.play().catch(e => {
        videoWrapper.classList.add('awaiting-interaction');
    });

    // 视频结束时重新播放
    video.addEventListener('ended', function() {
        video.currentTime = 0;
        video.play().catch(e => {
            playBtn.innerHTML = '<i class="fas fa-play"></i>';
        });
    });

    // 点击视频区域播放/暂停
    videoWrapper.addEventListener('click', function(e) {
        // 避免点击控制按钮时触发
        if (e.target.closest('.video-controls')) return;

        if (video.paused) {
            video.play().then(() => {
                playBtn.innerHTML = '<i class="fas fa-pause"></i>';
                videoWrapper.classList.remove('awaiting-interaction');
            }).catch(e => {
                console.log('播放失败:', e);
            });
        } else {
            video.pause();
            playBtn.innerHTML = '<i class="fas fa-play"></i>';
        }
    });

    // 播放/暂停按钮
    playBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (video.paused) {
            video.play().then(() => {
                playBtn.innerHTML = '<i class="fas fa-pause"></i>';
                videoWrapper.classList.remove('awaiting-interaction');
            }).catch(e => {
                console.log('播放失败:', e);
            });
        } else {
            video.pause();
            playBtn.innerHTML = '<i class="fas fa-play"></i>';
        }
    });

    // 静音按钮
    muteBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        video.muted = !video.muted;
        if (video.muted) {
            muteBtn.innerHTML = '<i class="fas fa-volume-mute"></i>';
        } else {
            muteBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
        }
    });

    // 全屏按钮
    fullscreenBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (!document.fullscreenElement) {
            // 添加全屏标记类
            videoWrapper.classList.add('fullscreen-active');

            // 进入全屏
            if (video.requestFullscreen) {
                video.requestFullscreen();
            } else if (video.webkitRequestFullscreen) {
                video.webkitRequestFullscreen();
            } else if (video.msRequestFullscreen) {
                video.msRequestFullscreen();
            }
        } else {
            // 退出全屏
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            }
        }
    });

    // 键盘快捷键
    document.addEventListener('keydown', function(e) {
        const rect = videoWrapper.getBoundingClientRect();
        const isVisible =
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth);

        if (!isVisible) return;

        switch(e.key) {
            case ' ':  // 空格键播放/暂停
                if (video.paused) {
                    video.play();
                    playBtn.innerHTML = '<i class="fas fa-pause"></i>';
                    videoWrapper.classList.remove('awaiting-interaction');
                } else {
                    video.pause();
                    playBtn.innerHTML = '<i class="fas fa-play"></i>';
                }
                e.preventDefault();
                break;
            case 'f':  // f键全屏
                fullscreenBtn.click();
                e.preventDefault();
                break;
            case 'm':  // m键静音
                video.muted = !video.muted;
                if (video.muted) {
                    muteBtn.innerHTML = '<i class="fas fa-volume-mute"></i>';
                } else {
                    muteBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
                }
                e.preventDefault();
                break;
        }
    });

    // 响应窗口大小变化，更新视频大小
    window.addEventListener('resize', updateVideoSize);

    // 点击进度条跳转视频
    if (progressContainer) {
        progressContainer.addEventListener('click', function(e) {
            const rect = progressContainer.getBoundingClientRect();
            const pos = (e.clientX - rect.left) / rect.width;
            const seekTime = video.duration * pos;

            // 确保时间有效
            if (isFinite(seekTime) && seekTime >= 0 && seekTime <= video.duration) {
                // 设置新时间
                video.currentTime = seekTime;

                // 直接更新进度条位置，无需等待timeupdate
                lastProgress = pos * 100;
                progressBar.style.width = `${lastProgress}%`;

                // 如果视频暂停中，则开始播放
                if (video.paused) {
                    video.play().then(() => {
                        playBtn.innerHTML = '<i class="fas fa-pause"></i>';
                        videoWrapper.classList.remove('awaiting-interaction');
                    }).catch(e => {
                        console.log('播放失败:', e);
                    });
                }
            }
        });
    }
}

// 移除复杂的全屏退出处理函数，简化逻辑
function handleFullscreenExit() {
    // 此函数不再需要复杂逻辑，可以保留为空，以备未来需要扩展
}

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

// Matrix效果
function initMatrixEffect() {
    const canvas = document.getElementById('matrix-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // 设置canvas大小为窗口大小
    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // 获取样式变量
    const computedStyle = getComputedStyle(document.documentElement);
    const primaryColor = computedStyle.getPropertyValue('--primary-color').trim() || '#00ffcc';
    const secondaryColor = computedStyle.getPropertyValue('--secondary-color').trim() || '#0088ff';

    // 矩阵字符
    const chars = "01010101";
    const fontSize = 12;
    const columns = Math.floor(canvas.width / fontSize);

    // 每列的当前位置
    const drops = [];
    for (let i = 0; i < columns; i++) {
        drops[i] = Math.random() * -100;
    }

    // 定义绘制函数
    function draw() {
        // 半透明黑色背景，形成拖尾效果
        ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // 设置文本样式
        ctx.font = `${fontSize}px monospace`;

        // 绘制字符
        for (let i = 0; i < columns; i++) {
            // 随机选择字符
            const char = chars[Math.floor(Math.random() * chars.length)];

            // 根据位置设置渐变颜色
            const y = drops[i] * fontSize;
            const gradient = ctx.createLinearGradient(0, y-fontSize, 0, y);
            gradient.addColorStop(0, primaryColor);
            gradient.addColorStop(1, secondaryColor);

            // 设置填充样式
            ctx.fillStyle = gradient;
            if (Math.random() > 0.99) {
                ctx.fillStyle = '#ffffff';
            }

            // 绘制字符
            ctx.fillText(char, i * fontSize, y);

            // 到底部后重新开始，或者随机重置
            if (y > canvas.height && Math.random() > 0.99) {
                drops[i] = 0;
            }

            // 更新位置
            drops[i]++;
        }

        // 通过requestAnimationFrame实现动画
        requestAnimationFrame(draw);
    }

    // 开始动画
    draw();
}

// 动态波纹效果
function initRippleEffect() {
    const techCircles = document.querySelectorAll('.tech-circle');

    // 如果没有tech-circle元素，不执行
    if (!techCircles.length) return;

    // 动态调整圆环位置
    function updateCirclePositions() {
        techCircles.forEach((circle, index) => {
            // 根据鼠标位置微调圆环
            document.addEventListener('mousemove', (e) => {
                const { clientX, clientY } = e;
                const centerX = window.innerWidth / 2;
                const centerY = window.innerHeight / 2;

                // 计算鼠标与中心点的距离
                const offsetX = (clientX - centerX) / centerX * 10;
                const offsetY = (clientY - centerY) / centerY * 10;

                // 设置位置偏移，每个圆环的偏移量不同
                const factor = 1 - index * 0.2;
                circle.style.transform = `translate(calc(-50% + ${offsetX * factor}px), calc(-50% + ${offsetY * factor}px)) scale(var(--scale))`;
            });
        });
    }

    // 由于性能考虑，只在桌面端启用
    if (window.innerWidth > 1024) {
        updateCirclePositions();
    }
}

// 动态网格效果
function initGridEffect() {
    const gridOverlay = document.querySelector('.grid-overlay');
    if (!gridOverlay) return;

    let isAnimating = false;

    // 添加鼠标移动交互
    document.addEventListener('mousemove', (e) => {
        if (isAnimating) return;

        // 根据鼠标位置使网格略微倾斜
        const { clientX, clientY } = e;
        const rotateX = (clientY / window.innerHeight - 0.5) * 3;
        const rotateY = (clientX / window.innerWidth - 0.5) * -3;

        gridOverlay.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
    });

    // 添加交互点击效果
    document.addEventListener('click', () => {
        if (isAnimating) return;
        isAnimating = true;

        // 点击时添加脉冲效果
        gridOverlay.style.animation = 'none';
        gridOverlay.offsetHeight; // 触发重排
        gridOverlay.style.animation = 'grid-pulse 1s forwards';

        setTimeout(() => {
            gridOverlay.style.animation = 'grid-fade 8s infinite alternate';
            isAnimating = false;
        }, 1000);
    });

    // 添加脉冲效果关键帧
    const style = document.createElement('style');
    style.textContent = `
        @keyframes grid-pulse {
            0% { opacity: 0.3; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(1.01); }
            100% { opacity: 0.5; transform: scale(1); }
        }
    `;
    document.head.appendChild(style);
}

// 生成彩色星星
function initStars() {
    const starsContainer = document.querySelector('.stars-container');
    if (!starsContainer) return;

    // 清空现有内容
    starsContainer.innerHTML = '';

    // 定义星星颜色
    const colors = [
        '#00ffcc', // 青绿色
        '#0088ff', // 蓝色
        '#aa00ff', // 紫色
        '#ff00aa', // 粉色
        '#ffcc00', // 黄色
        '#ff3366', // 红色
        '#33ffaa'  // 淡绿色
    ];

    // 创建随机星星
    const starCount = Math.min(window.innerWidth / 3, 150); // 根据屏幕宽度自适应星星数量

    for (let i = 0; i < starCount; i++) {
        const star = document.createElement('div');
        star.className = 'star';

        // 随机位置
        star.style.left = `${Math.random() * 100}%`;
        star.style.top = `${Math.random() * 100}%`;

        // 随机大小（1-3px）
        const size = Math.random() * 2 + 1;
        star.style.width = `${size}px`;
        star.style.height = `${size}px`;

        // 随机颜色
        const color = colors[Math.floor(Math.random() * colors.length)];
        star.style.setProperty('--color', color);

        // 随机发光大小
        const glowSize = Math.random() * 6 + 2;
        star.style.setProperty('--glow-size', `${glowSize}px`);

        // 随机动画持续时间（2-8秒）
        const duration = Math.random() * 6 + 2;
        star.style.setProperty('--duration', `${duration}s`);

        // 随机动画延迟
        const delay = Math.random() * 5;
        star.style.setProperty('--delay', `${delay}s`);

        // 随机不透明度
        const opacity = Math.random() * 0.5 + 0.4;
        star.style.setProperty('--opacity', opacity);

        // 添加到容器
        starsContainer.appendChild(star);
    }

    // 添加一些大的、明亮的星星
    for (let i = 0; i < 15; i++) {
        const star = document.createElement('div');
        star.className = 'star';

        // 随机位置
        star.style.left = `${Math.random() * 100}%`;
        star.style.top = `${Math.random() * 100}%`;

        // 较大的尺寸
        const size = Math.random() * 2 + 2;
        star.style.width = `${size}px`;
        star.style.height = `${size}px`;

        // 随机颜色
        const color = colors[Math.floor(Math.random() * colors.length)];
        star.style.setProperty('--color', color);

        // 更大的发光效果
        const glowSize = Math.random() * 10 + 5;
        star.style.setProperty('--glow-size', `${glowSize}px`);

        // 更长的动画持续时间
        const duration = Math.random() * 8 + 4;
        star.style.setProperty('--duration', `${duration}s`);

        // 随机动画延迟
        const delay = Math.random() * 5;
        star.style.setProperty('--delay', `${delay}s`);

        // 更高的不透明度
        star.style.setProperty('--opacity', '0.8');

        // 添加到容器
        starsContainer.appendChild(star);
    }
}

// 初始化所有背景效果
function initBackgroundEffects() {
    initMatrixEffect();
    initRippleEffect();
    initGridEffect();
    initStars();

    // 窗口大小变化时重新生成星星
    window.addEventListener('resize', () => {
        // 节流处理，避免频繁调用
        if (window.starResizeTimeout) {
            clearTimeout(window.starResizeTimeout);
        }
        window.starResizeTimeout = setTimeout(() => {
            initStars();
        }, 500);
    });
}

// 页面加载完成后初始化所有效果
document.addEventListener('DOMContentLoaded', function() {
    // 初始化加载页面
    initLoadingScreen();

    // 初始化粒子效果
    createRandomParticle();

    // 初始化主题选项动画
    animateThemeOptions();

    // 初始化视频播放器
    initVideoPlayer();

    // 初始化背景效果
    initBackgroundEffects();
});

// 仅用于开发环境 - 清除会话状态
function resetVisitState() {
    // 清除会话状态相关变量
    sessionStorage.clear();
    console.log('Visit state has been reset. This will simulate a first-time visit on the next navigation.');
}

// 注释掉下面这行代码来禁用自动重置（仅开发环境使用）
// resetVisitState();
