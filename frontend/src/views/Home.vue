<template>
  <div class="home">
    <!-- 简约风格的欢迎区域 -->
    <el-row :gutter="24" class="welcome-section">
      <el-col :span="16">
        <h1>{{ $t('app.title') }}</h1>
        <p class="subtitle">{{ $t('app.subtitle') }}</p>
        <div class="action-buttons">
          <el-button type="primary" size="large" @click="scrollToCreateTask">
            <el-icon><Plus /></el-icon> {{ $t('home.createTask') }}
          </el-button>
          <el-button size="large" @click="goToAnalysis">
            <el-icon><DataAnalysis /></el-icon> {{ $t('home.viewAnalysis') || '查看分析' }}
          </el-button>
        </div>
      </el-col>
      <el-col :span="8" class="welcome-stats">
        <el-row :gutter="16">
          <el-col :span="24">
            <el-card shadow="hover" class="stat-card">
              <el-statistic :value="statsData.totalHouses" title="房源总量">
                <template #suffix>
                  <span class="stat-trend">
                    <el-icon class="trend-icon"><ArrowUp /></el-icon>
                    {{ statsData.housingGrowth }}%
                  </span>
                </template>
              </el-statistic>
            </el-card>
          </el-col>
        </el-row>
        <el-row :gutter="16" style="margin-top: 16px;">
          <el-col :span="12">
            <el-card shadow="hover" class="stat-card small">
              <el-statistic :value="statsData.totalCities" title="覆盖城市" />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="hover" class="stat-card small">
              <el-statistic :value="statsData.totalTasks" title="爬取任务" />
            </el-card>
          </el-col>
        </el-row>
      </el-col>
    </el-row>

    <!-- 主要内容区域 -->
    <el-row :gutter="20" class="main-content">
      <!-- 左侧功能介绍 -->
      <el-col :span="16">
        <el-card class="intro-card" shadow="never">
          <template #header>
            <div class="card-header">
              <h2>{{ $t('home.systemIntro') }}</h2>
            </div>
          </template>
          <div class="system-intro">
            <p>{{ $t('home.introText') }}</p>
            
            <h3>{{ $t('home.mainFeatures') }}</h3>
            <el-row :gutter="24">
              <el-col :span="8">
                <el-card shadow="hover" class="feature-card">
                  <template #header>
                    <div class="feature-header">
                      <el-icon><Download /></el-icon>
                      <span>{{ $t('home.dataCollection') }}</span>
                    </div>
                  </template>
                  <p>{{ $t('home.dataCollectionDesc') }}</p>
                </el-card>
              </el-col>
              
              <el-col :span="8">
                <el-card shadow="hover" class="feature-card">
                  <template #header>
                    <div class="feature-header">
                      <el-icon><DataAnalysis /></el-icon>
                      <span>{{ $t('home.dataAnalysis') }}</span>
                    </div>
                  </template>
                  <p>{{ $t('home.dataAnalysisDesc') }}</p>
                </el-card>
              </el-col>
              
              <el-col :span="8">
                <el-card shadow="hover" class="feature-card">
                  <template #header>
                    <div class="feature-header">
                      <el-icon><PieChart /></el-icon>
                      <span>{{ $t('home.visualization') }}</span>
                    </div>
                  </template>
                  <p>{{ $t('home.visualizationDesc') }}</p>
                </el-card>
              </el-col>
            </el-row>
            
            <h3 class="quick-start-title">{{ $t('home.quickStart') }}</h3>
            <div class="steps-container">
              <el-steps :active="1" finish-status="success" :space="200" align-center>
                <el-step :title="$t('home.step1Title') || '创建任务'" :description="$t('home.step1')" />
                <el-step :title="$t('home.step2Title') || '查看结果'" :description="$t('home.step2')" />
                <el-step :title="$t('home.step3Title') || '分析数据'" :description="$t('home.step3')" />
              </el-steps>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧任务创建和最近任务 -->
      <el-col :span="8" ref="taskFormSection">
        <CrawlTaskForm @task-created="handleTaskCreated" class="task-form" />
        
        <el-card class="latest-tasks" shadow="never" v-loading="loading">
          <template #header>
            <div class="card-header">
              <h3>{{ $t('home.recentTasks') }}</h3>
              <el-button type="primary" link @click="goToTaskList">{{ $t('home.viewAll') }}</el-button>
            </div>
          </template>
          
          <div v-if="recentTasks.length > 0" class="tasks-container">
            <div v-for="task in recentTasks" :key="task.id" class="task-item">
              <div class="task-info">
                <div class="task-header">
                  <h4>{{ task.city }}</h4>
                  <el-tag :type="getStatusType(task.status)" size="small">{{ getLocalizedStatus(task.status) }}</el-tag>
                </div>
                <p>{{ $t('home.startTime') }} {{ formatDate(task.start_time) }}</p>
                <div class="progress-container">
                  <span>{{ $t('home.houseCount') }} {{ task.success_items }}/{{ task.total_items }}</span>
                  <el-progress 
                    :percentage="Math.round((task.success_items / Math.max(task.total_items, 1)) * 100)" 
                    :status="task.status === 'Failed' ? 'exception' : ''"
                  />
                </div>
              </div>
              <div class="task-actions">
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="viewTaskDetail(task)"
                  :disabled="task.status === '进行中' || task.status === 'In Progress'"
                >
                  {{ $t('home.view') }}
                </el-button>
              </div>
            </div>
          </div>
          <el-empty v-else :description="$t('home.noTasks')" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, onMounted, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import CrawlTaskForm from '../components/CrawlTaskForm.vue';
import api from '../api/api';
import { Plus, ArrowUp, Download, DataAnalysis, PieChart } from '@element-plus/icons-vue';

export default {
  name: 'HomeView',
  
  components: {
    CrawlTaskForm,
    Plus,
    ArrowUp,
    Download,
    DataAnalysis,
    PieChart
  },
  
  setup() {
    const router = useRouter();
    const { t } = useI18n();
    const loading = ref(false);
    const recentTasks = ref([]);
    const taskFormSection = ref(null);
    
    // 模拟统计数据
    const statsData = reactive({
      totalHouses: 4328,
      housingGrowth: 12.4,
      totalCities: 15,
      totalTasks: 56
    });
    
    // 获取最近任务
    const fetchRecentTasks = async () => {
      try {
        loading.value = true;
        
        const params = {
          limit: 5,
          offset: 0
        };
        
        // 使用api.getTasks方法，它会正确处理响应格式
        recentTasks.value = await api.getTasks(params);
        loading.value = false;
      } catch (error) {
        console.error('获取最近爬虫任务失败详情:', error);
        // 即使发生错误也设置loading为false
        loading.value = false;
        
        // 确保recentTasks至少是空数组，而不是undefined
        if (!recentTasks.value) {
          recentTasks.value = [];
        }
        
        // 仅在非超时错误时显示错误消息
        if (error.code !== 'ECONNABORTED') {
          ElMessage.error(t('home.fetchTasksFailed'));
        }
      }
    };
    
    // 处理任务创建成功事件
    const handleTaskCreated = (task) => {
      ElMessage.success(`${t('home.taskCreatedSuccess')}：${task.city}`);
      
      // 立即在UI中添加新创建的任务，无需等待刷新
      if (task && task.id) {
        // 创建一个新任务对象，包含必要的属性
        const newTask = {
          id: task.id,
          city: task.city,
          city_code: task.city_code,
          start_time: new Date().toISOString(),
          status: 'In Progress',
          total_items: task.total_items || 0, // 预计每页30个房源
          success_items: task.success_items || 0
        };
        
        // 将新任务添加到列表开头
        recentTasks.value = [newTask, ...recentTasks.value].slice(0, 5);
      }
      
      // 不再需要延迟刷新，避免重复请求
    };
    
    // 滚动到任务创建表单
    const scrollToCreateTask = () => {
      if (taskFormSection.value) {
        taskFormSection.value.$el.scrollIntoView({ behavior: 'smooth' });
      }
    };
    
    // 跳转到分析页面
    const goToAnalysis = () => {
      router.push({ name: 'Analysis' });
    };
    
    // 跳转到任务列表页
    const goToTaskList = () => {
      router.push({ name: 'TaskList' });
    };
    
    // 查看任务详情
    const viewTaskDetail = (task) => {
      router.push({ 
        name: 'HouseList', 
        params: { 
          taskId: task.id.toString()
        },
        query: {
          city: task.city
        }
      });
    };
    
    // 获取状态对应的类型
    const getStatusType = (status) => {
      if (status === '进行中' || status === 'In Progress') {
        return 'warning';
      } else if (status === '完成' || status === 'Completed') {
        return 'success';
      } else if (status === '失败' || status === 'Failed') {
        return 'danger';
      }
      return 'info';
    };
    
    // 获取本地化的状态文本
    const getLocalizedStatus = (status) => {
      if (status === '进行中' || status === 'In Progress') {
        return t('home.taskStatus.inProgress');
      } else if (status === '完成' || status === 'Completed') {
        return t('home.taskStatus.completed');
      } else if (status === '失败' || status === 'Failed') {
        return t('home.taskStatus.failed');
      }
      return status;
    };
    
    // 格式化日期
    const formatDate = (dateString) => {
      if (!dateString) return '';
      
      const date = new Date(dateString);
      return date.toLocaleString();
    };
    
    // 尝试获取真实的统计数据
    const fetchStatistics = async () => {
      try {
        const dashboardData = await api.getDashboardStats();
        if (dashboardData) {
          statsData.totalHouses = dashboardData.house_count || 0;
          statsData.housingGrowth = dashboardData.growth_rate || 0;
          statsData.totalCities = dashboardData.city_count || 0;
          statsData.totalTasks = dashboardData.task_count || 0;
          
          // 如果有最近任务数据，更新最近任务列表
          if (dashboardData.recent_tasks && dashboardData.recent_tasks.length > 0) {
            recentTasks.value = dashboardData.recent_tasks;
            loading.value = false;
          }
        }
      } catch (error) {
        console.error('获取仪表盘数据失败', error);
        // 保留模拟数据作为后备
      }
    };
    
    // 组件挂载时获取最近任务
    onMounted(() => {
      fetchStatistics();
      // 如果仪表板数据中没有包含最近任务，则单独获取
      if (recentTasks.value.length === 0) {
        fetchRecentTasks();
      }
    });
    
    return {
      loading,
      recentTasks,
      statsData,
      taskFormSection,
      handleTaskCreated,
      scrollToCreateTask,
      goToAnalysis,
      goToTaskList,
      viewTaskDetail,
      getStatusType,
      getLocalizedStatus,
      formatDate
    };
  }
};
</script>

<style scoped>
.home {
  max-width: 1200px;
  margin: 0 auto;
  overflow-x: hidden; /* 防止水平滚动 */
}

/* 全局隐藏水平滚动条 */
:deep(*) {
  scrollbar-width: none; /* Firefox */
}

:deep(*)::-webkit-scrollbar-horizontal {
  display: none; /* Chrome, Safari, Edge */
}

:deep(.el-carousel__indicators),
:deep(.el-carousel__arrow),
:deep(.el-scrollbar__bar.is-horizontal),
:deep([class*='-scroll']),
:deep([class*='carousel']),
:deep([class*='indicator']),
:deep([class*='slider']) {
  display: none !important;
}

/* 移除底部导航的滚动条 */
:deep(.el-carousel__container) {
  overflow: hidden !important;
}

:deep(.carousel-arrow-left),
:deep(.carousel-arrow-right) {
  display: none !important;
}

.welcome-section {
  margin-bottom: 30px;
  padding: 30px 0;
  border-bottom: 1px solid #f0f0f0;
}

.welcome-section h1 {
  font-size: 2.5rem;
  color: #2c7be5;
  margin-bottom: 10px;
  font-weight: 500;
}

.subtitle {
  font-size: 1.2rem;
  color: #666;
  margin-bottom: 24px;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.welcome-stats {
  display: flex;
  flex-direction: column;
}

.stat-card {
  text-align: center;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-card.small {
  height: 100%;
}

.stat-trend {
  color: #67c23a;
  font-size: 14px;
  margin-left: 5px;
}

.trend-icon {
  margin-right: 4px;
}

.intro-card, .latest-tasks {
  margin-bottom: 24px;
  border: 1px solid #f0f0f0;
}

.intro-card {
  display: flex;
  flex-direction: column;
  height: calc(100% - 24px); /* 减去margin-bottom的值 */
}

.main-content {
  display: flex;
  align-items: stretch;
  margin-bottom: 40px;
  width: 100%;
  padding: 0;
  margin-left: 0 !important;
  margin-right: 0 !important;
}

.main-content .el-col {
  display: flex;
  flex-direction: column;
  padding: 0;
}

/* 调整对齐问题 */
:deep(.el-row) {
  margin-left: 0 !important;
  margin-right: 0 !important;
}

:deep(.el-row--flex) {
  margin-left: 0 !important;
  margin-right: 0 !important;
}

:deep(.el-col-16), :deep(.el-col-8) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

.system-intro {
  line-height: 1.6;
  overflow-y: auto;
  flex: 1;
}

.system-intro h3 {
  margin: 20px 0 15px;
  font-weight: 500;
  color: #333;
}

.quick-start-title {
  margin: 30px 0 20px;
  text-align: left;
  font-weight: 500;
  color: #333;
}

.steps-container {
  width: 100%;
  position: relative;
  margin-bottom: 10px;
  display: flex;
  justify-content: center;
}

/* 确保步骤组件展示正常 */
:deep(.el-steps) {
  width: auto;
  max-width: 90%;
  overflow: hidden;
}

/* 步骤标题样式 */
:deep(.el-step__title) {
  font-weight: 500;
  font-size: 16px;
  text-align: center;
}

/* 步骤描述样式 */
:deep(.el-step__description) {
  font-size: 13px;
  white-space: normal;
  word-break: break-word;
  max-width: 90%;
  margin: 0 auto;
  color: #666;
  text-align: center;
}

/* 步骤图标样式 */
:deep(.el-step__icon) {
  color: #2c7be5;
}

:deep(.el-step__head.is-finish) {
  color: #67c23a;
  border-color: #67c23a;
}

:deep(.el-step__head.is-process) {
  color: #2c7be5;
  border-color: #2c7be5;
}

.system-intro p {
  margin-bottom: 15px;
  color: #606266;
}

.feature-card {
  height: 100%;
  transition: all 0.3s ease;
  border: 1px solid #f0f0f0;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 6px 16px -8px rgba(0,0,0,0.08);
}

.feature-header {
  display: flex;
  align-items: center;
}

.feature-header .el-icon {
  margin-right: 8px;
  color: #2c7be5;
}

/* 美化任务表单卡片 */
.task-form {
  margin-bottom: 24px;
  position: relative;
  width: 100%;
}

/* 确保右侧栏中的卡片充满整个宽度 */
.task-form > :deep(.el-card),
.latest-tasks {
  width: 100%;
  box-sizing: border-box;
}

/* 确保右侧的表单和列表对齐 */
:deep(.el-form), 
:deep(.latest-tasks > .el-card__body) {
  padding: 15px !important;
}

/* 最近爬虫任务样式 */
.latest-tasks {
  position: relative;
  display: flex;
  flex-direction: column;
  max-height: 500px; /* 使用固定最大高度 */
  margin-bottom: 24px;
  width: 100%;
}

/* 移除之前的装饰线 */
.latest-tasks::before {
  display: none;
}

.latest-tasks :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.latest-tasks :deep(.el-card__header) {
  background-color: #f9f9f9;
  border-bottom: 1px solid #f0f0f0;
  padding: 15px 20px;
}

:deep(.el-card__body) {
  padding: 15px 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 创建任务表单和最近任务列表的标题样式强化 */
.card-header h2, .card-header h3 {
  font-size: 16px;
  font-weight: 500;
  color: #333;
  margin: 0;
  position: relative;
  padding-left: 10px;
}

.card-header h2::before, .card-header h3::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 16px;
  background-color: #2c7be5;
  border-radius: 2px;
}

.tasks-container {
  max-height: 400px; /* 设置固定的最大高度 */
  overflow-y: auto;
  scrollbar-width: thin;
  flex: 1;
}

.tasks-container::-webkit-scrollbar {
  width: 6px;
}

.tasks-container::-webkit-scrollbar-thumb {
  background-color: #c0c4cc;
  border-radius: 3px;
}

.tasks-container::-webkit-scrollbar-track {
  background-color: #f5f7fa;
}

.latest-tasks :deep(.el-empty) {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

:deep(.el-progress-bar__outer) {
  background-color: #e9ecef;
}

/* 美化任务项 */
.task-item {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.3s ease;
  border-radius: 4px;
  margin-bottom: 8px;
}

.task-item:hover {
  background-color: #f9f9f9;
  transform: translateX(5px);
}

.task-item:last-child {
  border-bottom: none;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.task-info {
  flex: 1;
}

.task-info h4 {
  font-size: 15px;
  font-weight: 500;
  margin: 0;
  color: #333;
}

.task-info p {
  margin: 4px 0;
  font-size: 13px;
  color: #666;
}

.progress-container {
  margin-top: 8px;
}

.progress-container span {
  display: block;
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.task-actions {
  margin-left: 12px;
}

.task-actions .el-button {
  padding: 6px 12px;
}

/* 右侧栏整体样式优化 */
.main-content .el-col:last-child {
  padding-left: 10px !important;
}

@media (max-width: 768px) {
  .welcome-section {
    padding: 20px 0;
  }
  
  .welcome-section h1 {
    font-size: 2rem;
  }
  
  .subtitle {
    font-size: 1rem;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .main-content {
    flex-direction: column;
  }
  
  .intro-card, .latest-tasks {
    height: auto;
    margin-bottom: 20px;
  }
  
  .tasks-container {
    max-height: 300px;
  }
}

/* 隐藏底部步骤导航控件 - 更具体的选择器 */
:deep(.el-steps__nav),
:deep(.el-steps-nav),
:deep(.el-pagination),
:deep(.el-carousel__button),
:deep(.el-carousel-indicator),
:deep(.el-carousel-item__mask),
:deep(.el-carousel-arrow),
:deep([class*='step'][class*='nav']),
:deep([class*='step'][class*='dot']),
:deep([class*='carousel']),
:deep([class*='slider'][class*='button']),
:deep([class*='pagination']) {
  display: none !important;
}

/* 移除特定类型的滚动条 */
:deep([class*='horizontal-scroll']),
:deep([class*='overflow-x']),
:deep([class*='x-scroll']) {
  overflow-x: hidden !important;
}

/* 确保DOM树最后一个元素的滚动条不会显示 */
:deep(.el-main > *:last-child),
:deep(.home > *:last-child) {
  overflow-x: clip !important;
  margin-bottom: 0 !important;
}

:deep(body) {
  overflow-x: hidden;
}
</style>