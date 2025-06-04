<template>
  <div class="user-profile-container">
    <el-card class="profile-card">
      <template #header>
        <div class="card-header">
          <h2>{{ $t('user.profile') }}</h2>
          <p>{{ $t('user.profileDesc') }}</p>
        </div>
      </template>
      
      <div class="profile-content">
        <div class="avatar-section">
          <el-avatar :size="100" :src="userAvatar">{{ userInitials }}</el-avatar>
          <el-upload
            class="avatar-uploader"
            :show-file-list="false"
            :auto-upload="false"
            :on-change="handleAvatarChange"
          >
            <el-button type="primary" plain size="small" class="mt-3">
              {{ $t('user.changeAvatar') }}
            </el-button>
          </el-upload>
        </div>
        
        <el-divider />
        
        <el-form 
          ref="profileForm" 
          :model="formData" 
          :rules="rules" 
          label-position="top" 
          class="profile-form"
        >
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item :label="$t('user.username')" prop="username">
                <el-input v-model="formData.username" disabled />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="$t('user.email')" prop="email">
                <el-input v-model="formData.email" />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-divider>{{ $t('user.changePassword') }}</el-divider>
          
          <el-row :gutter="20">
            <el-col :span="24">
              <el-form-item :label="$t('user.currentPassword')" prop="currentPassword">
                <el-input 
                  v-model="formData.currentPassword" 
                  type="password" 
                  show-password
                  :placeholder="$t('user.currentPasswordPlaceholder')"
                />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item :label="$t('user.newPassword')" prop="newPassword">
                <el-input 
                  v-model="formData.newPassword" 
                  type="password" 
                  show-password
                  :placeholder="$t('user.newPasswordPlaceholder')"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="$t('user.confirmNewPassword')" prop="confirmPassword">
                <el-input 
                  v-model="formData.confirmPassword" 
                  type="password" 
                  show-password
                  :placeholder="$t('user.confirmPasswordPlaceholder')"
                />
              </el-form-item>
            </el-col>
          </el-row>
          
          <div class="form-actions">
            <el-button type="primary" @click="saveProfile" :loading="loading">
              {{ $t('user.saveChanges') }}
            </el-button>
          </div>
        </el-form>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import api from '../api/api';

export default {
  name: 'UserProfile',
  
  setup() {
    const profileForm = ref(null);
    const loading = ref(false);
    
    // 用户数据
    const formData = reactive({
      username: '',
      email: '',
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    });
    
    const userAvatar = ref('');
    const userInitials = computed(() => {
      if (!formData.username) return '';
      return formData.username.charAt(0).toUpperCase();
    });
    
    // 表单验证规则
    const validatePass = (rule, value, callback) => {
      if (value === '') {
        callback();
      } else if (value.length < 6) {
        callback(new Error('密码长度不能少于6个字符'));
      } else {
        if (formData.confirmPassword !== '') {
          profileForm.value.validateField('confirmPassword');
        }
        callback();
      }
    };
    
    const validateConfirmPass = (rule, value, callback) => {
      if (value === '') {
        callback();
      } else if (value !== formData.newPassword) {
        callback(new Error('两次输入密码不一致'));
      } else {
        callback();
      }
    };
    
    const rules = {
      email: [
        { required: true, message: '请输入邮箱地址', trigger: 'blur' },
        { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
      ],
      currentPassword: [
        { required: false, message: '请输入当前密码', trigger: 'blur' }
      ],
      newPassword: [
        { validator: validatePass, trigger: 'blur' }
      ],
      confirmPassword: [
        { validator: validateConfirmPass, trigger: 'blur' }
      ]
    };
    
    // 加载用户资料
    const loadUserProfile = async () => {
      try {
        const userData = await api.getUserProfile();
        formData.username = userData.username || '';
        formData.email = userData.email || '';
        userAvatar.value = userData.avatar || '';
      } catch (error) {
        ElMessage.error('获取用户资料失败');
        console.error(error);
      }
    };
    
    // 添加头像处理函数
    const handleAvatarChange = async (file) => {
      try {
        // 读取文件并转换为Base64
        const reader = new FileReader();
        reader.onload = async (e) => {
          try {
            loading.value = true;
            const base64Data = e.target.result;
            // 上传头像
            const response = await api.uploadAvatar(base64Data);
            userAvatar.value = response.avatar;
            ElMessage.success('头像更新成功');
          } catch (error) {
            ElMessage.error('更新头像失败: ' + (error.message || '未知错误'));
            console.error(error);
          } finally {
            loading.value = false;
          }
        };
        reader.readAsDataURL(file.raw);
      } catch (error) {
        ElMessage.error('处理头像失败: ' + (error.message || '未知错误'));
        console.error(error);
      }
    };
    
    // 保存用户资料
    const saveProfile = async () => {
      if (!profileForm.value) return;
      
      await profileForm.value.validate(async (valid) => {
        if (valid) {
          try {
            loading.value = true;
            
            const updateData = {
              email: formData.email
            };
            
            // 如果用户输入了密码，则更新密码
            if (formData.currentPassword && formData.newPassword) {
              updateData.currentPassword = formData.currentPassword;
              updateData.password = formData.newPassword;
            }
            
            await api.updateUserProfile(updateData);
            
            loading.value = false;
            ElMessage.success('个人资料更新成功');
            
            // 清空密码字段
            formData.currentPassword = '';
            formData.newPassword = '';
            formData.confirmPassword = '';
          } catch (error) {
            loading.value = false;
            ElMessage.error('更新个人资料失败: ' + (error.message || '未知错误'));
            console.error(error);
          }
        }
      });
    };
    
    onMounted(() => {
      loadUserProfile();
    });
    
    return {
      profileForm,
      formData,
      rules,
      loading,
      userAvatar,
      userInitials,
      saveProfile,
      handleAvatarChange
    };
  }
};
</script>

<style scoped>
.user-profile-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.profile-card {
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

.profile-content {
  padding: 10px 0;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 20px;
}

.mt-3 {
  margin-top: 12px;
}

.form-actions {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .user-profile-container {
    padding: 10px;
  }
}
</style> 