<template>
  <div class="login-container">
    <div class="login-card">
      <div class="card-header">
        <h2>{{ $t('auth.loginTitle') }}</h2>
        <p>{{ $t('auth.loginSubtitle') }}</p>
      </div>

      <el-form ref="loginForm" :model="formData" :rules="rules" class="login-form" @submit.prevent="handleLogin">
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
        
        <div class="form-actions">
          <el-checkbox v-model="formData.remember">{{ $t('auth.rememberMe') }}</el-checkbox>
          <router-link to="/forgot-password" class="forgot-link">{{ $t('auth.forgotPassword') }}</router-link>
        </div>
        
        <el-form-item>
          <el-button type="primary" class="submit-btn" native-type="submit" :loading="loading">
            {{ $t('auth.login') }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="card-footer">
        <p>{{ $t('auth.noAccount') }} <router-link to="/register">{{ $t('auth.register') }}</router-link></p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { User, Lock } from '@element-plus/icons-vue';
import api from '../api/api';

export default {
  name: 'LoginView',
  
  components: {
    User,
    Lock
  },
  
  setup() {
    const router = useRouter();
    const loginForm = ref(null);
    const loading = ref(false);
    
    const formData = reactive({
      username: '',
      password: '',
      remember: false
    });
    
    const rules = {
      username: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { min: 3, max: 20, message: '用户名长度应为3-20个字符', trigger: 'blur' }
      ],
      password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 6, max: 20, message: '密码长度应为6-20个字符', trigger: 'blur' }
      ]
    };
    
    const handleLogin = async () => {
      if (!loginForm.value) return;
      
      await loginForm.value.validate(async (valid) => {
        if (valid) {
          try {
            loading.value = true;
            
            // 调用登录API
            const data = {
              username: formData.username,
              password: formData.password
            };
            
            const result = await api.login(data);
            
            // 存储登录状态和token
            localStorage.setItem('token', result.token);
            localStorage.setItem('user', JSON.stringify(result.user));
            
            loading.value = false;
            ElMessage.success('登录成功');
            
            // 登录成功后跳转到首页
            router.push({ path: '/' });
          } catch (error) {
            loading.value = false;
            ElMessage.error('登录失败：' + (error.message || '未知错误'));
            console.error(error);
          }
        }
      });
    };
    
    return {
      loginForm,
      formData,
      rules,
      loading,
      handleLogin
    };
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 140px);
  padding: 20px;
  background-color: #f9fafb;
}

.login-card {
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

.login-form {
  padding: 0 24px;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.forgot-link {
  font-size: 14px;
  color: #0051c3;
  text-decoration: none;
}

.forgot-link:hover {
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