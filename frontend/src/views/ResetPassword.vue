<template>
  <div class="reset-password-container">
    <div class="reset-password-card">
      <div class="card-header">
        <h2>{{ $t('auth.resetPasswordTitle') }}</h2>
        <p>{{ $t('auth.resetPasswordSubtitle') }}</p>
      </div>

      <el-form 
        ref="resetFormRef" 
        :model="formData" 
        :rules="rules" 
        class="reset-password-form" 
        @submit.prevent="handleSubmit"
      >
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

        <el-form-item prop="code">
          <el-input 
            v-model="formData.code" 
            :placeholder="$t('auth.verificationCode')"
            maxlength="6"
            show-word-limit
          >
            <template #prefix>
              <el-icon><Key /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input 
            v-model="formData.password" 
            :placeholder="$t('auth.newPassword')"
            type="password" 
            show-password
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="confirmPassword">
          <el-input 
            v-model="formData.confirmPassword" 
            :placeholder="$t('auth.confirmNewPassword')"
            type="password" 
            show-password
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" class="submit-btn" native-type="submit" :loading="loading">
            {{ $t('auth.resetPassword') }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="card-footer">
        <p>{{ $t('auth.rememberedPassword') }} <router-link to="/login">{{ $t('auth.login') }}</router-link></p>
        <p><router-link to="/forgot-password">{{ $t('auth.resendCode') }}</router-link></p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Message, Lock, Key } from '@element-plus/icons-vue';
import api from '../api/api';

export default {
  name: 'ResetPasswordView',
  
  components: {
    Message,
    Lock,
    Key
  },
  
  setup() {
    const router = useRouter();
    const route = useRoute();
    const resetFormRef = ref(null);
    const loading = ref(false);
    
    const formData = reactive({
      email: '',
      code: '',
      password: '',
      confirmPassword: ''
    });
    
    const rules = {
      email: [
        { required: true, message: '请输入邮箱地址', trigger: 'blur' },
        { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
      ],
      code: [
        { required: true, message: '请输入验证码', trigger: 'blur' },
        { len: 6, message: '验证码必须是6位数字', trigger: 'blur' },
        { pattern: /^\d{6}$/, message: '验证码只能包含数字', trigger: 'blur' }
      ],
      password: [
        { required: true, message: '请输入新密码', trigger: 'blur' },
        { min: 6, message: '密码长度不能少于6位', trigger: 'blur' },
        { max: 50, message: '密码长度不能超过50位', trigger: 'blur' }
      ],
      confirmPassword: [
        { required: true, message: '请确认新密码', trigger: 'blur' },
        { 
          validator: (rule, value, callback) => {
            if (value !== formData.password) {
              callback(new Error('两次输入的密码不一致'));
            } else {
              callback();
            }
          }, 
          trigger: 'blur' 
        }
      ]
    };
    
    const handleSubmit = async () => {
      if (!resetFormRef.value) return;
      
      await resetFormRef.value.validate(async (valid) => {
        if (valid) {
          try {
            loading.value = true;
            
            const data = {
              email: formData.email,
              code: formData.code,
              password: formData.password
            };
            
            await api.resetPassword(data);
            
            loading.value = false;
            ElMessage.success('密码重置成功，请使用新密码登录');
            
            // 成功后跳转到登录页
            router.push({ path: '/login' });
          } catch (error) {
            loading.value = false;
            ElMessage.error('重置失败：' + (error.detail || error.message || '未知错误'));
            console.error(error);
          }
        }
      });
    };

    // 从URL参数中获取邮箱地址
    onMounted(() => {
      if (route.query.email) {
        formData.email = route.query.email;
      }
    });
    
    return {
      resetFormRef,
      formData,
      rules,
      loading,
      handleSubmit
    };
  }
};
</script>

<style scoped>
.reset-password-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 140px);
  padding: 20px;
  background-color: #f9fafb;
}

.reset-password-card {
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

.reset-password-form {
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
  margin-bottom: 8px;
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