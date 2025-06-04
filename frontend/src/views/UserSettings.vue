<template>
  <div class="user-settings-container">
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <h2>{{ $t('user.settings') }}</h2>
          <p>{{ $t('user.settingsDesc') }}</p>
        </div>
      </template>
      
      <div class="settings-content">
        <el-form 
          ref="settingsForm" 
          :model="settings" 
          label-position="top"
        >
          <h3 class="settings-section-title">{{ $t('user.notificationSettings') }}</h3>
          
          <el-form-item :label="$t('user.emailNotifications')">
            <el-switch v-model="settings.emailNotifications" />
            <div class="setting-description">
              {{ $t('user.emailNotificationsDesc') }}
            </div>
          </el-form-item>
          
          <el-form-item :label="$t('user.taskCompletionNotifications')">
            <el-switch v-model="settings.taskCompletionNotifications" />
            <div class="setting-description">
              {{ $t('user.taskCompletionNotificationsDesc') }}
            </div>
          </el-form-item>
          
          <el-divider />
          
          <h3 class="settings-section-title">{{ $t('user.displaySettings') }}</h3>
          
          <el-form-item :label="$t('user.language')">
            <language-switcher standalone />
          </el-form-item>
          
          <el-form-item :label="$t('user.theme')">
            <el-radio-group v-model="settings.theme">
              <el-radio label="light">{{ $t('user.themeLight') }}</el-radio>
              <el-radio label="dark">{{ $t('user.themeDark') }}</el-radio>
              <el-radio label="system">{{ $t('user.themeSystem') }}</el-radio>
            </el-radio-group>
            <div class="setting-description">
              {{ $t('user.themeDesc') }}
            </div>
          </el-form-item>
          
          <el-divider />
          
          <h3 class="settings-section-title">{{ $t('user.accountSettings') }}</h3>
          
          <el-form-item :label="$t('user.dataSharing')">
            <el-switch v-model="settings.dataSharing" />
            <div class="setting-description">
              {{ $t('user.dataSharingDesc') }}
            </div>
          </el-form-item>
          
          <div class="danger-zone">
            <h3 class="danger-zone-title">{{ $t('user.dangerZone') }}</h3>
            <p>{{ $t('user.dangerZoneDesc') }}</p>
            
            <el-button type="danger" plain @click="showDeleteAccountDialog">
              {{ $t('user.deleteAccount') }}
            </el-button>
          </div>
          
          <div class="form-actions">
            <el-button type="primary" @click="saveSettings" :loading="loading">
              {{ $t('user.saveChanges') }}
            </el-button>
          </div>
        </el-form>
      </div>
    </el-card>
    
    <!-- 删除账户确认对话框 -->
    <el-dialog
      v-model="deleteDialogVisible"
      :title="$t('user.deleteAccountConfirmation')"
      width="420px"
    >
      <p>{{ $t('user.deleteAccountWarning') }}</p>
      <el-form ref="deleteForm" :model="deleteFormData" label-position="top">
        <el-form-item 
          :label="$t('user.password')" 
          prop="password" 
          :rules="{ required: true, message: $t('user.passwordRequired') }"
        >
          <el-input 
            v-model="deleteFormData.password" 
            type="password" 
            show-password
            :placeholder="$t('user.passwordPlaceholder')"
          />
        </el-form-item>
        <el-form-item 
          :label="$t('user.deleteConfirmation')" 
          prop="confirmation"
          :rules="{ required: true, message: $t('user.confirmationRequired') }"
        >
          <el-input 
            v-model="deleteFormData.confirmation" 
            :placeholder="$t('user.deleteConfirmationPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="deleteDialogVisible = false">{{ $t('cancel') }}</el-button>
          <el-button type="danger" @click="deleteAccount" :loading="deleteLoading">
            {{ $t('user.deleteAccount') }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { useRouter } from 'vue-router';
import LanguageSwitcher from '../components/LanguageSwitcher.vue';
import api from '../api/api';

export default {
  name: 'UserSettings',
  
  components: {
    LanguageSwitcher
  },
  
  setup() {
    const router = useRouter();
    const settingsForm = ref(null);
    const deleteForm = ref(null);
    const loading = ref(false);
    const deleteLoading = ref(false);
    const deleteDialogVisible = ref(false);
    
    // 用户设置数据
    const settings = reactive({
      emailNotifications: true,
      taskCompletionNotifications: true,
      theme: 'light',
      dataSharing: true
    });
    
    // 删除账户表单
    const deleteFormData = reactive({
      password: '',
      confirmation: ''
    });
    
    // 加载用户设置
    const loadUserSettings = async () => {
      try {
        // 这里应该从API获取用户设置
        // 当前使用模拟数据
        settings.emailNotifications = true;
        settings.taskCompletionNotifications = true;
        settings.theme = localStorage.getItem('theme') || 'light';
        settings.dataSharing = true;
      } catch (error) {
        ElMessage.error('获取设置失败');
        console.error(error);
      }
    };
    
    // 保存用户设置
    const saveSettings = async () => {
      try {
        loading.value = true;
        
        // 保存主题设置到本地存储
        localStorage.setItem('theme', settings.theme);
        
        // 这里应该调用API保存用户设置
        await new Promise(resolve => setTimeout(resolve, 500)); // 模拟API调用
        
        loading.value = false;
        ElMessage.success('设置已保存');
      } catch (error) {
        loading.value = false;
        ElMessage.error('保存设置失败: ' + (error.message || '未知错误'));
        console.error(error);
      }
    };
    
    // 显示删除账户对话框
    const showDeleteAccountDialog = () => {
      deleteDialogVisible.value = true;
      // 重置表单
      deleteFormData.password = '';
      deleteFormData.confirmation = '';
    };
    
    // 删除账户
    const deleteAccount = async () => {
      if (!deleteForm.value) return;
      
      await deleteForm.value.validate(async (valid) => {
        if (valid) {
          // 检查确认输入是否正确
          if (deleteFormData.confirmation !== 'DELETE') {
            ElMessage.error('确认输入不正确');
            return;
          }
          
          try {
            deleteLoading.value = true;
            
            // 调用API删除账户
            await api.deleteAccount(deleteFormData.password);
            
            deleteLoading.value = false;
            deleteDialogVisible.value = false;
            
            // 清除本地存储并重定向到登录页
            localStorage.removeItem('token');
            ElMessage.success('账户已删除');
            router.push('/login');
          } catch (error) {
            deleteLoading.value = false;
            ElMessage.error('删除账户失败: ' + (error.message || '未知错误'));
            console.error(error);
          }
        }
      });
    };
    
    onMounted(() => {
      loadUserSettings();
    });
    
    return {
      settingsForm,
      deleteForm,
      settings,
      deleteFormData,
      loading,
      deleteLoading,
      deleteDialogVisible,
      saveSettings,
      showDeleteAccountDialog,
      deleteAccount
    };
  }
};
</script>

<style scoped>
.user-settings-container {
  max-width: 800px;
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

.danger-zone {
  margin-top: 32px;
  padding: 16px;
  border: 1px solid #f56c6c;
  border-radius: 8px;
  background-color: #fef0f0;
}

.danger-zone-title {
  color: #f56c6c;
  margin: 0 0 8px 0;
  font-size: 1.1rem;
}

.danger-zone p {
  margin: 0 0 16px 0;
  color: #606266;
  font-size: 0.9rem;
}

.form-actions {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .user-settings-container {
    padding: 10px;
  }
}
</style> 