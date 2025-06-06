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

        <el-form-item prop="verificationCode">
          <div class="verification-input-group">
            <el-input 
              v-model="formData.verificationCode" 
              :placeholder="$t('auth.verificationCode')"
              maxlength="6"
              class="verification-code-input"
            >
              <template #prefix>
                <el-icon><Key /></el-icon>
              </template>
            </el-input>
            <el-button 
              type="primary" 
              @click="sendVerificationCode" 
              :loading="sendingCode"
              :disabled="!formData.email || sendingCode || resendDisabled"
              class="send-code-btn"
            >
              {{ resendDisabled ? `${resendCountdown}s` : $t('auth.sendVerificationCode') }}
            </el-button>
          </div>
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
import { User, Lock, Message, Key } from '@element-plus/icons-vue';
import api from '../api/api';

export default {
  name: 'RegisterView',
  
  components: {
    User,
    Lock,
    Message,
    Key
  },
  
  setup() {
    const router = useRouter();
    const registerForm = ref(null);
    const loading = ref(false);
    const sendingCode = ref(false);
    const resendDisabled = ref(false);
    const resendCountdown = ref(0);
    
    const formData = reactive({
      username: '',
      email: '',
      verificationCode: '',
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
      verificationCode: [
        { required: true, message: '请输入验证码', trigger: 'blur' },
        { len: 6, message: '验证码为6位数字', trigger: 'blur' }
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

    // 发送验证码
    const sendVerificationCode = async () => {
      if (!formData.email) {
        ElMessage.warning('请先输入邮箱地址');
        return;
      }

      // 验证邮箱格式
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.email)) {
        ElMessage.warning('请输入正确的邮箱地址');
        return;
      }

      try {
        sendingCode.value = true;
        
        await api.sendVerificationCode({
          email: formData.email,
          code_type: 'email_verification'
        });
        
        ElMessage.success('验证码已发送，请查收邮件');
        
        // 开始倒计时
        startResendCountdown();
        
      } catch (error) {
        ElMessage.error('发送验证码失败：' + (error.message || '未知错误'));
      } finally {
        sendingCode.value = false;
      }
    };

    // 倒计时逻辑
    const startResendCountdown = () => {
      resendDisabled.value = true;
      resendCountdown.value = 60;
      
      const timer = setInterval(() => {
        resendCountdown.value--;
        
        if (resendCountdown.value <= 0) {
          clearInterval(timer);
          resendDisabled.value = false;
        }
      }, 1000);
    };
    
    const handleRegister = async () => {
      if (!registerForm.value) return;
      
      await registerForm.value.validate(async (valid) => {
        if (valid) {
          try {
            loading.value = true;
            
            const data = {
              username: formData.username,
              email: formData.email,
              password: formData.password,
              verification_code: formData.verificationCode
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
      sendingCode,
      resendDisabled,
      resendCountdown,
      sendVerificationCode,
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

.verification-input-group {
  display: flex;
  gap: 8px;
}

.verification-code-input {
  flex: 1;
}

.send-code-btn {
  min-width: 120px;
  font-size: 12px;
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