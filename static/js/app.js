// API 基础配置
const API_BASE = '/api';

// 获取token
function getToken() {
    return localStorage.getItem('diary_token');
}

// 设置token
function setToken(token) {
    localStorage.setItem('diary_token', token);
}

// 清除token
function clearToken() {
    localStorage.removeItem('diary_token');
}

// 检查是否已登录
function isLoggedIn() {
    return !!getToken();
}

// API请求封装
async function apiRequest(url, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
        const response = await fetch(`${API_BASE}${url}`, {
            ...options,
            headers
        });
        
        if (response.status === 401) {
            clearToken();
            window.location.href = '/login';
            throw new Error('请先登录');
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || '请求失败');
        }
        
        return data;
    } catch (error) {
        console.error('API请求错误:', error);
        throw error;
    }
}

// 登出
function logout() {
    clearToken();
    window.location.href = '/login';
}

// 检查登录状态
async function checkAuth() {
    if (!isLoggedIn()) {
        window.location.href = '/login';
        return false;
    }
    
    try {
        await apiRequest('/auth/me');
        return true;
    } catch (error) {
        clearToken();
        window.location.href = '/login';
        return false;
    }
}

// 显示加载状态
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    }
}

// 隐藏加载状态
function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '';
    }
}

// 显示消息提示
function showMessage(message, type = 'success') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = message;
    messageDiv.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;padding:0.6875rem 1rem;box-shadow:0 4px 12px rgba(46,40,35,0.08);font-weight:500;font-family:inherit;font-size:0.875rem;min-width:200px;max-width:360px;';

    document.body.appendChild(messageDiv);

    // 渐入动画
    messageDiv.style.opacity = '0';
    messageDiv.style.transform = 'translateY(-8px)';
    messageDiv.style.transition = 'all 0.2s ease';
    requestAnimationFrame(() => {
        messageDiv.style.opacity = '1';
        messageDiv.style.transform = 'translateY(0)';
    });

    setTimeout(() => {
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(-8px)';
        setTimeout(() => messageDiv.remove(), 200);
    }, 2400);
}

// 格式化日期
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 获取所有日记
async function getDiaries() {
    return await apiRequest('/diaries');
}

// 获取单个日记
async function getDiary(id) {
    return await apiRequest(`/diaries/${id}`);
}

// 创建日记
async function createDiary(title, content, diaryDate) {
    const body = { title: title || "", content: content };
    if (diaryDate) {
        body.diary_date = diaryDate + 'T00:00:00';
    }
    return await apiRequest('/diaries', {
        method: 'POST',
        body: JSON.stringify(body)
    });
}

// 更新日记
async function updateDiary(id, title, content) {
    return await apiRequest(`/diaries/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ title, content })
    });
}

// 删除日记
async function deleteDiary(id) {
    return await apiRequest(`/diaries/${id}`, {
        method: 'DELETE'
    });
}

// 搜索短语
async function searchPhrase(phrase, sourceLang = 'zh', targetLang = 'en') {
    return await apiRequest('/search-phrase', {
        method: 'POST',
        body: JSON.stringify({ phrase, source_lang: sourceLang, target_lang: targetLang })
    });
}

// 导出函数供其他模块使用
window.api = {
    request: apiRequest,
    getDiaries,
    getDiary,
    createDiary,
    updateDiary,
    deleteDiary,
    searchPhrase,
    showLoading,
    hideLoading,
    showMessage,
    formatDate,
    logout,
    checkAuth,
    isLoggedIn
};
