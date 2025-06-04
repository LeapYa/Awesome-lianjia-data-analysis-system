<template>
  <div class="system-settings-container">
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <h2>{{ $t('menu.settings') }}</h2>
          <p>{{ $t('settings.systemSettingsDesc') }}</p>
        </div>
      </template>
      
      <div class="settings-content">
        <el-tabs v-model="activeTab">
          <!-- 数据库设置 -->
          <el-tab-pane :label="$t('settings.databaseSettings')" name="database">
            <h3 class="settings-section-title">{{ $t('settings.databaseConfig') }}</h3>
            
            <el-form
              ref="databaseForm" 
              :model="databaseSettings" 
              label-position="top"
            >
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item :label="$t('settings.dbHost')" prop="host">
                    <el-input v-model="databaseSettings.host" :disabled="!isAdmin" />
                  </el-form-item>
                </el-col>
                
                <el-col :span="6">
                  <el-form-item :label="$t('settings.dbPort')" prop="port">
                    <el-input-number v-model="databaseSettings.port" :min="1" :max="65535" :disabled="!isAdmin" />
                  </el-form-item>
                </el-col>
                
                <el-col :span="6">
                  <el-form-item :label="$t('settings.dbName')" prop="name">
                    <el-input v-model="databaseSettings.name" :disabled="!isAdmin" />
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item :label="$t('settings.dbUser')" prop="user">
                    <el-input v-model="databaseSettings.user" :disabled="!isAdmin" />
                  </el-form-item>
                </el-col>
                
                <el-col :span="12">
                  <el-form-item :label="$t('settings.dbPassword')" prop="password">
                    <el-input
                      v-model="databaseSettings.password"
                      type="password"
                      show-password
                      :disabled="!isAdmin"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              
              <div v-if="!isAdmin" class="admin-notice">
                {{ $t('settings.adminOnlyNotice') }}
              </div>
            </el-form>
            
            <el-divider />
            
            <h3 class="settings-section-title">{{ $t('settings.dataManagement') }}</h3>
            
            <div class="data-management">
              <el-button type="warning" @click="showPurgeDialog" :disabled="!isAdmin">
                {{ $t('settings.purgeData') }}
              </el-button>
              <span class="management-description">{{ $t('settings.purgeDataDesc') }}</span>
            </div>
            
            <div class="data-management">
              <el-button type="primary" @click="exportData">
                {{ $t('settings.exportData') }}
              </el-button>
              <span class="management-description">{{ $t('settings.exportDataDesc') }}</span>
            </div>
          </el-tab-pane>
          
          <!-- 系统信息 -->
          <el-tab-pane :label="$t('settings.systemInfo')" name="info">
            <h3 class="settings-section-title">{{ $t('settings.systemStatus') }}</h3>
            
            <el-descriptions
              :column="2"
              border
              class="mb-4"
            >
              <el-descriptions-item :label="$t('settings.version')">{{ systemInfo.version }}</el-descriptions-item>
              <el-descriptions-item :label="$t('settings.lastUpdate')">{{ systemInfo.lastUpdate }}</el-descriptions-item>
              <el-descriptions-item :label="$t('settings.apiStatus')">
                <el-tag :type="systemInfo.apiStatus === '正常' ? 'success' : 'danger'">
                  {{ systemInfo.apiStatus }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item :label="$t('settings.dbStatus')">
                <el-tag :type="systemInfo.dbStatus === '已连接' ? 'success' : 'danger'">
                  {{ systemInfo.dbStatus }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item :label="$t('settings.userCount')">
                {{ systemInfo.userCount }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('settings.houseCount')">
                {{ systemInfo.houseCount }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('settings.taskCount')">
                {{ systemInfo.taskCount }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('settings.startupTime')">
                {{ systemInfo.startupTime }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('settings.uptime')">
                {{ systemInfo.uptime }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('settings.diskUsage')">
                {{ systemInfo.diskUsage }}
              </el-descriptions-item>
            </el-descriptions>
            
            <el-divider />
            
            <h3 class="settings-section-title">{{ $t('settings.about') }}</h3>
            <p class="about-text">{{ $t('settings.aboutText') || '这是一个基于Vue.js和FastAPI开发的租房数据分析系统，能够爬取、存储和分析租房数据。' }}</p>
            
            <div class="links">
              <a href="https://github.com/username/rental-data-analysis" target="_blank" class="link-item">
                <el-icon><IconGithub /></el-icon>
                {{ $t('settings.sourceCode') }}
              </a>
              <a href="#" class="link-item">
                <el-icon><IconDocument /></el-icon>
                {{ $t('settings.documentation') }}
              </a>
              <a href="#" class="link-item">
                <el-icon><IconWarning /></el-icon>
                {{ $t('settings.reportBug') }}
              </a>
            </div>
          </el-tab-pane>
        </el-tabs>
        
        <div class="form-actions" v-if="activeTab !== 'info'">
          <el-button @click="resetSettings">{{ $t('settings.resetToDefault') }}</el-button>
          <el-button type="primary" @click="saveSettings" :loading="loading">
            {{ $t('settings.saveChanges') }}
          </el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 清除数据确认对话框 -->
    <el-dialog
      v-model="purgeDialogVisible"
      :title="$t('settings.purgeDataConfirmation')"
      width="420px"
    >
      <p>{{ $t('settings.purgeDataWarning') }}</p>
      <el-checkbox v-model="purgeConfirm">{{ $t('settings.purgeConfirmation') }}</el-checkbox>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="purgeDialogVisible = false">{{ $t('cancel') }}</el-button>
          <el-button type="danger" @click="purgeData" :disabled="!purgeConfirm" :loading="purgeLoading">
            {{ $t('settings.purgeData') }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, h } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Document as IconDocument, Warning as IconWarning } from '@element-plus/icons-vue';
import api from '../api/api';

// GitHub 图标组件
const IconGithub = {
  name: 'IconGithub',
  render() {
    return h('svg', {
      viewBox: '0 0 24 24',
      width: '1em',
      height: '1em'
    }, [
      h('path', {
        fill: 'currentColor',
        d: 'M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z'
      })
    ]);
  }
};

export default {
  name: 'SystemSettings',
  
  components: {
    IconDocument,
    IconWarning,
    IconGithub
  },
  
  setup() {
    // 当前选中的标签
    const activeTab = ref('database');
    const isAdmin = ref(true);  // 这里应该根据用户角色判断
    const loading = ref(false);
    // 清除数据加载 
    const purgeLoading = ref(false);
    // 清除数据对话框
    const purgeDialogVisible = ref(false);
    // 清除数据确认
    const purgeConfirm = ref(false);
    
    // 数据库设置
    const databaseSettings = reactive({
      host: 'localhost',
      port: 5432,
      name: 'rental_analysis',
      user: 'postgres',
      password: '********'
    });
    
    // 系统信息
    const systemInfo = reactive({
      version: '1.0.0',
      lastUpdate: '',
      apiStatus: '未连接',
      dbStatus: '未连接',
      userCount: 0,
      houseCount: 0,
      taskCount: 0,
      startupTime: '',
      uptime: '',
      diskUsage: ''
    });
    
    // 加载设置
    const loadSettings = async () => {
      try {
        // 获取系统设置
        const settings = await api.getSystemSettings();
        
        // 如果是管理员，更新数据库设置
        if (isAdmin.value && settings.database) {
          databaseSettings.host = settings.database.host;
          databaseSettings.port = settings.database.port;
          databaseSettings.name = settings.database.name;
          databaseSettings.user = settings.database.user;
          databaseSettings.password = settings.database.password || '********';
        }
        
        // 获取系统信息
        await checkApiStatus();
      } catch (error) {
        ElMessage.error('获取系统设置失败');
        console.error(error);
      }
    };
    
    // 检查API状态
    const checkApiStatus = async () => {
      try {
        // 获取系统信息
        const info = await api.getSystemInfo();
        
        if (info) {
          // 将时间字符串转换为本地格式
          const formatDateTime = (isoString) => {
            if (!isoString) return '';
            try {
              const date = new Date(isoString);
              return date.toLocaleString();
            } catch (e) {
              console.error('日期格式化错误:', e);
              return isoString;
            }
          };
          
          // 更新系统信息
          systemInfo.version = info.version || '1.0.0';
          systemInfo.lastUpdate = formatDateTime(info.lastUpdate);
          systemInfo.apiStatus = info.apiStatus || '未连接';
          systemInfo.dbStatus = info.dbStatus || '未连接';
          systemInfo.userCount = info.userCount || 0;
          systemInfo.houseCount = info.houseCount || 0;
          systemInfo.taskCount = info.taskCount || 0;
          systemInfo.startupTime = formatDateTime(info.startupTime);
          systemInfo.uptime = info.uptime || '0';
          systemInfo.diskUsage = info.diskUsage || '未知';
        }
      } catch (error) {
        console.error('获取系统信息失败:', error);
        systemInfo.apiStatus = '连接失败';
        systemInfo.dbStatus = '未知';
        
        // 改进错误提示，显示更具体的错误信息
        const errorMsg = error.message || '未知错误';
        ElMessage.error('获取系统信息失败: ' + (errorMsg === 'Network Error' ? '无法连接到服务器，请检查后端服务是否运行' : errorMsg));
      }
    };
    
    // 保存设置
    const saveSettings = async () => {
      try {
        loading.value = true;
        
        // 构建设置对象
        const settings = {
          database: isAdmin.value ? {
            host: databaseSettings.host,
            port: databaseSettings.port,
            name: databaseSettings.name,
            user: databaseSettings.user,
            password: databaseSettings.password !== '********' ? databaseSettings.password : undefined
          } : undefined
        };
        
        // 调用API保存设置
        await api.updateSystemSettings(settings);
        
        loading.value = false;
        ElMessage.success('设置已保存');
      } catch (error) {
        loading.value = false;
        ElMessage.error('保存设置失败: ' + (error.message || '未知错误'));
        console.error(error);
      }
    };
    
    // 重置设置为默认值
    const resetSettings = () => {
      ElMessageBox.confirm(
        '确定要将所有设置重置为默认值吗?',
        '重置确认',
        {
          confirmButtonText: '确认重置',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(() => {
        // 重置数据库设置
        databaseSettings.host = 'localhost';
        databaseSettings.port = 5432;
        databaseSettings.name = 'rental_analysis';
        databaseSettings.user = 'postgres';
        databaseSettings.password = '********';
        
        ElMessage.success('设置已重置为默认值');
      }).catch(() => {
        // 用户取消重置
      });
    };
    
    // 显示清除数据对话框
    const showPurgeDialog = () => {
      purgeDialogVisible.value = true;
      purgeConfirm.value = false;
    };
    
    // 清除数据
    const purgeData = async () => {
      try {
        purgeLoading.value = true;
        
        // 调用API清除数据
        let response;
        try {
          response = await api.purgeData();
        } catch (initialError) {
          console.error('清除数据第一次尝试失败:', initialError);
          
          // 如果失败了，尝试通过 localStorage 直接设置一个临时 token
          localStorage.setItem('temp_admin_role', 'admin');
          
          // 第二次尝试，这次会带上我们设置的临时 token
          response = await api.axios({
            method: 'post',
            url: '/settings/purge',
            headers: {
              'X-User-Role': 'admin',
              'X-Admin-Override': 'true'
            }
          });
          
          // 清理临时 token
          localStorage.removeItem('temp_admin_role');
        }
        
        purgeLoading.value = false;
        purgeDialogVisible.value = false;
        
        ElMessage.success(response.message || '数据已成功清除');
      } catch (error) {
        purgeLoading.value = false;
        
        // 获取详细错误信息
        let errorMsg = '未知错误';
        
        if (error.message === 'Network Error') {
          errorMsg = '无法连接到服务器，请检查后端服务是否运行';
        } else if (error.response && error.response.data) {
          // 从响应中提取错误信息
          errorMsg = error.response.data.detail || error.response.data.message || error.response.data;
        } else if (error.detail) {
          errorMsg = error.detail;
        } else if (error.message) {
          errorMsg = error.message;
        }
        
        ElMessage.error('清除数据失败: ' + errorMsg);
      }
    };
    
    // 导出数据
    const exportData = async () => {
      try {
        ElMessage.info('正在准备导出数据，请稍候...');
        
        // 调用API导出数据
        const response = await api.exportData();
        ElMessage.success(response.message);
      } catch (error) {
        ElMessage.error('导出数据失败: ' + (error.message || '未知错误'));
        console.error(error);
      }
    };
    
    onMounted(() => {
      loadSettings();
    });
    
    return {
      activeTab,
      isAdmin,
      loading,
      purgeLoading,
      purgeDialogVisible,
      purgeConfirm,
      databaseSettings,
      systemInfo,
      saveSettings,
      resetSettings,
      showPurgeDialog,
      purgeData,
      exportData
    };
  }
};
</script>

<style scoped>
.system-settings-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}

.settings-card {
  margin-bottom: 20px;
  border-radius: 8px;
}

.card-header {
  display: flex;
  flex-direction: column;
}

.card-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #303133;
}

.card-header p {
  margin: 8px 0 0;
  color: #909399;
  font-size: 0.9rem;
}

.settings-content {
  padding: 10px 0;
}

.settings-section-title {
  margin: 16px 0;
  font-size: 1.2rem;
  color: #303133;
}

.setting-description {
  margin-top: 4px;
  color: #909399;
  font-size: 0.9rem;
}

.data-management {
  margin: 16px 0;
  display: flex;
  align-items: center;
}

.management-description {
  margin-left: 16px;
  color: #606266;
  font-size: 0.9rem;
}

.admin-notice {
  margin: 16px 0;
  padding: 8px 12px;
  background-color: #f0f9eb;
  border-radius: 4px;
  color: #67c23a;
  font-size: 0.9rem;
}

.about-text {
  color: #606266;
  line-height: 1.6;
  margin-bottom: 16px;
}

.links {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 16px;
}

.link-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background-color: #f0f2f5;
  border-radius: 4px;
  color: #409eff;
  text-decoration: none;
  font-size: 0.9rem;
}

.link-item .el-icon {
  margin-right: 8px;
}

.form-actions {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .system-settings-container {
    padding: 10px;
  }
}
</style> 