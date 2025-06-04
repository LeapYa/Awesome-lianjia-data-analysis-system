<template>
  <div class="task-list">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <h3>{{ t('taskList.title') }}</h3>
          <el-button type="primary" size="small" @click="refreshTasks" :disabled="showCrawlerMask">{{ t('taskList.refresh') }}</el-button>
        </div>
      </template>
      
      <!-- 爬虫任务启动遮罩 -->
      <div v-if="showCrawlerMask" class="crawler-mask">
        <div class="mask-content">
          <el-icon class="loading-icon"><Loading /></el-icon>
          <h3>{{ t('taskList.crawlerRunning') }}</h3>
          <p>{{ t('taskList.waitForCrawler') }}</p>
          <p>{{ t('taskList.remainingTime') }}: {{ remainingSeconds }}秒</p>
          <el-progress :percentage="maskProgressPercentage" :stroke-width="20" style="margin: 15px 0;" />
          <!-- <el-button type="primary" @click="forceDismissMask">{{ t('taskList.viewAnyway') }}</el-button> -->
        </div>
      </div>
      
      <!-- 只有当不显示遮罩时才显示表格 -->
      <div v-if="!showCrawlerMask">
        <el-table :data="tasks" stripe style="width: 100%" v-loading="loading">
          <el-table-column prop="id" label="ID" width="60" align="center" header-align="center" />
          <el-table-column prop="city" :label="t('home.city')" width="100" align="center" header-align="center" />
          <el-table-column prop="status" :label="t('home.status')" width="100" align="center" header-align="center">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)">{{ getLocalizedStatus(scope.row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="start_time" :label="t('home.startTime')" width="180" align="center" header-align="center">
            <template #default="scope">
              {{ formatDate(scope.row.start_time) }}
            </template>
          </el-table-column>
          <el-table-column prop="end_time" :label="t('taskList.columns.endTime')" width="180" align="center" header-align="center">
            <template #default="scope">
              {{ scope.row.end_time ? formatDate(scope.row.end_time) : scope.row.expected_end_time ? formatDate(scope.row.expected_end_time) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="total_items" :label="t('taskList.columns.totalItems')" width="100" align="center" header-align="center" />
          <el-table-column prop="success_items" :label="t('taskList.columns.successItems')" width="100" align="center" header-align="center" />
          <el-table-column :label="t('taskList.columns.progress')" width="180" align="center" header-align="center">
            <template #default="scope">
              <el-progress
                :percentage="calculateProgress(scope.row)"
                :status="getProgressStatus(scope.row.status)"
              />
            </template>
          </el-table-column>
          <el-table-column :label="t('taskList.columns.actions')" width="250" align="center" header-align="center">
            <template #default="scope">
              <el-button-group>
                <el-button 
                  size="small"
                  type="primary"
                  @click="viewDetail(scope.row)"
                  :disabled="scope.row.status === '进行中' || scope.row.status === 'In Progress'"
                >
                  <el-icon><ViewIcon /></el-icon> {{ t('home.view') }}
                </el-button>
                <el-button 
                  size="small"
                  type="success"
                  @click="runAnalysis(scope.row)"
                  :disabled="scope.row.status === '进行中' || scope.row.status === 'In Progress' || scope.row.success_items === 0"
                >
                  <el-icon><DataAnalysis /></el-icon> {{ t('menu.analysis') }}
                </el-button>
                <el-button 
                  size="small"
                  type="danger"
                  @click="deleteTask(scope.row)"
                  :disabled="scope.row.status === '进行中' || scope.row.status === 'In Progress'"
                >
                  <el-icon><Delete /></el-icon> {{ t('common.delete') }}
                </el-button>
              </el-button-group>
            </template>
          </el-table-column>
        </el-table>
        
        <div class="pagination-container">
          <el-pagination
            background
            layout="total, sizes, prev, pager, next"
            :total="total"
            :page-size="pageSize"
            :current-page="currentPage"
            :page-sizes="[10, 20, 50, 100]"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import api from '../api/api';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { View as ViewIcon, DataAnalysis, Delete, Loading } from '@element-plus/icons-vue';

export default {
  name: 'TaskList',
  
  components: {
    ViewIcon,
    DataAnalysis,
    Delete,
    Loading
  },
  
  setup() {
    const router = useRouter();
    const { t } = useI18n();
    
    // 爬虫任务启动遮罩相关
    const showCrawlerMask = ref(false);
    const remainingSeconds = ref(60);
    const maskProgressPercentage = ref(0);
    let maskTimer = null;
    
    // 检查是否需要显示爬虫启动遮罩
    const checkCrawlerMask = () => {
      const lastStartTime = localStorage.getItem('lastCrawlTaskStartTime');
      if (!lastStartTime) return;
      
      const now = new Date().getTime();
      const startTime = parseInt(lastStartTime);
      const elapsedSeconds = Math.floor((now - startTime) / 1000);
      
      // 如果60秒内启动了爬虫，显示遮罩
      if (elapsedSeconds < 60) {
        showCrawlerMask.value = true;
        remainingSeconds.value = 60 - elapsedSeconds;
        maskProgressPercentage.value = Math.floor((elapsedSeconds / 60) * 100);
        
        // 开始倒计时
        startMaskTimer();
      }
    };
    
    // 开始遮罩倒计时
    const startMaskTimer = () => {
      // 清除可能存在的旧定时器
      if (maskTimer) {
        clearInterval(maskTimer);
      }
      
      // 创建新定时器，每秒更新一次
      maskTimer = setInterval(() => {
        remainingSeconds.value--;
        maskProgressPercentage.value = Math.floor(((60 - remainingSeconds.value) / 60) * 100);
        
        // 倒计时结束，关闭遮罩
        if (remainingSeconds.value <= 0) {
          showCrawlerMask.value = false;
          clearInterval(maskTimer);
          maskTimer = null;
          // 刷新任务列表
          fetchTasks();
        }
      }, 1000);
    };
    
    // 手动关闭遮罩
    const forceDismissMask = () => {
      showCrawlerMask.value = false;
      if (maskTimer) {
        clearInterval(maskTimer);
        maskTimer = null;
      }
      // 刷新任务列表
      fetchTasks();
    };
    
    // 任务列表数据
    const tasks = ref([]);
    const loading = ref(false);
    
    // 分页参数
    const currentPage = ref(1);
    const pageSize = ref(10);
    const total = ref(0);
    
    // 获取任务列表
    const fetchTasks = async () => {
      try {
        loading.value = true;
        
        const params = {
          limit: pageSize.value,
          offset: (currentPage.value - 1) * pageSize.value
        };
        
        const result = await api.getTasks(params);
        tasks.value = result;
        
        // TODO: 获取总数量，后端API需要支持
        total.value = 100; // 临时设置，实际项目中应从API获取
        
        loading.value = false;
      } catch (error) {
        loading.value = false;
        ElMessage.error(t('taskList.messages.fetchTasksFailed') + ': ' + (error.message || error));
        console.error(error);
      }
    };
    
    // 刷新任务列表
    const refreshTasks = () => {
      fetchTasks();
    };
    
    // 处理页码变化
    const handleCurrentChange = (page) => {
      currentPage.value = page;
      fetchTasks();
    };
    
    // 处理每页显示数量变化
    const handleSizeChange = (size) => {
      pageSize.value = size;
      currentPage.value = 1;
      fetchTasks();
    };
    
    // 查看详情
    const viewDetail = (task) => {
      // 检查任务是否进行中
      if (task.status === '进行中' || task.status === 'In Progress') {
        ElMessage.warning(t('taskList.messages.taskInProgress'));
        return;
      }
      router.push({ 
        name: 'HouseList', 
        params: { taskId: task.id.toString() },
        query: { city: task.city }
      });
    };
    
    // 运行数据分析
    const runAnalysis = async (task) => {
      try {
        // 检查任务是否进行中
        if (task.status === '进行中' || task.status === 'In Progress') {
          ElMessage.warning(t('taskList.messages.cannotAnalyzeInProgress'));
          return;
        }
        
        // 检查是否有成功爬取的数据
        if (task.success_items === 0) {
          ElMessage.warning(t('taskList.messages.noDataToAnalyze'));
          return;
        }
        
        loading.value = true;
        
        const data = {
          task_id: task.id,
          city: task.city,
          analysis_types: [] // 空数组表示运行所有类型的分析
        };
        
        await api.runAnalysis(data);
        
        loading.value = false;
        ElMessage.success(t('taskList.messages.analysisStarted'));
        
        // 跳转到分析结果页面，同时传递taskId和city参数
        router.push({ 
          name: 'Analysis', 
          query: { 
            city: task.city,
            taskId: task.id,
            immediate: 'true' // 标记为立即分析
          } 
        });
      } catch (error) {
        loading.value = false;
        ElMessage.error(t('taskList.messages.analysisStartFailed'));
        console.error(error);
      }
    };
    
    // 删除任务
    const deleteTask = async (task) => {
      try {
        // 检查任务是否进行中
        if (task.status === '进行中' || task.status === 'In Progress') {
          ElMessage.warning(t('taskList.messages.cannotDeleteInProgress'));
          return;
        }
        
        // 确认删除
        await ElMessageBox.confirm(
          t('taskList.messages.confirmDelete', { id: task.id, city: task.city }),
          t('taskList.messages.deleteConfirmTitle'),
          {
            confirmButtonText: t('common.confirm'),
            cancelButtonText: t('common.cancel'),
            type: 'warning'
          }
        );
        
        loading.value = true;
        
        // 调用删除API
        await api.deleteTask(task.id);
        
        loading.value = false;
        ElMessage.success(t('taskList.messages.deleteSuccess'));
        
        // 刷新任务列表
        refreshTasks();
      } catch (error) {
        loading.value = false;
        
        // 用户取消删除操作
        if (error === 'cancel') {
          return;
        }
        
        ElMessage.error(t('taskList.messages.deleteFailed'));
        console.error(error);
      }
    };
    
    // 计算进度百分比
    const calculateProgress = (task) => {
      // 优先使用后端返回的progress字段
      if (task.progress !== undefined && task.progress !== null) {
        return task.progress;
      }
      
      // 如果后端没有提供progress字段，才进行前端计算
      if (!task.total_items || task.total_items === 0) return 0;
      
      // 计算成功爬取的百分比
      const progress = (task.success_items / task.total_items) * 100;
      return Math.min(Math.round(progress), 100);
    };
    
    // 获取状态对应的类型
    const getStatusType = (status) => {
      switch (status) {
        case '进行中':
        case 'In Progress':
          return 'warning';
        case '完成':
        case 'Completed':
          return 'success';
        case '失败':
        case 'Failed':
          return 'danger';
        default:
          return 'info';
      }
    };
    
    // 获取进度条状态
    const getProgressStatus = (status) => {
      switch (status) {
        case '进行中':
        case 'In Progress':
          return '';
        case '完成':
        case 'Completed':
          return 'success';
        case '失败':
        case 'Failed':
          return 'exception';
        default:
          return '';
      }
    };
    
    // 格式化日期
    const formatDate = (dateString) => {
      if (!dateString) return '';
      
      const date = new Date(dateString);
      return date.toLocaleString();
    };
    
    // 获取本地化状态文本
    const getLocalizedStatus = (status) => {
      switch (status) {
        case '进行中':
        case 'In Progress':
          return t('taskList.status.inProgress');
        case '完成':
        case 'Completed':
          return t('taskList.status.completed');
        case '失败':
        case 'Failed':
          return t('taskList.status.failed');
        default:
          return status;
      }
    };
    
    // 组件挂载时获取任务列表
    onMounted(() => {
      // 检查是否需要显示爬虫启动遮罩
      checkCrawlerMask();
      
      // 如果没有显示遮罩，则直接获取任务列表
      if (!showCrawlerMask.value) {
        fetchTasks();
      }
    });
    
    // 组件卸载前清除定时器
    onBeforeUnmount(() => {
      if (maskTimer) {
        clearInterval(maskTimer);
        maskTimer = null;
      }
    });
    
    return {
      tasks,
      loading,
      currentPage,
      pageSize,
      total,
      refreshTasks,
      handleCurrentChange,
      handleSizeChange,
      viewDetail,
      runAnalysis,
      deleteTask,
      calculateProgress,
      getStatusType,
      getProgressStatus,
      formatDate,
      getLocalizedStatus,
      // 添加遮罩相关
      showCrawlerMask,
      remainingSeconds,
      maskProgressPercentage,
      forceDismissMask,
      t
    };
  }
};
</script>

<style scoped>
.task-list {
  margin-bottom: 20px;
  position: relative;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

/* 修改后的爬虫遮罩样式 - 改为在卡片内显示 */
.crawler-mask {
  position: relative;
  padding: 30px 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.mask-content {
  width: 100%;
  max-width: 450px;
  margin: 0 auto;
}

.loading-icon {
  font-size: 36px;
  margin-bottom: 15px;
  color: #409EFF;
  animation: spin 1.5s linear infinite;
}

.mask-content h3 {
  font-size: 18px;
  margin-bottom: 15px;
}

.mask-content p {
  margin: 10px 0;
  color: #606266;
}

.mask-content .el-button {
  margin-top: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style> 