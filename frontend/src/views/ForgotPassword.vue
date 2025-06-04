<template>
  <div class="forgot-password-container">
    <div class="forgot-password-card">
      <div class="card-header">
        <h2>{{ $t('auth.forgotPasswordTitle') }}</h2>
        <p>{{ $t('auth.forgotPasswordSubtitle') }}</p>
      </div>

      <el-form ref="passwordFormRef" :model="formData" :rules="rules" class="forgot-password-form" @submit.prevent="handleSubmit">
        <el-form-item prop="email">
          <el-input 
            v-model="formData.email" 
            :placeholder="$t('auth.email')"
            type="email" 
          >
            <template #prefix>
              <el-icon><Message /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" class="submit-btn" native-type="submit" :loading="loading">
            {{ $t('auth.sendResetLink') }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="card-footer">
        <p>{{ $t('auth.rememberedPassword') }} <router-link to="/login">{{ $t('auth.login') }}</router-link></p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Message } from '@element-plus/icons-vue';
import api from '../api/api';

export default {
  name: 'ForgotPasswordView',
  
  components: {
    Message
  },
  
  setup() {
    const router = useRouter();
    const passwordFormRef = ref(null);
    const loading = ref(false);
    
    const formData = reactive({
      email: ''
    });
    
    const rules = {
      email: [
        { required: true, message: '请输入邮箱地址', trigger: 'blur' },
        { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
      ]
    };
    
    const handleSubmit = async () => {
      if (!passwordFormRef.value) return;
      
      await passwordFormRef.value.validate(async (valid) => {
        if (valid) {
          try {
            loading.value = true;
            
            // 调用忘记密码API
            const data = {
              email: formData.email
            };
            
            await api.forgotPassword(data);
            
            loading.value = false;
            ElMessage.success('密码重置链接已发送到您的邮箱');
            
            // 成功后跳转到登录页
            router.push({ path: '/login' });
          } catch (error) {
            loading.value = false;
            ElMessage.error('发送失败：' + (error.message || '未知错误'));
            console.error(error);
          }
        }
      });
    };
    
    return {
      passwordFormRef,
      formData,
      rules,
      loading,
      handleSubmit
    };
  }
};
</script>

<style scoped>
.forgot-password-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 140px);
  padding: 20px;
  background-color: #f9fafb;
}

.forgot-password-card {
  width: 100%;
  max-width: 400px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.card-header {
  padding: 24px 24px 0;
  text-align: center;
}

.card-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 8px;
}

.card-header p {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 24px;
}

.forgot-password-form {
  padding: 0 24px;
}

.submit-btn {
  width: 100%;
  padding: 12px;
  font-size: 16px;
  font-weight: 500;
}

.card-footer {
  margin-top: 16px;
  padding: 16px 24px;
  text-align: center;
  border-top: 1px solid #e5e7eb;
  background-color: #f9fafb;
}

.card-footer p {
  font-size: 14px;
  color: #6b7280;
}

.card-footer a {
  color: #0051c3;
  text-decoration: none;
  font-weight: 500;
}

.card-footer a:hover {
  text-decoration: underline;
}
</style> 