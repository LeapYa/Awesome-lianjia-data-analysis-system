<template>
  <div class="ip-management-container">
    <el-card class="ip-status-card">
      <template #header>
        <div class="card-header">
          <h3>{{ $t('ipManagement.currentIp') }}</h3>
        </div>
      </template>
      <div class="ip-status">
        <div class="current-ip">
          <div class="ip-address">
            <el-icon><Connection /></el-icon>
            <span>{{ currentIp }}</span>
          </div>
          <div class="ip-location">
            <el-icon><Location /></el-icon>
            <span>{{ currentLocation }}</span>
          </div>
        </div>
        <div class="ip-actions">
          <el-button type="primary" @click="refreshIp">
            <el-icon><Refresh /></el-icon>
            {{ $t('ipManagement.refreshIp') }}
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card class="ip-pool-card">
      <template #header>
        <div class="card-header">
          <h3>{{ $t('ipManagement.proxyPool') }}</h3>
          <el-button type="primary" size="small" @click="addProxy">
            <el-icon><Plus /></el-icon>
            {{ $t('ipManagement.addProxy') }}
          </el-button>
        </div>
      </template>
      
      <el-table :data="proxyList" style="width: 100%" v-loading="loading">
        <el-table-column prop="ip" :label="$t('ipManagement.ipAddress')" />
        <el-table-column prop="port" :label="$t('ipManagement.port')" width="100" />
        <el-table-column prop="location" :label="$t('ipManagement.location')" width="150" />
        <el-table-column prop="status" :label="$t('ipManagement.status')" width="120">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ $t(`ipManagement.statusTypes.${scope.row.status}`) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="latency" :label="$t('ipManagement.latency')" width="120">
          <template #default="scope">
            {{ scope.row.latency ? `${scope.row.latency}ms` : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="lastUsed" :label="$t('ipManagement.lastUsed')" width="180" />
        <el-table-column :label="$t('ipManagement.actions')" width="200" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" @click="testProxy(scope.row)">
              {{ $t('ipManagement.test') }}
            </el-button>
            <el-button size="small" type="danger" @click="deleteProxy(scope.row)">
              {{ $t('ipManagement.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="ip-settings-card">
      <template #header>
        <div class="card-header">
          <h3>{{ $t('ipManagement.ipSettings') }}</h3>
        </div>
      </template>
      
      <el-form :model="ipSettings" label-width="180px">
        <el-form-item :label="$t('ipManagement.rotationStrategy')">
          <el-select v-model="ipSettings.rotationStrategy" style="width: 100%">
            <el-option
              v-for="item in rotationStrategies"
              :key="item.value"
              :label="$t(`ipManagement.strategies.${item.label}`)"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item :label="$t('ipManagement.rotationInterval')" v-if="ipSettings.rotationStrategy === 'time'">
          <el-input-number v-model="ipSettings.rotationInterval" :min="1" :max="1440" />
          <span class="unit-label">{{ $t('ipManagement.minutes') }}</span>
        </el-form-item>
        
        <el-form-item :label="$t('ipManagement.maxFailures')" v-if="ipSettings.rotationStrategy === 'failure'">
          <el-input-number v-model="ipSettings.maxFailures" :min="1" :max="10" />
          <span class="unit-label">{{ $t('ipManagement.failures') }}</span>
        </el-form-item>
        
        <el-form-item :label="$t('ipManagement.autoAddProxies')">
          <el-switch v-model="ipSettings.autoAddProxies" />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="saveSettings">{{ $t('ipManagement.saveSettings') }}</el-button>
          <el-button @click="resetSettings">{{ $t('ipManagement.resetSettings') }}</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 添加代理对话框 -->
    <el-dialog
      v-model="proxyDialogVisible"
      :title="$t('ipManagement.addProxy')"
      width="500px"
    >
      <el-form :model="newProxy" label-width="100px">
        <el-form-item :label="$t('ipManagement.ipAddress')" required>
          <el-input v-model="newProxy.ip" />
        </el-form-item>
        <el-form-item :label="$t('ipManagement.port')" required>
          <el-input-number v-model="newProxy.port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item :label="$t('ipManagement.username')">
          <el-input v-model="newProxy.username" />
        </el-form-item>
        <el-form-item :label="$t('ipManagement.password')">
          <el-input v-model="newProxy.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="proxyDialogVisible = false">{{ $t('cancel') }}</el-button>
          <el-button type="primary" @click="saveProxy">
            {{ $t('ipManagement.addProxy') }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Connection, Location, Refresh, Plus } from '@element-plus/icons-vue';
// eslint-disable-next-line no-unused-vars
import api from '../api/api';

export default {
  name: 'IpManagement',
  components: {
    Connection,
    Location,
    Refresh,
    Plus
  },
  setup() {
    // 当前IP信息
    const currentIp = ref('---.---.---.---');
    const currentLocation = ref('未知');
    
    // 代理列表
    const proxyList = ref([]);
    const loading = ref(false);
    
    // IP设置
    const ipSettings = reactive({
      rotationStrategy: 'manual', // manual, time, failure, request
      rotationInterval: 30, // 分钟
      maxFailures: 3,
      autoAddProxies: false
    });
    
    // 轮换策略选项
    const rotationStrategies = [
      { value: 'manual', label: 'manual' },
      { value: 'time', label: 'time' },
      { value: 'failure', label: 'failure' },
      { value: 'request', label: 'request' }
    ];
    
    // 添加代理对话框
    const proxyDialogVisible = ref(false);
    const newProxy = reactive({
      ip: '',
      port: 8080,
      username: '',
      password: ''
    });
    
    // 获取当前IP信息
    const getCurrentIp = async () => {
      try {
        // 调用后端API获取当前IP信息
        const response = await api.getCurrentIp();
        currentIp.value = response.ip;
        currentLocation.value = response.location;
      } catch (error) {
        console.error('获取当前IP信息失败:', error);
        ElMessage.error('获取当前IP信息失败');
      }
    };
    
    // 刷新IP
    const refreshIp = async () => {
      try {
        // 调用后端API刷新IP
        const response = await api.refreshIp();
        if (response.success) {
          ElMessage.success(response.message || 'IP已刷新');
          getCurrentIp();
        } else {
          ElMessage.warning(response.message || 'IP刷新失败');
        }
      } catch (error) {
        console.error('刷新IP失败:', error);
        ElMessage.error('刷新IP失败');
      }
    };
    
    // 获取代理列表
    const getProxyList = async () => {
      loading.value = true;
      try {
        // 调用后端API获取代理列表
        const response = await api.getProxyList();
        proxyList.value = response;
      } catch (error) {
        console.error('获取代理列表失败:', error);
        ElMessage.error('获取代理列表失败');
      } finally {
        loading.value = false;
      }
    };
    
    // 添加代理
    const addProxy = () => {
      // 重置表单
      Object.assign(newProxy, {
        ip: '',
        port: 8080,
        username: '',
        password: ''
      });
      proxyDialogVisible.value = true;
    };
    
    // 保存代理
    const saveProxy = async () => {
      // 表单验证
      if (!newProxy.ip || !newProxy.port) {
        ElMessage.warning('请填写必填项');
        return;
      }
      
      try {
        // 调用后端API添加代理
        const response = await api.addProxy(newProxy);
        if (response.success) {
          ElMessage.success(response.message || '已添加代理');
          proxyDialogVisible.value = false;
          getProxyList(); // 刷新列表
        } else {
          ElMessage.warning(response.message || '添加代理失败');
        }
      } catch (error) {
        console.error('添加代理失败:', error);
        ElMessage.error('添加代理失败');
      }
    };
    
    // 测试代理
    const testProxy = async (proxy) => {
      try {
        // 调用后端API测试代理
        const response = await api.testProxy(proxy.id);
        if (response.success) {
          ElMessage.success(`代理 ${proxy.ip}:${proxy.port} 测试成功`);
        } else {
          ElMessage.warning(response.message || '代理测试失败');
        }
        getProxyList(); // 刷新列表
      } catch (error) {
        console.error('测试代理失败:', error);
        ElMessage.error('测试代理失败');
      }
    };
    
    // 删除代理
    const deleteProxy = async (proxy) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除代理 ${proxy.ip}:${proxy.port} 吗？`,
          '删除确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );
        
        // 调用后端API删除代理
        const response = await api.deleteProxy(proxy.id);
        if (response.success) {
          ElMessage.success(response.message || '已删除代理');
          getProxyList(); // 刷新列表
        } else {
          ElMessage.warning(response.message || '删除代理失败');
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除代理失败:', error);
          ElMessage.error('删除代理失败');
        }
      }
    };
    
    // 根据状态获取标签类型
    const getStatusType = (status) => {
      const map = {
        active: 'success',
        inactive: 'info',
        error: 'danger'
      };
      return map[status] || 'info';
    };
    
    // 保存设置
    const saveSettings = async () => {
      try {
        // 调用后端API保存设置
        const response = await api.saveIpSettings({
          rotation_strategy: ipSettings.rotationStrategy,
          rotation_interval: ipSettings.rotationInterval,
          max_failures: ipSettings.maxFailures,
          auto_add_proxies: ipSettings.autoAddProxies
        });
        
        if (response.success) {
          ElMessage.success(response.message || '设置已保存');
        } else {
          ElMessage.warning(response.message || '保存设置失败');
        }
      } catch (error) {
        console.error('保存设置失败:', error);
        ElMessage.error('保存设置失败');
      }
    };
    
    // 获取IP设置
    const getIpSettings = async () => {
      try {
        // 调用后端API获取IP设置
        const settings = await api.getIpSettings();
        Object.assign(ipSettings, {
          rotationStrategy: settings.rotation_strategy,
          rotationInterval: settings.rotation_interval,
          maxFailures: settings.max_failures,
          autoAddProxies: settings.auto_add_proxies
        });
      } catch (error) {
        console.error('获取IP设置失败:', error);
      }
    };
    
    // 重置设置
    const resetSettings = async () => {
      try {
        // 重置为默认值并保存
        Object.assign(ipSettings, {
          rotationStrategy: 'manual',
          rotationInterval: 30,
          maxFailures: 3,
          autoAddProxies: false
        });
        
        await saveSettings();
        ElMessage.success('设置已重置');
      } catch (error) {
        console.error('重置设置失败:', error);
        ElMessage.error('重置设置失败');
      }
    };
    
    // 页面加载时获取数据
    onMounted(() => {
      getCurrentIp();
      getProxyList();
      getIpSettings();
    });
    
    return {
      currentIp,
      currentLocation,
      proxyList,
      loading,
      ipSettings,
      rotationStrategies,
      proxyDialogVisible,
      newProxy,
      refreshIp,
      addProxy,
      saveProxy,
      testProxy,
      deleteProxy,
      getStatusType,
      saveSettings,
      resetSettings
    };
  }
};
</script>

<style scoped>
.ip-management-container {
  padding: 20px;
}

.ip-status-card,
.ip-pool-card,
.ip-settings-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
}

.ip-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.current-ip {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ip-address,
.ip-location {
  display: flex;
  align-items: center;
  font-size: 16px;
}

.ip-address .el-icon,
.ip-location .el-icon {
  margin-right: 10px;
  font-size: 20px;
}

.ip-address {
  font-weight: 500;
  font-size: 22px;
}

.unit-label {
  margin-left: 10px;
  color: #606266;
}
</style> 