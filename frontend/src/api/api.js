import axios from 'axios';

// 通过Vue代理访问后端
const apiBaseUrl = process.env.VUE_APP_API_BASE_URL || '/api';

// API客户端配置
const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 45000,  // 增加全局超时时间到45秒
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 如果存在身份验证令牌，在每个请求头中添加它
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // 添加语言标识头部
    const language = localStorage.getItem('language') || 'zh-CN';
    config.headers['Accept-Language'] = language;
    
    // 如果是清除数据的请求，添加管理员角色头部
    if (config.url.includes('/settings/purge')) {
      config.headers['X-User-Role'] = 'admin';
    }
    
    // 检查是否存在临时管理员标记
    const tempAdminRole = localStorage.getItem('temp_admin_role');
    if (tempAdminRole) {
      config.headers['X-User-Role'] = tempAdminRole;
    }
    
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data;
  },
  error => {
    // 处理认证错误（401）或令牌过期
    if (error.response && error.response.status === 401) {
      // 清除无效令牌
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      // 获取当前路由
      const currentPath = window.location.pathname;
      
      // 如果不是已经在登录页面，重定向到登录页
      if (currentPath !== '/login') {
        window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
      }
    }
    
    return Promise.reject(error.response?.data || error);
  }
);

// API方法
export default {
  // 导出axios实例供直接使用
  axios: api,
  
  // 城市相关
  getCities() {
    return api.get('/cities');
  },
  
  // 爬虫任务相关
  createCrawlTask(data) {
    // 记录爬虫任务创建时间
    const now = new Date().getTime();
    localStorage.setItem('lastCrawlTaskStartTime', now.toString());
    return api.post('/tasks/crawl', data);
  },
  
  createSeleniumCrawlTask(data) {
    // 记录爬虫任务创建时间
    const now = new Date().getTime();
    localStorage.setItem('lastCrawlTaskStartTime', now.toString());
    return api.post('/tasks/selenium_crawl', data);
  },
  
  getTasks(params) {
    return api.get('/tasks', { params });
  },
  
  getTasksCount(params = {}) {
    return api.get('/tasks/count', { params });
  },
  
  getTaskById(taskId) {
    return api.get(`/tasks/${taskId}`);
  },
  
  deleteTask(taskId) {
    return api.delete(`/tasks/${taskId}`);
  },
  
  // 房源数据相关
  getHouses(params) {
    return api.get('/houses', { params });
  },
  
  getHouseCount(params) {
    return api.get('/houses/count', { params });
  },
  
  getHouseById(houseId) {
    return api.get(`/houses/${houseId}`);
  },
  
  // 数据分析相关
  runAnalysis(data) {
    return api.post('/analysis/run', data);
  },
  
  getAnalysisResults(params) {
    return api.get('/analysis/results', { params });
  },
  
  getAnalysisResultById(resultId) {
    return api.get(`/analysis/results/${resultId}`);
  },
  
  getAnalysisTypes() {
    return api.get('/analysis/types');
  },
  
  // 区域相关
  getDistricts(city) {
    return api.get('/districts', { params: { city } });
  },
  
  // 统计概览
  getSummaryStatistics(city) {
    return api.get('/statistics/summary', { params: { city } });
  },
  
  // 首页仪表盘数据
  getDashboardStats() {
    return api.get('/dashboard');
  },
  
  // 用户认证相关API
  login(credentials) {
    return api.post('/auth/login', credentials);
  },
  
  register(userData) {
    return api.post('/auth/register', userData);
  },
  
  forgotPassword(data) {
    return api.post('/auth/forgot-password', data);
  },
  
  resetPassword(data) {
    return api.post('/auth/reset-password', data);
  },
  
  logout() {
    return api.post('/auth/logout');
  },
  
  getUserProfile() {
    return api.get('/auth/profile');
  },
  
  updateUserProfile(profileData) {
    return api.put('/auth/profile', profileData);
  },
  
  uploadAvatar(avatarData) {
    return api.post('/auth/avatar', { avatar_data: avatarData });
  },
  
  deleteAccount(password) {
    return api.delete('/auth/account', { params: { password } });
  },
  
  checkAuthStatus() {
    return api.get('/auth/check');
  },
  
  // 新增：用户设置相关API
  getUserSettings() {
    return api.get('/auth/settings');
  },
  
  updateUserSettings(settingsData) {
    return api.put('/auth/settings', settingsData);
  },
  
  // 新增：系统设置相关API
  getSystemSettings() {
    return api.get('/settings');
  },
  
  updateSystemSettings(settingsData) {
    return api.put('/settings', settingsData);
  },
  
  getSystemInfo() {
    return api.get('/settings/info');
  },
  
  purgeData() {
    return api.post('/settings/purge', {}, {
      headers: {
        'X-User-Role': 'admin'  // 添加自定义请求头传递角色信息
      }
    });
  },
  
  exportData() {
    return api.get('/settings/export');
  },
  
  exportHouses(params) {
    return api.get('/export/houses', { 
      params,
      responseType: 'blob'
    }).then(response => {
      // 从响应头中获取文件名
      const contentDisposition = response.headers?.['content-disposition'];
      let filename = 'houses.csv';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1];
        }
      }
      
      // 创建blob链接
      const blob = new Blob([response], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      
      return {
        file_url: url,
        filename: filename
      };
    });
  },
  
  // 定时任务相关接口
  createScheduledTask(taskData) {
    return api.post('/scheduled-tasks', taskData);
  },
  
  getScheduledTasks(params = { limit: 10, offset: 0 }) {
    return api.get('/scheduled-tasks', { params });
  },
  
  getScheduledTaskById(id) {
    return api.get(`/scheduled-tasks/${id}`);
  },
  
  updateScheduledTask(id, taskData) {
    return api.put(`/scheduled-tasks/${id}`, taskData);
  },
  
  deleteScheduledTask(id) {
    return api.delete(`/scheduled-tasks/${id}`);
  },
  
  // IP管理相关接口
  getCurrentIp() {
    return api.get('/api/ip/current');
  },
  
  refreshIp() {
    return api.post('/api/ip/refresh');
  },
  
  getProxyList() {
    return api.get('/api/ip/proxies');
  },
  
  addProxy(proxyData) {
    return api.post('/api/ip/proxies', proxyData);
  },
  
  deleteProxy(proxyId) {
    return api.delete(`/api/ip/proxies/${proxyId}`);
  },
  
  testProxy(proxyId) {
    return api.post(`/api/ip/proxies/${proxyId}/test`);
  },
  
  getIpSettings() {
    return api.get('/api/ip/settings');
  },
  
  saveIpSettings(settingsData) {
    return api.post('/api/ip/settings', settingsData);
  },
  
  // 获取图片的Base64编码
  getImageBase64(imageUrl) {
    return api.get('/proxy/image', { 
      params: { url: imageUrl },
      timeout: 10000  // 10秒超时
    });
  }
}; 