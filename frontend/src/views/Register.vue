<template>
  <div class="register-container">
    <div class="register-card">
      <div class="card-header">
        <h2>{{ $t('auth.registerTitle') }}</h2>
        <p>{{ $t('auth.registerSubtitle') }}</p>
      </div>

      <el-form ref="registerForm" :model="formData" :rules="rules" class="register-form" @submit.prevent="handleRegister">
        <el-form-item prop="username">
          <el-input 
            v-model="formData.username" 
            :placeholder="$t('auth.username')"
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        
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
        
        <el-form-item prop="password">
          <el-input 
            v-model="formData.password" 
            :placeholder="$t('auth.password')" 
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
            :placeholder="$t('auth.confirmPassword')" 
            type="password" 
            show-password
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        
        <div class="form-actions">
          <el-checkbox v-model="formData.agreement">
            {{ $t('auth.agreeTerms') }} <a href="#" class="terms-link">{{ $t('auth.termsLink') }}</a>
          </el-checkbox>
        </div>
        
        <el-form-item>
          <el-button type="primary" class="submit-btn" native-type="submit" :loading="loading">
            {{ $t('auth.register') }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="card-footer">
        <p>{{ $t('auth.haveAccount') }} <router-link to="/login">{{ $t('auth.login') }}</router-link></p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { User, Lock, Message } from '@element-plus/icons-vue';
import api from '../api/api';

export default {
  name: 'RegisterView',
  
  components: {
    User,
    Lock,
    Message
  },
  
  setup() {
    const router = useRouter();
    const registerForm = ref(null);
    const loading = ref(false);
    
    const formData = reactive({
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      agreement: false
    });
    
    const validatePass = (rule, value, callback) => {
      if (value === '') {
        callback(new Error('请输入密码'));
      } else {
        if (formData.confirmPassword !== '') {
          registerForm.value.validateField('confirmPassword');
        }
        callback();
      }
    };
    
    const validateConfirmPass = (rule, value, callback) => {
      if (value === '') {
        callback(new Error('请再次输入密码'));
      } else if (value !== formData.password) {
        callback(new Error('两次输入密码不一致'));
      } else {
        callback();
      }
    };
    
    const validateAgreement = (rule, value, callback) => {
      if (!value) {
        callback(new Error('请阅读并同意用户协议'));
      } else {
        callback();
      }
    };
    
    const rules = {
      username: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { min: 3, max: 20, message: '用户名长度应为3-20个字符', trigger: 'blur' }
      ],
      email: [
        { required: true, message: '请输入邮箱地址', trigger: 'blur' },
        { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
      ],
      password: [
        { required: true, validator: validatePass, trigger: 'blur' },
        { min: 6, max: 20, message: '密码长度应为6-20个字符', trigger: 'blur' }
      ],
      confirmPassword: [
        { required: true, validator: validateConfirmPass, trigger: 'blur' }
      ],
      agreement: [
        { required: true, validator: validateAgreement, trigger: 'change' }
      ]
    };
    
    const handleRegister = async () => {
      if (!registerForm.value) return;
      
      await registerForm.value.validate(async (valid) => {
        if (valid) {
          try {
            loading.value = true;
            
            // 调用注册API
            const data = {
              username: formData.username,
              email: formData.email,
              password: formData.password
            };
            
            await api.register(data);
            
            loading.value = false;
            ElMessage.success('注册成功，请登录');
            
            // 注册成功后跳转到登录页
            router.push({ path: '/login' });
          } catch (error) {
            loading.value = false;
            ElMessage.error('注册失败：' + (error.message || '未知错误'));
            console.error(error);
          }
        }
      });
    };
    
    return {
      registerForm,
      formData,
      rules,
      loading,
      handleRegister
    };
  }
};
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 140px);
  padding: 20px;
  background-color: #f9fafb;
}

.register-card {
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

.register-form {
  padding: 0 24px;
}

.form-actions {
  margin-bottom: 24px;
}

.terms-link {
  color: #0051c3;
  text-decoration: none;
}

.terms-link:hover {
  text-decoration: underline;
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