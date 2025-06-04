<template>
  <div class="house-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <h3>房源列表</h3>
          <div class="filter-actions">
            <el-button type="primary" size="small" @click="refreshData">刷新</el-button>
            <el-button type="success" size="small" @click="exportData" :disabled="loading">
              <el-icon><Download /></el-icon> 导出CSV
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 筛选条件 -->
      <div class="filter-container">
        <el-form :model="filters" inline>
          <el-form-item label="城市">
            <el-select v-model="filters.city" placeholder="选择城市" clearable @change="handleCityChange">
              <el-option
                v-for="(code, name) in cities"
                :key="name"
                :label="name"
                :value="name"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="区域">
            <el-select v-model="filters.district" placeholder="选择区域" clearable>
              <el-option
                v-for="district in districts"
                :key="district"
                :label="district"
                :value="district"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="价格区间">
            <el-input-number v-model="filters.minPrice" placeholder="最低价" :min="0" />
            <span class="separator">-</span>
            <el-input-number v-model="filters.maxPrice" placeholder="最高价" :min="0" />
          </el-form-item>
          
          <el-form-item label="户型">
            <el-select v-model="filters.roomCount" placeholder="房间数" clearable>
              <el-option v-for="i in 5" :key="i" :label="`${i}室`" :value="i" />
            </el-select>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="applyFilters">筛选</el-button>
            <el-button @click="resetFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- 房源列表 -->
      <el-table 
        :data="houses" 
        stripe 
        style="width: 100%" 
        v-loading="loading"
        @expand-change="handleExpandChange"
        row-key="id"
      >
        <el-table-column type="expand">
          <template #default="props">
            <div class="house-detail">
              <el-row :gutter="20">
                <el-col :span="8">
                  <div class="image-container">
                    <img 
                      v-if="props.row.loadedImage"
                      :src="props.row.loadedImage" 
                      alt="房源图片" 
                      class="house-image" 
                      @error="handleImageError" 
                      ref="houseImage"
                    />
                    <div v-else-if="props.row.imageLoading" class="image-loading">
                      <el-skeleton-item variant="image" style="width: 100%; height: 150px" />
                    </div>
                    <div v-else-if="!props.row.image" class="image-unavailable">
                      <span>暂无图片</span>
                    </div>
                    <div v-else class="image-loading">
                      <span>加载图片中...</span>
                    </div>
                  </div>
                </el-col>
                <el-col :span="16">
                  <p><strong>地址:</strong> 
                    {{ props.row.location_qu || '' }} 
                    {{ props.row.location_big || '' }} 
                    {{ props.row.location_small || '' }}
                    <span v-if="!props.row.location_qu && !props.row.location_big && !props.row.location_small">未知</span>
                  </p>
                  <p><strong>户型:</strong> {{ props.row.room || props.row.layout || '未知' }}</p>
                  <p><strong>面积:</strong> {{ props.row.size || props.row.area || '未知' }}{{ props.row.size || props.row.area ? '㎡' : '' }}</p>
                  <p><strong>单价:</strong> {{ props.row.unit_price || '未知' }}{{ props.row.unit_price ? '元/㎡/月' : '' }}</p>
                  <p><strong>朝向:</strong> {{ props.row.direction || '未知' }}</p>
                  <p><strong>楼层:</strong> {{ props.row.floor || '未知' }}</p>
                  <p><strong>爬取时间:</strong> {{ formatDate(props.row.crawl_time) }}</p>
                  <el-button 
                    type="primary" 
                    size="small" 
                    @click="openLink(props.row.link || props.row.url)"
                    :disabled="!(props.row.link || props.row.url)"
                  >
                    {{ props.row.link || props.row.url ? '查看详情' : '链接不可用' }}
                  </el-button>
                </el-col>
              </el-row>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="250" />
        <el-table-column prop="price" label="价格(元/月)" width="120" sortable />
        <el-table-column label="区域" width="100">
          <template #default="scope">
            {{ scope.row.location_qu || '未知' }}
          </template>
        </el-table-column>
        <el-table-column label="面积(㎡)" width="100" sortable>
          <template #default="scope">
            {{ scope.row.size || scope.row.area || '未知' }}
          </template>
        </el-table-column>
        <el-table-column label="户型" width="120">
          <template #default="scope">
            {{ scope.row.room || scope.row.layout || '未知' }}
          </template>
        </el-table-column>
        <el-table-column label="朝向" width="100">
          <template #default="scope">
            {{ scope.row.direction || '未知' }}
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
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
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, onMounted, watch, nextTick } from 'vue';
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus';
import { Download } from '@element-plus/icons-vue';
import { useRoute } from 'vue-router';
import api from '../api/api';

export default {
  name: 'HouseList',
  
  components: {
    Download
  },
  
  setup() {
    const route = useRoute();
    
    // 房源数据
    const houses = ref([]);
    const loading = ref(false);
    
    // 筛选条件
    const filters = reactive({
      city: '',
      district: '',
      minPrice: null,
      maxPrice: null,
      roomCount: null,
      taskId: null
    });
    
    // 城市和区域数据
    const cities = ref({});
    const districts = ref([]);
    
    // 分页参数
    const currentPage = ref(1);
    const pageSize = ref(20);
    const total = ref(0);
    
    // 获取房源数据
    const fetchData = async () => {
      try {
        loading.value = true;
        
        // 构建请求参数
        const params = {
          city: filters.city || undefined,
          district: filters.district || undefined,
          min_price: filters.minPrice || undefined,
          max_price: filters.maxPrice || undefined,
          room_count: filters.roomCount || undefined,
          limit: pageSize.value,
          offset: (currentPage.value - 1) * pageSize.value
        };
        
        // 如果有任务ID，添加到请求参数中
        if (filters.taskId) {
          params.task_id = filters.taskId;
        }
        
        // 获取房源列表
        houses.value = await api.getHouses(params);
        
        // 初始化图片状态
        if (houses.value && houses.value.length > 0) {
          houses.value.forEach(house => {
            // 设置默认图片状态
            house.loadedImage = null;
            house.imageLoading = false;
            house.imageLoadError = false;
          });
          
          // 添加调试输出
          console.log('第一条房源数据:', JSON.stringify(houses.value[0], null, 2));
        }
        
        // 获取总数量
        const countResult = await api.getHouseCount(params);
        total.value = countResult.count;
        
        loading.value = false;
      } catch (error) {
        loading.value = false;
        ElMessage.error('获取房源数据失败');
        console.error(error);
      }
    };
    
    // 获取城市列表
    const getCities = async () => {
      try {
        cities.value = await api.getCities();
      } catch (error) {
        ElMessage.error('获取城市列表失败');
        console.error(error);
      }
    };
    
    // 根据城市获取区域列表
    const getDistricts = async (city) => {
      try {
        if (!city) {
          districts.value = [];
          return;
        }
        
        districts.value = await api.getDistricts(city);
      } catch (error) {
        ElMessage.error('获取区域列表失败');
        console.error(error);
      }
    };
    
    // 监听路由参数变化
    watch(() => route.query, (query) => {
      if (query.city) {
        filters.city = query.city;
      }
      
      // 从params中获取taskId
      if (route.params.taskId) {
        filters.taskId = parseInt(route.params.taskId);
        fetchData();
      } else if (query.taskId) {
        // 兼容旧版本，也支持从query中获取taskId
        filters.taskId = query.taskId;
        fetchData();
      }
    }, { immediate: true });
    
    // 城市变化时更新区域列表
    const handleCityChange = (city) => {
      filters.district = '';
      getDistricts(city);
    };
    
    // 刷新数据
    const refreshData = () => {
      fetchData();
    };
    
    // 应用筛选条件
    const applyFilters = () => {
      currentPage.value = 1;
      fetchData();
    };
    
    // 重置筛选条件
    const resetFilters = () => {
      // 保留城市筛选，重置其他条件
      const city = filters.city;
      
      Object.assign(filters, {
        city,
        district: '',
        minPrice: null,
        maxPrice: null,
        roomCount: null,
        taskId: null
      });
      
      currentPage.value = 1;
      fetchData();
    };
    
    // 导出数据
    const exportData = async () => {
      try {
        // 显示确认对话框
        ElMessageBox.confirm(
          '确定要导出当前筛选条件下的所有数据吗？',
          '导出确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'info'
          }
        ).then(async () => {
          // 显示加载指示器
          const loadingInstance = ElLoading.service({
            text: '正在导出数据...',
            background: 'rgba(0, 0, 0, 0.7)'
          });
          
          try {
            // 构建与当前筛选条件相同的请求参数
            const params = {
              city: filters.city || undefined,
              district: filters.district || undefined,
              min_price: filters.minPrice || undefined,
              max_price: filters.maxPrice || undefined,
              room_count: filters.roomCount || undefined,
              task_id: filters.taskId || undefined
            };
            
            // 调用后端导出API
            const response = await api.exportHouses(params);
            
            if (!response || !response.file_url) {
              ElMessage.warning('导出数据失败，请稍后再试');
              loadingInstance.close();
              return;
            }
            
            // 创建下载链接
            const link = document.createElement('a');
            link.setAttribute('href', response.file_url);
            link.setAttribute('download', response.filename || '房源数据.csv');
            link.style.visibility = 'hidden';
            
            // 添加到文档并触发点击
            document.body.appendChild(link);
            link.click();
            
            // 清理
            document.body.removeChild(link);
            
            // 提示成功
            ElMessage.success(`数据导出成功: ${response.filename}`);
          } catch (error) {
            console.error('导出数据失败:', error);
            ElMessage.error('导出数据失败: ' + (error.message || '未知错误'));
          } finally {
            // 关闭加载指示器
            loadingInstance.close();
          }
        }).catch(() => {
          // 用户取消了导出
          ElMessage.info('已取消导出');
        });
      } catch (error) {
        console.error('导出操作失败:', error);
        ElMessage.error('导出操作失败');
      }
    };
    
    // 在新标签页打开链接
    const openLink = (url) => {
      if (!url) {
        ElMessage.warning('链接不可用');
        return;
      }
      window.open(url, '_blank');
    };
    
    // 处理页码变化
    const handleCurrentChange = (page) => {
      currentPage.value = page;
      fetchData();
    };
    
    // 处理每页显示数量变化
    const handleSizeChange = (size) => {
      pageSize.value = size;
      currentPage.value = 1;
      fetchData();
    };
    
    // 格式化日期
    const formatDate = (dateString) => {
      if (!dateString) return '';
      
      const date = new Date(dateString);
      return date.toLocaleString();
    };
    
    // 处理图片加载错误
    const handleImageError = (e) => {
      // 使用base64编码的简单灰色图片作为默认图片
      e.target.src = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAPoAAADICAYAAADBXvybAAAABmJLR0QA/wD/AP+gvaeTAAAAN0lEQVR4nO3BAQ0AAADCoPdPbQ8HFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPwbcwAAAYUy4iEAAAAASUVORK5CYII=';
      e.target.alt = '图片暂不可用';
      e.target.classList.add('image-error');
    };
    
    // 处理行展开事件
    const handleExpandChange = (row, expandedRows) => {
      // 只在行真正展开时加载图片，不影响展开操作
      if (expandedRows.includes(row)) {
        // 使用nextTick确保DOM更新后再加载图片
        nextTick(() => {
          if (row && row.image && !row.loadedImage) {
            loadImage(row);
          }
        });
      }
    };
    
    // 加载图片
    const loadImage = async (row) => {
      // 如果没有图片URL，不尝试加载
      if (!row.image) {
        row.loadedImage = null;
        return;
      }
      
      // 先设置加载状态
      row.imageLoading = true;
      
      try {
        // 调用后端API获取图片的base64编码
        const response = await api.getImageBase64(row.image);
        if (response && response.base64) {
          // 更新行数据，添加loadedImage属性
          row.loadedImage = response.base64;
        } else {
          // 如果后端没有返回base64数据，设置为错误状态
          handleImageLoadError(row);
        }
      } catch (error) {
        console.error('加载图片失败:', error);
        handleImageLoadError(row);
      } finally {
        // 无论成功或失败，都结束加载状态
        row.imageLoading = false;
      }
    };
    
    // 处理图片加载失败
    const handleImageLoadError = (row) => {
      // 设置为默认图片
      row.loadedImage = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAPoAAADICAYAAADBXvybAAAABmJLR0QA/wD/AP+gvaeTAAAAN0lEQVR4nO3BAQ0AAADCoPdPbQ8HFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPwbcwAAAYUy4iEAAAAASUVORK5CYII=';
      row.imageLoadError = true;
    };
    
    // 组件挂载时获取初始数据
    onMounted(() => {
      getCities();
      
      // 如果URL中包含城市参数，则获取对应的区域列表
      if (route.query.city) {
        filters.city = route.query.city;
        getDistricts(filters.city);
      }
      
      fetchData();
    });
    
    return {
      houses,
      loading,
      filters,
      cities,
      districts,
      currentPage,
      pageSize,
      total,
      handleCityChange,
      refreshData,
      applyFilters,
      resetFilters,
      exportData,
      openLink,
      handleCurrentChange,
      handleSizeChange,
      formatDate,
      handleImageError,
      handleExpandChange
    };
  }
};
</script>

<style scoped>
.house-list {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-container {
  margin-bottom: 20px;
}

.filter-actions {
  display: flex;
  gap: 10px;
}

.separator {
  margin: 0 5px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.house-detail {
  padding: 10px;
}

.house-image {
  width: 100%;
  max-width: 240px;
  border-radius: 4px;
}

.image-container {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.image-loading {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.image-error {
  border: 1px dashed #ccc;
  min-height: 120px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #909399;
  font-style: italic;
  background-color: #f5f7fa;
  position: relative;
}

.image-error::after {
  content: '图片暂不可用';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #909399;
  font-size: 14px;
  background-color: rgba(255,255,255,0.7);
  padding: 5px 10px;
  border-radius: 4px;
}

.image-unavailable {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #909399;
  font-style: italic;
  background-color: #f5f7fa;
  position: relative;
}

.image-unavailable::after {
  content: '暂无图片';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #909399;
  font-size: 14px;
  background-color: rgba(255,255,255,0.7);
  padding: 5px 10px;
  border-radius: 4px;
}
</style> 