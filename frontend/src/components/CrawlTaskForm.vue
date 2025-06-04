<template>
  <div class="crawl-task-form">
    <el-card class="task-card">
      <template #header>
        <div class="card-header">
          <h3>{{ $t('home.createTask') }}</h3>
        </div>
      </template>
      
      <el-form :model="form" label-width="120px" :rules="rules" ref="taskForm">
        <el-form-item :label="$t('home.city')" prop="city">
          <el-select v-model="form.city" :placeholder="$t('home.selectCity')" style="width: 100%">
            <el-option
              v-for="(code, name) in cities"
              :key="name"
              :label="name"
              :value="name"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item :label="$t('home.crawlPages')" prop="maxPages">
          <el-input-number v-model="form.maxPages" :min="1" :max="50" style="width: 100%" />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="submitForm" :loading="loading">{{ $t('home.startCrawling') }}</el-button>
          <el-button @click="resetForm">{{ $t('home.reset') }}</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import api from '../api/api';

export default {
  name: 'CrawlTaskForm',
  emits: ['task-created'],
  
  setup(props, { emit }) {
    const { t } = useI18n();
    
    // 表单数据
    const form = reactive({
      city: '',
      maxPages: 5
    });
    
    // 表单验证规则
    const rules = reactive({
      city: [
        { required: true, message: t('home.selectCity'), trigger: 'change' }
      ],
      maxPages: [
        { required: true, message: t('home.请设置爬取页数'), trigger: 'blur' }
      ]
    });
    
    // 城市列表
    const cities = ref({});
    
    // 表单引用
    const taskForm = ref(null);
    
    // 加载状态
    const loading = ref(false);
    
    // 获取城市列表
    const getCities = async () => {
      try {
        cities.value = await api.getCities();
      } catch (error) {
        ElMessage.error(t('home.fetchCitiesFailed'));
        console.error(error);
      }
    };
    
    // 提交表单
    const submitForm = async () => {
      if (!taskForm.value) return;
      
      await taskForm.value.validate(async (valid) => {
        if (valid) {
          try {
            loading.value = true;
            
            const data = {
              city: form.city,
              max_pages: form.maxPages
            };
            
            const result = await api.createCrawlTask(data);
            
            loading.value = false;
            ElMessage.success(t('home.爬虫任务创建成功'));
            
            // 通知父组件任务已创建
            emit('task-created', result);
            
            // 重置表单
            resetForm();
          } catch (error) {
            loading.value = false;
            ElMessage.error(t('home.taskCreateFailed'));
            console.error(error);
          }
        }
      });
    };
    
    // 重置表单
    const resetForm = () => {
      if (taskForm.value) {
        taskForm.value.resetFields();
      }
    };
    
    // 组件挂载时获取城市列表
    onMounted(() => {
      getCities();
    });
    
    return {
      form,
      rules,
      cities,
      taskForm,
      loading,
      submitForm,
      resetForm
    };
  }
};
</script>

<style scoped>
.crawl-task-form {
  margin-bottom: 24px;
}

.task-card {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  border: 1px solid #eaeaea;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  font-size: 16px;
  font-weight: 500;
  color: #333;
  margin: 0;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #444;
}

:deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #2c7be5 inset;
}

:deep(.el-select .el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px #2c7be5 inset;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-input-number .el-input__wrapper) {
  padding-right: 0;
}

:deep(.el-button--primary) {
  background-color: #2c7be5;
  border-color: #2c7be5;
  height: 36px;
  border-radius: 4px;
}

:deep(.el-button--primary:hover),
:deep(.el-button--primary:focus) {
  background-color: #1a68d1;
  border-color: #1a68d1;
}

:deep(.el-button--default) {
  border-color: #dcdfe6;
  color: #606266;
  height: 36px;
  border-radius: 4px;
}

:deep(.el-button--default:hover),
:deep(.el-button--default:focus) {
  color: #2c7be5;
  border-color: #c6e2ff;
  background-color: #ecf5ff;
}

:deep(.el-form-item:last-child) {
  margin-bottom: 0;
}
</style> 