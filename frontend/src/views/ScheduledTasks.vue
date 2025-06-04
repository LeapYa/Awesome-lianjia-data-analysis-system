<template>
  <div class="container">
    <el-card class="task-card">
      <div class="card-header">
        <h2>{{ $t('scheduledTasks.title') }}</h2>
        <el-button type="primary" @click="showTaskDialog(null)">
          <el-icon><Plus /></el-icon> {{ $t('scheduledTasks.createTask') }}
        </el-button>
      </div>

      <el-table :data="tasks" v-loading="loading" style="width: 100%">
        <!-- 表格列 -->
        <el-table-column prop="name" :label="$t('scheduledTasks.taskName')" min-width="140" />
        <el-table-column prop="city" :label="$t('scheduledTasks.city')" min-width="100" />
        
        <el-table-column :label="$t('scheduledTasks.schedule')" min-width="180">
          <template #default="scope">
            {{ formatSchedule(scope.row.schedule, scope.row.time) }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('scheduledTasks.nextRun')" min-width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.next_run) }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('scheduledTasks.status')" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('scheduledTasks.actions')" width="150" fixed="right">
          <template #default="scope">
            <el-button-group>
              <el-button 
                type="primary" 
                plain 
                size="small" 
                @click="showTaskDialog(scope.row)"
                :disabled="scope.row.status === '执行中'"
              >
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button 
                type="danger" 
                plain 
                size="small" 
                @click="confirmDelete(scope.row)"
                :disabled="scope.row.status === '执行中'"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 任务对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? $t('scheduledTasks.editTask') : $t('scheduledTasks.createTask')"
      width="600px"
    >
      <el-form 
        ref="taskFormRef" 
        :model="taskForm" 
        :rules="taskRules" 
        label-position="top"
      >
        <el-form-item :label="$t('scheduledTasks.taskName')" prop="name">
          <el-input v-model="taskForm.name" />
        </el-form-item>

        <el-form-item :label="$t('scheduledTasks.city')" prop="city">
          <el-select 
            v-model="taskForm.city" 
            filterable 
            :placeholder="$t('scheduledTasks.selectCity')"
            style="width: 100%"
          >
            <el-option
              v-for="city in cityOptions"
              :key="city.value"
              :label="city.label"
              :value="city.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('scheduledTasks.pagesToCrawl')" prop="pages">
          <el-input-number 
            v-model="taskForm.pages" 
            :min="1" 
            :max="100" 
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item :label="$t('scheduledTasks.schedule')" prop="schedule">
          <el-select 
            v-model="taskForm.scheduleType" 
            style="width: 100%"
            @change="handleScheduleTypeChange"
          >
            <el-option
              v-for="option in scheduleOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>

        <!-- 周几选择（仅在每周模式下显示） -->
        <el-form-item 
          v-if="taskForm.scheduleType === 'weekly'" 
          :label="$t('scheduledTasks.weekday')" 
          prop="weekday"
        >
          <el-select v-model="taskForm.weekday" style="width: 100%">
            <el-option
              v-for="(day, index) in weekdayOptions"
              :key="index"
              :label="day"
              :value="index"
            />
          </el-select>
        </el-form-item>

        <!-- 月份日期选择（仅在每月模式下显示） -->
        <el-form-item 
          v-if="taskForm.scheduleType === 'monthly'" 
          :label="$t('scheduledTasks.monthDay')" 
          prop="monthDay"
        >
          <el-select v-model="taskForm.monthDay" style="width: 100%">
            <el-option
              v-for="day in 31"
              :key="day"
              :label="day"
              :value="day"
            />
          </el-select>
        </el-form-item>

        <!-- 运行时间选择 -->
        <el-form-item :label="$t('scheduledTasks.runTime')" prop="time">
          <el-time-picker
            v-model="taskForm.time"
            format="HH:mm"
            value-format="HH:mm"
            style="width: 100%"
          />
        </el-form-item>

        <!-- 任务状态（仅编辑时显示） -->
        <el-form-item v-if="isEdit" :label="$t('scheduledTasks.status')" prop="status">
          <el-select v-model="taskForm.status" style="width: 100%">
            <el-option label="正常" value="正常" />
            <el-option label="暂停" value="暂停" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">{{ $t('scheduledTasks.cancel') }}</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitting">
            {{ $t('scheduledTasks.confirm') }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue';
import { Plus, Edit, Delete } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useI18n } from 'vue-i18n';
import api from '../api/api';

export default {
  name: 'ScheduledTasks',
  components: {
    Plus,
    Edit,
    Delete,
  },
  setup() {
    const { t } = useI18n();
    const loading = ref(false);
    const submitting = ref(false);
    const dialogVisible = ref(false);
    const isEdit = ref(false);
    const tasks = ref([]);
    const currentPage = ref(1);
    const pageSize = ref(10);
    const total = ref(0);
    const taskFormRef = ref(null);
    const cityOptions = ref([]);
    
    // 调度选项
    const scheduleOptions = [
      { value: 'daily', label: t('scheduledTasks.daily') },
      { value: 'weekly', label: t('scheduledTasks.weekly') },
      { value: 'monthly', label: t('scheduledTasks.monthly') }
    ];

    // 周几选项
    const weekdayOptions = [
      t('scheduledTasks.sunday'),
      t('scheduledTasks.monday'),
      t('scheduledTasks.tuesday'),
      t('scheduledTasks.wednesday'),
      t('scheduledTasks.thursday'), 
      t('scheduledTasks.friday'),
      t('scheduledTasks.saturday')
    ];

    // 任务表单
    const taskForm = reactive({
      id: null,
      name: '',
      city: '',
      pages: 5,
      scheduleType: 'daily',
      weekday: 1, // 默认周一
      monthDay: 1, // 默认每月1号
      time: '09:00',
      status: '正常'
    });

    // 表单验证规则
    const taskRules = {
      name: [
        { required: true, message: t('scheduledTasks.nameRequired'), trigger: 'blur' },
        { min: 2, max: 100, message: t('scheduledTasks.nameLength'), trigger: 'blur' }
      ],
      city: [
        { required: true, message: t('scheduledTasks.cityRequired'), trigger: 'change' }
      ],
      pages: [
        { required: true, message: t('scheduledTasks.pagesRequired'), trigger: 'blur' },
        { type: 'number', min: 1, max: 100, message: t('scheduledTasks.pagesRange'), trigger: 'blur' }
      ],
      time: [
        { required: true, message: t('scheduledTasks.timeRequired'), trigger: 'change' }
      ]
    };

    // 获取城市列表
    const fetchCities = async () => {
      try {
        const response = await api.getCities();
        console.log('城市数据:', response);
        
        // 后端返回的是 Dict[str, str] 格式 (城市名: 城市代码)
        // 由于可能存在编码问题，手动处理城市数据
        const cityData = response;
        const cities = [];
        
        if (typeof cityData === 'object' && cityData !== null) {
          // 遍历所有城市数据
          for (const [name, code] of Object.entries(cityData)) {
            cities.push({
              value: name, 
              label: name,
              code: code
            });
          }
        }
        
        if (cities.length > 0) {
          cityOptions.value = cities;
          console.log('成功获取城市列表，共', cities.length, '个城市');
        } else {
          throw new Error('城市数据格式不正确');
        }
      } catch (error) {
        console.error('获取城市列表失败:', error);
        // 使用模拟数据
        cityOptions.value = [
          { value: '北京', label: '北京', code: 'bj' },
          { value: '上海', label: '上海', code: 'sh' },
          { value: '广州', label: '广州', code: 'gz' },
          { value: '深圳', label: '深圳', code: 'sz' },
          { value: '杭州', label: '杭州', code: 'hz' },
          { value: '南京', label: '南京', code: 'nj' },
          { value: '武汉', label: '武汉', code: 'wh' },
          { value: '成都', label: '成都', code: 'cd' }
        ];
        ElMessage.warning('使用模拟城市数据');
      }
    };

    // 获取任务列表
    const fetchTasks = async () => {
      loading.value = true;
      try {
        // 确保已登录
        const token = localStorage.getItem('token');
        if (!token) {
          await ensureLoggedIn();
        }
        
        console.log('开始获取定时任务列表...');
        
        const response = await api.getScheduledTasks({
          limit: pageSize.value,
          offset: (currentPage.value - 1) * pageSize.value
        });
        
        console.log('定时任务API响应:', response);

        // API可能返回不同的数据结构，进行兼容处理
        let taskData;
        if (response && Array.isArray(response)) {
          taskData = response;
        } else if (response && Array.isArray(response.data)) {
          taskData = response.data;
        } else if (response && response.data && Array.isArray(response.data.items)) {
          taskData = response.data.items;
          total.value = response.data.total || taskData.length;
        } else {
          console.warn('无法识别的任务数据格式:', response);
          taskData = [];
        }
        
        tasks.value = taskData;
        if (total.value === 0) {
          total.value = taskData.length > 0 ? (currentPage.value - 1) * pageSize.value + taskData.length : 0;
        }
        
        console.log('获取到的定时任务:', taskData);
      } catch (error) {
        console.error('获取定时任务列表失败:', error);
        if (error.status === 401 || error.status === 403) {
          ElMessage.error('登录失效，请重新登录');
          await ensureLoggedIn();
          // 重试一次
          try {
            const response = await api.getScheduledTasks({
              limit: pageSize.value,
              offset: (currentPage.value - 1) * pageSize.value
            });
            tasks.value = Array.isArray(response) ? response : 
                         (Array.isArray(response.data) ? response.data : []);
            console.log('重试获取任务成功');
          } catch (retryError) {
            console.error('重试获取任务仍然失败:', retryError);
            // 使用模拟数据
            useMockTasks();
          }
        } else {
          // 其他错误，使用模拟数据
          useMockTasks();
        }
      } finally {
        loading.value = false;
      }
    };
    
    // 使用模拟任务数据
    const useMockTasks = () => {
      const mockTasks = [
        {
          id: 1,
          name: '北京每日爬取',
          city: '北京',
          pages: 10,
          schedule: 'daily',
          time: '09:00',
          next_run: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          status: '正常',
          created_at: new Date().toISOString()
        },
        {
          id: 2,
          name: '上海周一爬取',
          city: '上海',
          pages: 5,
          schedule: 'weekly|1',
          time: '10:00',
          next_run: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
          status: '正常',
          created_at: new Date().toISOString()
        },
        {
          id: 3,
          name: '广州月初爬取',
          city: '广州',
          pages: 20,
          schedule: 'monthly|1',
          time: '08:30',
          next_run: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString(),
          status: '暂停',
          created_at: new Date().toISOString()
        }
      ];
      tasks.value = mockTasks;
      total.value = mockTasks.length;
      ElMessage.warning('使用模拟任务数据');
    };

    // 处理页码变化
    const handleCurrentChange = (page) => {
      currentPage.value = page;
      fetchTasks();
    };

    // 处理每页数量变化
    const handleSizeChange = (size) => {
      pageSize.value = size;
      currentPage.value = 1;
      fetchTasks();
    };

    // 显示任务对话框
    const showTaskDialog = (task) => {
      resetForm();
      if (task) {
        isEdit.value = true;
        
        // 解析schedule字段
        const [scheduleType, value] = task.schedule.split('|');
        
        taskForm.id = task.id;
        taskForm.name = task.name;
        taskForm.city = task.city;
        taskForm.pages = task.pages;
        taskForm.scheduleType = scheduleType;
        taskForm.time = task.time || '09:00';
        taskForm.status = task.status;
        
        if (scheduleType === 'weekly' && value) {
          taskForm.weekday = parseInt(value);
        } else if (scheduleType === 'monthly' && value) {
          taskForm.monthDay = parseInt(value);
        }
      } else {
        isEdit.value = false;
      }
      dialogVisible.value = true;
    };

    // 重置表单
    const resetForm = () => {
      taskForm.id = null;
      taskForm.name = '';
      taskForm.city = '';
      taskForm.pages = 5;
      taskForm.scheduleType = 'daily';
      taskForm.weekday = 1;
      taskForm.monthDay = 1;
      taskForm.time = '09:00';
      taskForm.status = '正常';
      
      if (taskFormRef.value) {
        taskFormRef.value.resetFields();
      }
    };

    // 处理调度类型变化
    const handleScheduleTypeChange = () => {
      // 什么都不做，只是触发视图更新
    };

    // 格式化调度信息
    const formatSchedule = (schedule, time) => {
      if (!schedule) return '-';
      
      const [type, value] = schedule.split('|');
      let text = '';
      
      switch (type) {
        case 'daily':
          text = t('scheduledTasks.everyDayAt', { time: time || '00:00' });
          break;
        case 'weekly':
          if (value !== undefined) {
            const weekdayIndex = parseInt(value);
            text = t('scheduledTasks.everyWeekAt', { day: weekdayOptions[weekdayIndex], time: time || '00:00' });
          }
          break;
        case 'monthly':
          if (value !== undefined) {
            text = t('scheduledTasks.everyMonthAt', { day: value, time: time || '00:00' });
          }
          break;
        default:
          text = schedule;
      }
      
      return text;
    };

    // 格式化日期时间
    const formatDateTime = (dateTime) => {
      if (!dateTime) return '-';
      
      const date = new Date(dateTime);
      return new Intl.DateTimeFormat('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      }).format(date);
    };

    // 获取状态类型（用于tag的颜色）
    const getStatusType = (status) => {
      switch (status) {
        case '正常':
          return 'success';
        case '暂停':
          return 'info';
        case '执行中':
          return 'warning';
        case '错误':
          return 'danger';
        default:
          return '';
      }
    };

    // 确认删除任务
    const confirmDelete = (task) => {
      ElMessageBox.confirm(
        t('scheduledTasks.confirmDeleteTask', { name: task.name }),
        t('scheduledTasks.warning'),
        {
          confirmButtonText: t('scheduledTasks.confirm'),
          cancelButtonText: t('scheduledTasks.cancel'),
          type: 'warning'
        }
      )
        .then(() => {
          deleteTask(task.id);
        })
        .catch(() => {
          // 用户取消删除操作
        });
    };

    // 删除任务
    const deleteTask = async (id) => {
      try {
        await api.deleteScheduledTask(id);
        ElMessage.success(t('scheduledTasks.deleteSuccess'));
        fetchTasks();
      } catch (error) {
        console.error('删除定时任务失败:', error);
        ElMessage.error(t('scheduledTasks.deleteError'));
      }
    };

    // 提交表单
    const submitForm = async () => {
      if (!taskFormRef.value) return;
      
      await taskFormRef.value.validate(async (valid) => {
        if (valid) {
          submitting.value = true;
          
          try {
            // 构建schedule参数
            let scheduleValue = '';
            if (taskForm.scheduleType === 'weekly') {
              scheduleValue = `${taskForm.scheduleType}|${taskForm.weekday}`;
            } else if (taskForm.scheduleType === 'monthly') {
              scheduleValue = `${taskForm.scheduleType}|${taskForm.monthDay}`;
            } else {
              scheduleValue = taskForm.scheduleType;
            }
            
            const taskData = {
              name: taskForm.name,
              city: taskForm.city,
              pages: taskForm.pages,
              schedule: scheduleValue,
              time: taskForm.time
            };
            
            if (isEdit.value) {
              // 更新任务
              if (taskForm.status) {
                taskData.status = taskForm.status;
              }
              await api.updateScheduledTask(taskForm.id, taskData);
              ElMessage.success(t('scheduledTasks.updateSuccess'));
            } else {
              // 创建任务
              await api.createScheduledTask(taskData);
              ElMessage.success(t('scheduledTasks.createSuccess'));
            }
            
            dialogVisible.value = false;
            fetchTasks();
          } catch (error) {
            console.error('保存定时任务失败:', error);
            ElMessage.error(t('scheduledTasks.saveError'));
          } finally {
            submitting.value = false;
          }
        }
      });
    };

    // 组件挂载时获取数据
    onMounted(async () => {
      await ensureLoggedIn();
      fetchCities();
      fetchTasks();
    });

    // 临时：确保用户已登录
    const ensureLoggedIn = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          console.log('未找到token');
          ElMessage.error('未找到token，请重新登录');
        } else {
          console.log('已有token，尝试验证是否有效...');
          try {
            // 尝试验证token是否有效
            await api.checkAuthStatus();
            console.log('token有效');
          } catch (authError) {
            console.error('token无效，尝试重新登录:', authError);
            localStorage.removeItem('token');
            // 递归调用，重新登录
            return await ensureLoggedIn();
          }
        }
      } catch (error) {
        console.error('确保登录状态失败:', error);
        ElMessage.error('登录失败，请确认网络连接并检查API服务是否正常运行');
        throw error;
      }
    };

    return {
      loading,
      submitting,
      dialogVisible,
      isEdit,
      tasks,
      currentPage,
      pageSize,
      total,
      cityOptions,
      scheduleOptions,
      weekdayOptions,
      taskForm,
      taskFormRef,
      taskRules,
      handleCurrentChange,
      handleSizeChange,
      showTaskDialog,
      handleScheduleTypeChange,
      formatSchedule,
      formatDateTime,
      getStatusType,
      confirmDelete,
      submitForm
    };
  }
};
</script>

<style scoped>
.container {
  padding: 20px;
}

.task-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style> 