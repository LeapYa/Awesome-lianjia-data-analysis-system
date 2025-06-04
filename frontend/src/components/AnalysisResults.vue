<template>
  <div class="analysis-results">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2 class="section-title">数据分析结果</h2>
          <div class="filter-actions">
            <div class="city-selector">
              <span class="selector-label">城市:</span>
              <el-select v-model="selectedCity" placeholder="选择城市查看数据" clearable @change="handleCityChange" size="default">
              <el-option
                v-for="(code, name) in cities"
                :key="name"
                :label="name"
                :value="name"
              />
            </el-select>
            </div>
            <el-button type="primary" @click="refreshData">刷新</el-button>
            <el-button type="success" @click="runAnalysisNow" :loading="analysisLoading">立即分析</el-button>
          </div>
        </div>
      </template>
      
      <div v-loading="loading">
        <!-- 数据概览 -->
        <div class="summary-section" v-if="summaryData">
          <h3 class="overview-title">租房市场概览 - {{ selectedCity || '全部城市' }}</h3>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-card shadow="hover" class="stat-card">
                <h2>{{ summaryData.total_count }}</h2>
                <p>房源总数</p>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" class="stat-card">
                <h2>{{ summaryData.avg_price }}元/月</h2>
                <p>平均租金</p>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" class="stat-card">
                <h2>{{ summaryData.avg_unit_price }}元/㎡/月</h2>
                <p>平均单位租金</p>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" class="stat-card">
                <h2>{{ getTopDistrict() }}</h2>
                <p>热门区域</p>
              </el-card>
            </el-col>
          </el-row>
        </div>
        
        <!-- 分析结果标签页 -->
        <div class="current-city-indicator">
          当前数据: <span class="city-name">{{ selectedCity || '全部城市' }}</span>
          <span v-if="analysisTime[activeTab]" class="analysis-time">
            最后分析时间: {{ formatAnalysisTime(analysisTime[activeTab]) }}
          </span>
        </div>
        <el-tabs v-model="activeTab" @tab-click="handleTabClick" type="border-card" class="analysis-tabs">
          <el-tab-pane label="区域租金分析" name="district_analysis">
            <div class="chart-container" v-if="analysisData.district_analysis">
              <div id="district-price-chart" class="chart"></div>
              <div id="district-count-chart" class="chart"></div>
            </div>
            <el-empty v-else description="暂无区域租金分析数据" />
          </el-tab-pane>
          
          <el-tab-pane label="户型租金分析" name="room_type_analysis">
            <div class="chart-container" v-if="analysisData.room_type_analysis">
              <div id="room-type-price-chart" class="chart"></div>
              <div id="room-type-count-chart" class="chart"></div>
            </div>
            <el-empty v-else description="暂无户型租金分析数据" />
          </el-tab-pane>
          
          <el-tab-pane label="朝向租金分析" name="direction_analysis">
            <div class="chart-container" v-if="analysisData.direction_analysis">
              <div id="direction-chart" class="chart"></div>
            </div>
            <el-empty v-else description="暂无朝向租金分析数据" />
          </el-tab-pane>
          
          <el-tab-pane label="楼层租金分析" name="floor_analysis">
            <div class="chart-container" v-if="analysisData.floor_analysis">
              <div id="floor-chart" class="chart"></div>
            </div>
            <el-empty v-else description="暂无楼层租金分析数据" />
          </el-tab-pane>
          
          <el-tab-pane label="租金分布" name="price_distribution">
            <div class="chart-container" v-if="analysisData.price_distribution">
              <div id="price-distribution-chart" class="chart"></div>
            </div>
            <el-empty v-else description="暂无租金分布数据" />
          </el-tab-pane>
          
          <el-tab-pane label="小区租金分析" name="community_analysis">
            <div class="chart-container" v-if="analysisData.community_analysis">
              <div id="community-chart" class="chart"></div>
            </div>
            <el-empty v-else description="暂无小区租金分析数据" />
          </el-tab-pane>
          
          <!-- 新增特征分析标签页 -->
          <el-tab-pane label="特征标签分析" name="features_analysis">
            <div class="chart-container" v-if="analysisData.features_analysis">
              <div id="features-chart" class="chart"></div>
              <div class="feature-stats-table">
                <h4>特征标签统计</h4>
                <el-table :data="analysisData.features_analysis" stripe style="width: 100%" :default-sort="{prop: 'count', order: 'descending'}">
                  <el-table-column prop="feature" label="特征标签" width="150" />
                  <el-table-column prop="count" label="出现次数" sortable width="120" />
                  <el-table-column prop="percentage" label="占比(%)" sortable width="120">
                    <template #default="scope">
                      {{ scope.row.percentage.toFixed(2) }}%
                    </template>
                  </el-table-column>
                  <el-table-column prop="avg_price" label="均价(元/月)" sortable width="130" />
                  <el-table-column prop="avg_size" label="均面积(㎡)" sortable width="130" />
                  <el-table-column prop="stddev_price" label="价格标准差" sortable width="130" />
                </el-table>
              </div>
            </div>
            <el-empty v-else description="暂无特征标签分析数据" />
          </el-tab-pane>
          
          <el-tab-pane label="特征组合分析" name="feature_combinations">
            <div class="chart-container" v-if="analysisData.feature_combinations">
              <div class="feature-combo-table">
                <h4>常见特征组合</h4>
                <p class="help-text">展示最常见的特征组合及其对应的价格和面积情况</p>
                <el-table :data="analysisData.feature_combinations" stripe style="width: 100%" :default-sort="{prop: 'count', order: 'descending'}">
                  <el-table-column prop="features" label="特征组合" min-width="250">
                    <template #default="scope">
                      <el-tag v-for="(feature, index) in formatFeatures(scope.row.features)" :key="index" class="feature-tag" size="small">
                        {{ feature }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="count" label="房源数量" sortable width="100" />
                  <el-table-column prop="percentage" label="占比(%)" sortable width="100">
                    <template #default="scope">
                      {{ scope.row.percentage.toFixed(2) }}%
                    </template>
                  </el-table-column>
                  <el-table-column prop="avg_price" label="均价(元/月)" sortable width="120" />
                  <el-table-column prop="avg_size" label="均面积(㎡)" sortable width="120" />
                  <el-table-column label="价格区间" width="170">
                    <template #default="scope">
                      {{ scope.row.min_price }}元 - {{ scope.row.max_price }}元
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
            <el-empty v-else description="暂无特征组合分析数据" />
          </el-tab-pane>
          
          <el-tab-pane label="地铁影响分析" name="metro_price_impact">
            <div class="chart-container" v-if="analysisData.metro_price_impact">
              <div id="metro-impact-chart" class="chart"></div>
              <div class="feature-stats-table">
                <h4>地铁对各区域房价的影响</h4>
                <el-table :data="analysisData.metro_price_impact" stripe style="width: 100%">
                  <el-table-column prop="location_qu" label="区域" width="120" />
                  <el-table-column prop="near_metro" label="是否靠近地铁" width="120">
                    <template #default="scope">
                      {{ scope.row.near_metro ? '是' : '否' }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="house_count" label="房源数量" sortable width="100" />
                  <el-table-column prop="avg_price" label="均价(元/月)" sortable width="120" />
                  <el-table-column prop="avg_size" label="均面积(㎡)" sortable width="120" />
                  <el-table-column label="价格区间" width="170">
                    <template #default="scope">
                      {{ scope.row.min_price }}元 - {{ scope.row.max_price }}元
                    </template>
                  </el-table-column>
                  <el-table-column prop="percentage" label="占比(%)" sortable width="100">
                    <template #default="scope">
                      {{ scope.row.percentage.toFixed(2) }}%
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
            <el-empty v-else description="暂无地铁影响分析数据" />
          </el-tab-pane>
          
          <el-tab-pane label="热门特征价格影响" name="popular_features_price">
            <div class="chart-container" v-if="analysisData.popular_features_price">
              <div id="popular-features-chart" class="chart"></div>
              <div class="feature-impact-table">
                <h4>热门特征对价格的影响</h4>
                <el-table :data="transformPopularFeaturesData()" stripe style="width: 100%">
                  <el-table-column prop="feature" label="特征名称" width="150" />
                  <el-table-column prop="has_feature" label="是否具有该特征" width="150">
                    <template #default="scope">
                      {{ scope.row.has_feature ? '是' : '否' }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="house_count" label="房源数量" sortable width="120" />
                  <el-table-column prop="avg_price" label="均价(元/月)" sortable width="130" />
                  <el-table-column prop="avg_size" label="均面积(㎡)" sortable width="130" />
                  <el-table-column prop="price_diff" label="价格差异" sortable width="130">
                    <template #default="scope">
                      <span :class="{'price-increase': scope.row.price_diff > 0, 'price-decrease': scope.row.price_diff < 0}">
                        {{ scope.row.price_diff > 0 ? '+' : '' }}{{ scope.row.price_diff }}元
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="percentage" label="占比(%)" sortable width="100">
                    <template #default="scope">
                      {{ scope.row.percentage.toFixed(2) }}%
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
            <el-empty v-else description="暂无热门特征价格影响分析数据" />
          </el-tab-pane>
          
          <!-- 新增的分析标签页 -->
          <el-tab-pane label="价格详细统计" name="price_stats">
            <div class="chart-container" v-if="analysisData.price_stats">
              <div class="stats-table">
                <h4>价格统计详情</h4>
                <el-table :data="analysisData.price_stats" stripe style="width: 100%">
                  <el-table-column prop="location_qu" label="区域" width="120" />
                  <el-table-column prop="price_mean" label="均价" width="100" />
                  <el-table-column prop="price_median" label="中位数" width="100" />
                  <el-table-column prop="price_25th" label="25%分位" width="100" />
                  <el-table-column prop="price_75th" label="75%分位" width="100" />
                  <el-table-column prop="price_min" label="最低价" width="100" />
                  <el-table-column prop="price_max" label="最高价" width="100" />
                  <el-table-column prop="price_std" label="标准差" width="100" />
                  <el-table-column prop="price_count" label="样本数" width="100" />
                </el-table>
              </div>
              <div id="boxplot-chart" class="chart"></div>
            </div>
            <el-empty v-else description="暂无价格统计数据" />
          </el-tab-pane>
          
          <el-tab-pane label="户型价格交叉" name="room_price_cross">
            <div class="chart-container" v-if="analysisData.room_price_cross">
              <div id="room-price-cross-chart" class="chart"></div>
            </div>
            <el-empty v-else description="暂无户型价格交叉分析数据" />
          </el-tab-pane>
          
          <el-tab-pane label="租金效率分析" name="rental_efficiency">
            <div class="chart-container" v-if="analysisData.rental_efficiency">
              <div id="rental-efficiency-chart" class="chart"></div>
            </div>
            <el-empty v-else description="暂无租金效率分析数据" />
          </el-tab-pane>
          
          <el-tab-pane label="价格趋势" name="price_trend" v-if="analysisData.price_trend">
            <div class="chart-container">
              <div id="price-trend-chart" class="chart"></div>
            </div>
          </el-tab-pane>
          
          <!-- 价格变化分析标签页 -->
          <el-tab-pane label="价格变化分析" name="price_changes">
            <div class="chart-container" v-if="analysisData.price_changes">
              <!-- 价格变化总体趋势 -->
              <div class="price-change-summary analysis-card">
                <h4>价格变化趋势</h4>
                <div class="summary-stats">
                  <div class="stat-item">
                    <div class="stat-value">{{ priceChangeSummary.increaseCount }}</div>
                    <div class="stat-label">上涨房源数</div>
                  </div>
                  <div class="stat-item">
                    <div class="stat-value">{{ priceChangeSummary.decreaseCount }}</div>
                    <div class="stat-label">下跌房源数</div>
                  </div>
                  <div class="stat-item">
                    <div class="stat-value">{{ priceChangeSummary.unchangedCount }}</div>
                    <div class="stat-label">价格不变</div>
                  </div>
                  <div class="stat-item">
                    <div class="stat-value" :class="{'price-increase': priceChangeSummary.avgIncrease > 0, 'price-decrease': priceChangeSummary.avgIncrease < 0}">
                      {{ priceChangeSummary.avgIncrease > 0 ? '+' : '' }}{{ priceChangeSummary.avgIncrease }}
                    </div>
                    <div class="stat-label">平均涨跌金额</div>
                  </div>
                  <div class="stat-item">
                    <div class="stat-value" :class="{'price-increase': priceChangeSummary.avgIncreasePercent > 0, 'price-decrease': priceChangeSummary.avgIncreasePercent < 0}">
                      {{ priceChangeSummary.avgIncreasePercent > 0 ? '+' : '' }}{{ priceChangeSummary.avgIncreasePercent }}%
                    </div>
                    <div class="stat-label">平均涨跌幅度</div>
                  </div>
                </div>
              </div>
              
              <!-- 价格变化分布饼图 -->
              <div class="chart-row">
                <div class="chart-column">
                  <div id="price-change-pie-chart" class="chart"></div>
                </div>
                <div class="chart-column">
                  <div id="district-price-change-chart" class="chart"></div>
                </div>
              </div>
              
              <!-- 按区域统计价格变化 -->
              <div class="analysis-card">
                <h4>区域价格变化</h4>
                <el-table :data="districtChanges" style="width: 100%" :default-sort="{prop: 'increaseCount', order: 'descending'}" stripe>
                  <el-table-column prop="location_qu" label="区域" width="120"></el-table-column>
                  <el-table-column prop="increaseCount" label="上涨房源" sortable width="100"></el-table-column>
                  <el-table-column prop="decreaseCount" label="下跌房源" sortable width="100"></el-table-column>
                  <el-table-column prop="avgIncrease" label="平均涨幅" sortable width="100">
                    <template #default="scope">
                      <span :class="{'price-increase': scope.row.avgIncrease > 0, 'price-decrease': scope.row.avgIncrease < 0}">
                        {{ scope.row.avgIncrease > 0 ? '+' : '' }}{{ scope.row.avgIncrease }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="avgIncreasePercent" label="平均涨幅%" sortable width="100">
                    <template #default="scope">
                      <span :class="{'price-increase': scope.row.avgIncreasePercent > 0, 'price-decrease': scope.row.avgIncreasePercent < 0}">
                        {{ scope.row.avgIncreasePercent > 0 ? '+' : '' }}{{ scope.row.avgIncreasePercent }}%
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="totalCount" label="总房源数" sortable width="100"></el-table-column>
                </el-table>
              </div>
              
              <!-- 价格变化详情表格 -->
              <div class="analysis-card">
                <h4>价格变化详情 <small>(显示前50条)</small></h4>
                <el-table :data="priceChangeDetails" style="width: 100%" :default-sort="{prop: 'priceChangePercent', order: 'descending'}" height="400" stripe>
                  <el-table-column prop="title" label="房源标题" min-width="200"></el-table-column>
                  <el-table-column prop="locationQu" label="区域" width="100"></el-table-column>
                  <el-table-column prop="locationSmall" label="小区" width="120"></el-table-column>
                  <el-table-column prop="prevPrice" label="前次价格" width="100"></el-table-column>
                  <el-table-column prop="price" label="当前价格" width="100"></el-table-column>
                  <el-table-column prop="priceChange" label="变化金额" width="100">
                    <template #default="scope">
                      <span :class="{'price-increase': scope.row.priceChange > 0, 'price-decrease': scope.row.priceChange < 0}">
                        {{ scope.row.priceChange > 0 ? '+' : '' }}{{ scope.row.priceChange }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="priceChangePercent" label="变化百分比" sortable width="120">
                    <template #default="scope">
                      <span :class="{'price-increase': scope.row.priceChangePercent > 0, 'price-decrease': scope.row.priceChangePercent < 0}">
                        {{ scope.row.priceChangePercent > 0 ? '+' : '' }}{{ scope.row.priceChangePercent }}%
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="date" label="更新日期" width="120"></el-table-column>
                </el-table>
              </div>
            </div>
            <el-empty v-else description="暂无价格变化数据。需要至少两次爬取数据才能分析价格变化。" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, onMounted, watch, onUnmounted, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { useRoute } from 'vue-router';
import api from '../api/api';
import * as echarts from 'echarts';

export default {
  name: 'AnalysisResults',
  
  setup() {
    const route = useRoute();
    
    // 加载状态
    const loading = ref(false);
    const analysisLoading = ref(false);
    
    // 城市相关
    const cities = ref({});
    const selectedCity = ref('');
    
    // 当前标签页
    const activeTab = ref('district_analysis');
    
    // 图表实例
    const charts = reactive({});
    
    // 数据分析结果
    const analysisData = reactive({
      district_analysis: null,
      room_type_analysis: null,
      direction_analysis: null,
      floor_analysis: null,
      price_distribution: null,
      community_analysis: null,
      price_stats: null,
      room_price_cross: null,
      rental_efficiency: null,
      price_trend: null,
      price_changes: null,
      features_analysis: null,
      feature_combinations: null,
      metro_price_impact: null,
      popular_features_price: null
    });
    
    // 分析时间
    const analysisTime = reactive({
      district_analysis: null,
      room_type_analysis: null,
      direction_analysis: null,
      floor_analysis: null,
      price_distribution: null,
      community_analysis: null,
      price_stats: null,
      room_price_cross: null,
      rental_efficiency: null,
      price_trend: null,
      price_changes: null,
      features_analysis: null,
      feature_combinations: null,
      metro_price_impact: null,
      popular_features_price: null
    });
    
    // 概览数据
    const summaryData = ref(null);
    
    // 价格变化分析相关
    const priceChangeSummary = computed(() => {
      if (!analysisData.price_changes) return { 
        increaseCount: 0, 
        decreaseCount: 0, 
        unchangedCount: 0, 
        avgIncrease: 0, 
        avgIncreasePercent: 0
      };
      return analysisData.price_changes.summary || {};
    });
    
    const districtChanges = ref([]);
    const priceChangeDetails = ref([]);
    
    // 格式化分析时间
    const formatAnalysisTime = (timeString) => {
      if (!timeString) return '';
      const date = new Date(timeString);
      return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
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
    
    // 城市变化处理
    const handleCityChange = () => {
      fetchData();
    };
    
    // 标签页切换处理
    const handleTabClick = () => {
      console.log('切换到标签页:', activeTab.value);
      
      // 确保先清理旧图表实例，防止内存泄漏
      try {
        // 根据不同标签页清理对应的图表
        switch (activeTab.value) {
          case 'district_analysis':
            ['district-price-chart', 'district-count-chart'].forEach(id => {
              if (charts[id]) {
                charts[id].dispose();
                charts[id] = null;
              }
            });
            break;
          case 'room_type_analysis':
            ['room-type-price-chart', 'room-type-count-chart'].forEach(id => {
              if (charts[id]) {
                charts[id].dispose();
                charts[id] = null;
              }
            });
            break;
          case 'direction_analysis':
            if (charts['direction-chart']) {
              charts['direction-chart'].dispose();
              charts['direction-chart'] = null;
            }
            break;
          case 'floor_analysis':
            if (charts['floor-chart']) {
              charts['floor-chart'].dispose();
              charts['floor-chart'] = null;
            }
            break;
          case 'price_distribution':
            if (charts['price-distribution-chart']) {
              charts['price-distribution-chart'].dispose();
              charts['price-distribution-chart'] = null;
            }
            break;
          case 'community_analysis':
            if (charts['community-chart']) {
              charts['community-chart'].dispose();
              charts['community-chart'] = null;
            }
            break;
          case 'price_stats':
            if (charts['boxplot-chart']) {
              charts['boxplot-chart'].dispose();
              charts['boxplot-chart'] = null;
            }
            break;
          case 'room_price_cross':
            if (charts['room-price-cross-chart']) {
              charts['room-price-cross-chart'].dispose();
              charts['room-price-cross-chart'] = null;
            }
            break;
          case 'rental_efficiency':
            if (charts['rental-efficiency-chart']) {
              charts['rental-efficiency-chart'].dispose();
              charts['rental-efficiency-chart'] = null;
            }
            break;
          case 'price_trend':
            if (charts['price-trend-chart']) {
              charts['price-trend-chart'].dispose();
              charts['price-trend-chart'] = null;
            }
            break;
          case 'price_changes':
            ['price-change-pie-chart', 'district-price-change-chart'].forEach(id => {
              if (charts[id]) {
                charts[id].dispose();
                charts[id] = null;
              }
            });
            break;
          case 'features_analysis':
            if (charts['features-chart']) {
              charts['features-chart'].dispose();
              charts['features-chart'] = null;
            }
            break;
          case 'feature_combinations':
            if (charts['feature-combo-table']) {
              charts['feature-combo-table'].dispose();
              charts['feature-combo-table'] = null;
            }
            break;
          case 'metro_price_impact':
            if (charts['metro-impact-chart']) {
              charts['metro-impact-chart'].dispose();
              charts['metro-impact-chart'] = null;
            }
            break;
          case 'popular_features_price':
            if (charts['popular-features-chart']) {
              charts['popular-features-chart'].dispose();
              charts['popular-features-chart'] = null;
            }
            break;
        }
      } catch (error) {
        console.error('清理旧图表实例时出错:', error);
      }
      
      // 延迟一下，确保DOM已经更新
      setTimeout(() => {
        try {
        renderCharts();
        } catch (error) {
          console.error('标签页切换后渲染图表失败:', error);
          
          // 尝试再次渲染，有时DOM需要更长时间来更新
          setTimeout(() => {
            try {
              console.log('尝试第二次渲染图表:', activeTab.value);
              renderCharts();
            } catch (retryError) {
              console.error('图表第二次渲染尝试也失败:', retryError);
            }
          }, 500);
        }
      }, 100);
    };
    
    // 获取概览数据
    const fetchSummaryData = async () => {
      try {
        const params = {};
        if (selectedCity.value) {
          params.city = selectedCity.value;
        }
        
        summaryData.value = await api.getSummaryStatistics(selectedCity.value);
        
        // 添加详细日志，检查返回的数据结构
        console.log('获取到概览数据:', summaryData.value);
        
        // 专门检查district_distribution字段
        if (summaryData.value && summaryData.value.district_distribution) {
          console.log('区域分布数据:', summaryData.value.district_distribution);
          if (Array.isArray(summaryData.value.district_distribution) && 
              summaryData.value.district_distribution.length > 0) {
            console.log('第一个区域:', summaryData.value.district_distribution[0]);
            console.log('区域名称字段:', summaryData.value.district_distribution[0].district);
          } else {
            console.log('区域分布数组为空或不是数组');
          }
        } else {
          console.log('无区域分布数据');
        }
      } catch (error) {
        console.error('获取概览数据失败', error);
      }
    };
    
    // 获取分析结果
    const fetchAnalysisResult = async (analysisType, skipLoading = false) => {
      try {
        if (!skipLoading) {
          loading.value = true;
        }
        
        // 构建请求参数
        const params = {
          analysis_type: analysisType
        };
        
        if (selectedCity.value) {
          params.city = selectedCity.value;
        }
        
        // 获取分析结果
        const response = await api.getAnalysisResults(params);
        
        if (response && response.length > 0) {
          // 保存分析时间
          analysisTime[analysisType] = response[0].analysis_time;
          
          // 处理不同类型的分析结果
          if (analysisType === 'price_changes') {
            // 价格变化分析需要特殊处理
            await fetchPriceChangesData();
          } else {
            // 其他分析结果处理
            if (typeof response[0].result_data === 'string') {
              // 如果是字符串，需要解析
              analysisData[analysisType] = JSON.parse(response[0].result_data);
            } else {
              // 如果已经是对象，直接使用
              analysisData[analysisType] = response[0].result_data;
            }
          }
        } else {
          analysisData[analysisType] = null;
          analysisTime[analysisType] = null;
        }
      } catch (error) {
        console.error(`获取${analysisType}数据失败:`, error);
        analysisData[analysisType] = null;
        analysisTime[analysisType] = null;
      } finally {
        if (!skipLoading) {
          loading.value = false;
        }
      }
    };
    
    // 获取数据
    const fetchData = async () => {
      try {
        loading.value = true;
        
        // 获取概览数据
        await fetchSummaryData();
        console.log('概览数据获取完成:', summaryData.value);
        // 获取各类分析结果
        await Promise.all([
          fetchAnalysisResult('district_analysis'),
          fetchAnalysisResult('room_type_analysis'),
          fetchAnalysisResult('direction_analysis'),
          fetchAnalysisResult('floor_analysis'),
          fetchAnalysisResult('price_distribution'),
          fetchAnalysisResult('community_analysis'),
          fetchAnalysisResult('price_stats'),
          fetchAnalysisResult('room_price_cross'),
          fetchAnalysisResult('rental_efficiency'),
          fetchAnalysisResult('price_trend'),
          fetchAnalysisResult('price_changes'),
          fetchAnalysisResult('features_analysis'),
          fetchAnalysisResult('feature_combinations'),
          fetchAnalysisResult('metro_price_impact'),
          fetchAnalysisResult('popular_features_price')
        ]);
        
        loading.value = false;
        console.log('所有数据获取完成');
        // 延迟渲染图表，确保DOM已更新
        setTimeout(() => {
          console.log('开始渲染图表:', activeTab.value);
        renderCharts();
        }, 300);
      } catch (error) {
        loading.value = false;
        ElMessage.error('获取分析数据失败');
        console.error(error);
      }
    };
    
    // 获取价格变化分析数据
    const fetchPriceChangesData = async () => {
      try {
        if (!selectedCity.value) return;
        
        // 获取不同部分的价格变化分析结果
        const [distributionResponse, districtResponse, detailsResponse] = await Promise.all([
          api.getAnalysisResults({
            analysis_type: 'price_changes_percent_distribution',
            city: selectedCity.value
          }),
          api.getAnalysisResults({
            analysis_type: 'price_changes_district_summary',
            city: selectedCity.value
          }),
          api.getAnalysisResults({
            analysis_type: 'price_changes_detailed_changes',
            city: selectedCity.value
          })
        ]);
        
        // 如果没有数据，返回
        if (!distributionResponse || distributionResponse.length === 0) {
          analysisData.price_changes = null;
          return;
        }
        
        // 保存分析时间
        analysisTime.price_changes = distributionResponse[0].analysis_time;
        
        // 解析百分比分布数据
        const distribution = distributionResponse[0] ? JSON.parse(distributionResponse[0].result_data) : [];
        
        // 处理区域汇总数据
        let districtData = [];
        if (districtResponse && districtResponse.length > 0) {
          const rawData = JSON.parse(districtResponse[0].result_data);
          districtData = rawData.map(item => ({
            location_qu: item.location_qu,
            increaseCount: item.increase_count || 0,
            decreaseCount: item.decrease_count || 0,
            unchangedCount: item.unchanged_count || 0,
            avgIncrease: parseFloat((item.avg_increase || 0).toFixed(2)),
            avgDecrease: parseFloat((item.avg_decrease || 0).toFixed(2)),
            avgIncreasePercent: parseFloat((item.avg_increase_percent || 0).toFixed(2)),
            avgDecreasePercent: parseFloat((item.avg_decrease_percent || 0).toFixed(2)),
            totalCount: item.total_count || 0
          }));
        }
        
        // 计算总体统计
        let increaseCount = 0;
        let decreaseCount = 0;
        let unchangedCount = 0;
        let sumIncrease = 0;
        let sumIncreasePercent = 0;
        let increaseItems = 0;
        
        districtData.forEach(district => {
          increaseCount += district.increaseCount;
          decreaseCount += district.decreaseCount;
          unchangedCount += district.unchangedCount;
          
          if (district.increaseCount > 0 && district.avgIncrease) {
            sumIncrease += district.avgIncrease * district.increaseCount;
            sumIncreasePercent += district.avgIncreasePercent * district.increaseCount;
            increaseItems += district.increaseCount;
          }
        });
        
        const summary = {
          increaseCount,
          decreaseCount,
          unchangedCount,
          avgIncrease: increaseItems > 0 ? parseFloat((sumIncrease / increaseItems).toFixed(2)) : 0,
          avgIncreasePercent: increaseItems > 0 ? parseFloat((sumIncreasePercent / increaseItems).toFixed(2)) : 0
        };
        
        // 处理详细记录
        let details = [];
        if (detailsResponse && detailsResponse.length > 0) {
          const rawDetails = JSON.parse(detailsResponse[0].result_data);
          details = rawDetails.slice(0, 50).map(item => ({
            houseId: item.house_id,
            title: item.title,
            locationQu: item.location_qu,
            locationSmall: item.location_small,
            prevPrice: item.prev_price,
            price: item.price,
            priceChange: item.price_change,
            priceChangePercent: parseFloat((item.price_change_percent || 0).toFixed(2)),
            prevDate: item.prev_date,
            date: item.date,
            priceChangeCategory: item.price_change_category
          }));
        }
        
        // 组装价格变化分析结果
        analysisData.price_changes = {
          distribution,
          district_changes: districtData,
          details,
          summary
        };
      } catch (error) {
        console.error('获取价格变化数据失败:', error);
        analysisData.price_changes = null;
      }
    };
    
    // 刷新数据
    const refreshData = () => {
      fetchData();
    };
    
    // 获取热门区域
    const getTopDistrict = () => {
      try {
        if (!summaryData.value) return '暂无数据';
        if (!summaryData.value.district_distribution) return '暂无数据';
        if (!Array.isArray(summaryData.value.district_distribution)) return '暂无数据';
        if (summaryData.value.district_distribution.length === 0) return '暂无数据';
        
        const topDistrict = summaryData.value.district_distribution[0];
        return topDistrict.district || '未知区域';
      } catch (error) {
        console.error('获取热门区域失败:', error);
        return '暂无数据';
      }
    };
    
    // 渲染所有图表
    const renderCharts = () => {
      switch (activeTab.value) {
        case 'district_analysis':
          renderDistrictAnalysisCharts();
          break;
        case 'room_type_analysis':
          renderRoomTypeAnalysisCharts();
          break;
        case 'direction_analysis':
          renderDirectionAnalysisChart();
          break;
        case 'floor_analysis':
          renderFloorAnalysisChart();
          break;
        case 'price_distribution':
          renderPriceDistributionChart();
          break;
        case 'community_analysis':
          renderCommunityAnalysisChart();
          break;
        case 'price_stats':
          renderPriceStatsChart();
          break;
        case 'room_price_cross':
          renderRoomPriceCrossChart();
          break;
        case 'rental_efficiency':
          renderRentalEfficiencyChart();
          break;
        case 'price_trend':
          renderPriceTrendChart();
          break;
        case 'price_changes':
          renderPriceChangesChart();
          break;
        case 'features_analysis':
          renderFeaturesAnalysisChart();
          break;
        case 'feature_combinations':
          renderFeatureCombinationsChart();
          break;
        case 'metro_price_impact':
          renderMetroPriceImpactChart();
          break;
        case 'popular_features_price':
          renderPopularFeaturesPriceChart();
          break;
      }
    };
    
    // 渲染区域分析图表
    const renderDistrictAnalysisCharts = () => {
      if (!analysisData.district_analysis) return;
      
      // 区域-价格图表
      renderChart({
        elementId: 'district-price-chart',
        title: '各区域平均租金',
        data: analysisData.district_analysis,
        xKey: 'location_qu',
        yKey: 'avg_price',
        type: 'bar'
      });
      
      // 区域-数量图表
      renderChart({
        elementId: 'district-count-chart',
        title: '各区域房源数量',
        data: analysisData.district_analysis,
        xKey: 'location_qu',
        yKey: 'house_count',
        type: 'bar'
      });
    };
    
    // 渲染户型分析图表
    const renderRoomTypeAnalysisCharts = () => {
      if (!analysisData.room_type_analysis) return;
      
      // 户型-价格图表
      renderChart({
        elementId: 'room-type-price-chart',
        title: '各户型平均租金',
        data: analysisData.room_type_analysis,
        xKey: 'room_type',
        yKey: 'avg_price',
        type: 'bar'
      });
      
      // 户型-数量图表
      renderChart({
        elementId: 'room-type-count-chart',
        title: '各户型房源数量',
        data: analysisData.room_type_analysis,
        xKey: 'room_type',
        yKey: 'house_count',
        type: 'bar'
      });
    };
    
    // 渲染朝向分析图表
    const renderDirectionAnalysisChart = () => {
      if (!analysisData.direction_analysis) return;
      
      renderChart({
        elementId: 'direction-chart',
        title: '各朝向平均租金',
        data: analysisData.direction_analysis,
        xKey: 'direction',
        yKey: 'avg_price',
        type: 'bar'
      });
    };
    
    // 渲染楼层分析图表
    const renderFloorAnalysisChart = () => {
      if (!analysisData.floor_analysis) return;
      
      renderChart({
        elementId: 'floor-chart',
        title: '各楼层平均租金',
        data: analysisData.floor_analysis,
        xKey: 'floor_type',
        yKey: 'avg_price',
        type: 'bar'
      });
    };
    
    // 渲染租金分布图表
    const renderPriceDistributionChart = () => {
      if (!analysisData.price_distribution) return;
      
      renderChart({
        elementId: 'price-distribution-chart',
        title: '租金价格分布',
        data: analysisData.price_distribution,
        xKey: 'price_range',
        yKey: 'house_count',
        type: 'bar'
      });
    };
    
    // 渲染小区分析图表
    const renderCommunityAnalysisChart = () => {
      if (!analysisData.community_analysis) return;
      
      // 只展示前15个小区
      const topCommunities = analysisData.community_analysis.slice(0, 15);
      
      renderChart({
        elementId: 'community-chart',
        title: '热门小区平均租金',
        data: topCommunities,
        xKey: 'location_small',
        yKey: 'avg_price',
        type: 'bar'
      });
    };
    
    // 渲染价格统计图表
    const renderPriceStatsChart = () => {
      if (!analysisData.price_stats) return;
      
      const chartDom = document.getElementById('boxplot-chart');
      if (!chartDom) return;
      
      // 如果已存在图表实例，则销毁
      if (charts['boxplot-chart']) {
        charts['boxplot-chart'].dispose();
      }
      
      // 创建新的图表实例
      charts['boxplot-chart'] = echarts.init(chartDom);
      
      // 准备数据
      const districts = analysisData.price_stats.map(item => item.location_qu);
      const boxplotData = analysisData.price_stats.map(item => [
        item.price_min,        // 最小值
        item.price_25th,       // 第一四分位数
        item.price_median,     // 中位数
        item.price_75th,       // 第三四分位数
        item.price_max         // 最大值
      ]);
      
      // 箱型图配置
      const option = {
        title: {
          text: '各区域租金价格分布',
          left: 'center'
        },
        tooltip: {
          trigger: 'item',
          formatter: function(params) {
            return `${params.name}<br/>
                    最小值: ${params.data[0]}元<br/>
                    25%分位: ${params.data[1]}元<br/>
                    中位数: ${params.data[2]}元<br/>
                    75%分位: ${params.data[3]}元<br/>
                    最大值: ${params.data[4]}元`;
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: districts,
          axisLabel: {
            interval: 0,
            rotate: 30
          }
        },
        yAxis: {
          type: 'value',
          name: '租金(元/月)'
        },
        series: [
          {
            name: '租金统计',
            type: 'boxplot',
            data: boxplotData,
            itemStyle: {
              borderWidth: 1.5
            }
          }
        ]
      };
      
      // 渲染图表
      charts['boxplot-chart'].setOption(option);
      
      // 窗口大小变化时自动调整图表大小
      window.addEventListener('resize', () => {
        charts['boxplot-chart'].resize();
      });
    };
    
    // 渲染户型价格交叉图表 - 热力图形式
    const renderRoomPriceCrossChart = () => {
      if (!analysisData.room_price_cross || !Array.isArray(analysisData.room_price_cross) || analysisData.room_price_cross.length === 0) {
        console.warn('户型价格交叉分析数据为空或格式不正确');
        return;
      }
      
      const chartDom = document.getElementById('room-price-cross-chart');
      if (!chartDom) {
        console.error('找不到DOM元素: room-price-cross-chart');
        return;
      }
      
      // 如果已存在图表实例，则销毁
      if (charts['room-price-cross-chart']) {
        charts['room-price-cross-chart'].dispose();
      }
      
      // 创建新的图表实例
      charts['room-price-cross-chart'] = echarts.init(chartDom);
      
      // 准备数据
      const roomTypes = [...new Set(analysisData.room_price_cross.map(item => item.room_type))];
      const priceRanges = [...new Set(analysisData.room_price_cross.map(item => item.price_range))];
      
      if (roomTypes.length === 0 || priceRanges.length === 0) {
        console.warn('户型或价格区间数据为空');
        return;
      }
      
      // 创建热力图数据
      const heatmapData = [];
      analysisData.room_price_cross.forEach(item => {
        if (item.room_type && item.price_range) {
          const roomTypeIndex = roomTypes.indexOf(item.room_type);
          const priceRangeIndex = priceRanges.indexOf(item.price_range);
          if (roomTypeIndex !== -1 && priceRangeIndex !== -1) {
            heatmapData.push([roomTypeIndex, priceRangeIndex, item.house_count || 0]);
          }
        }
      });
      
      if (heatmapData.length === 0) {
        console.warn('热力图数据为空');
        return;
      }
      
      // 热力图配置
      const option = {
        title: {
          text: '户型与价格区间分布',
          left: 'center'
        },
        tooltip: {
          position: 'top',
          formatter: function(params) {
            return `${roomTypes[params.data[0]]} / ${priceRanges[params.data[1]]}<br/>
                    房源数量: ${params.data[2]}<br/>`;
          }
        },
        grid: {
          left: '3%',
          right: '7%',
          bottom: '12%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: roomTypes,
          splitArea: {
            show: true
          }
        },
        yAxis: {
          type: 'category',
          data: priceRanges,
          splitArea: {
            show: true
          }
        },
        visualMap: {
          min: 0,
          max: Math.max(...heatmapData.map(item => item[2]), 1),
          calculable: true,
          orient: 'horizontal',
          left: 'center',
          bottom: '0%'
        },
        series: [
          {
            name: '房源数量',
            type: 'heatmap',
            data: heatmapData,
            label: {
              show: true
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }
        ]
      };
      
      // 渲染图表
      try {
        charts['room-price-cross-chart'].setOption(option);
        console.log('户型价格交叉图表渲染成功');
      } catch (error) {
        console.error('户型价格交叉图表渲染失败:', error);
      }
    };
    
    // 渲染租金效率图表
    const renderRentalEfficiencyChart = () => {
      if (!analysisData.rental_efficiency) return;
      
      const chartDom = document.getElementById('rental-efficiency-chart');
      if (!chartDom) return;
      
      // 如果已存在图表实例，则销毁
      if (charts['rental-efficiency-chart']) {
        charts['rental-efficiency-chart'].dispose();
      }
      
      // 创建新的图表实例
      charts['rental-efficiency-chart'] = echarts.init(chartDom);
      
      // 准备数据
      const sizeRanges = analysisData.rental_efficiency.map(item => item.size_range);
      const avgUnitPrices = analysisData.rental_efficiency.map(item => item.avg_unit_price);
      const avgPrices = analysisData.rental_efficiency.map(item => item.avg_price);
      
      // 双Y轴图表配置
      const option = {
        title: {
          text: '不同面积段的租金效率分析',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          }
        },
        legend: {
          data: ['单位面积租金(元/㎡/月)', '平均租金(元/月)'],
          top: 30
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: sizeRanges,
          axisLabel: {
            interval: 0,
            rotate: 30
          }
        },
        yAxis: [
          {
            type: 'value',
            name: '单位面积租金(元/㎡/月)',
            position: 'left'
          },
          {
            type: 'value',
            name: '平均租金(元/月)',
            position: 'right'
          }
        ],
        series: [
          {
            name: '单位面积租金(元/㎡/月)',
            type: 'bar',
            data: avgUnitPrices
          },
          {
            name: '平均租金(元/月)',
            type: 'line',
            yAxisIndex: 1,
            data: avgPrices,
            symbol: 'circle',
            symbolSize: 8,
            lineStyle: {
              width: 3
            }
          }
        ]
      };
      
      // 渲染图表
      try {
        charts['rental-efficiency-chart'].setOption(option);
        console.log('租金效率图表渲染成功');
      } catch (error) {
        console.error('租金效率图表渲染失败:', error);
        try {
          // 尝试使用简化配置
          const simpleOption = {
            title: { text: '不同面积段的租金效率分析' },
            xAxis: { type: 'category', data: sizeRanges },
            yAxis: { type: 'value' },
            series: [{
              name: '单位面积租金',
              type: 'bar',
              data: avgUnitPrices
            }]
          };
          charts['rental-efficiency-chart'].setOption(simpleOption);
          console.log('租金效率图表使用简化配置渲染成功');
        } catch (e) {
          console.error('租金效率图表简化配置也渲染失败:', e);
        }
      }

      // 窗口大小变化时自动调整图表大小
      window.addEventListener('resize', () => {
        if (charts['rental-efficiency-chart']) {
          charts['rental-efficiency-chart'].resize();
        }
      });
    };
    
    // 渲染价格趋势图表
    const renderPriceTrendChart = () => {
      if (!analysisData.price_trend) return;
      
      const chartDom = document.getElementById('price-trend-chart');
      if (!chartDom) return;
      
      // 如果已存在图表实例，则销毁
      if (charts['price-trend-chart']) {
        charts['price-trend-chart'].dispose();
      }
      
      // 创建新的图表实例
      charts['price-trend-chart'] = echarts.init(chartDom);
      
      // 获取所有不同的区域
      const districts = [...new Set(analysisData.price_trend.map(item => item.location_qu))];
      
      // 按区域分组数据
      const seriesData = districts.map(district => {
        const districtData = analysisData.price_trend
          .filter(item => item.location_qu === district)
          .sort((a, b) => new Date(a.crawl_date) - new Date(b.crawl_date));
        
        return {
          name: district,
          type: 'line',
          data: districtData.map(item => [item.crawl_date, item.avg_price]),
          smooth: true,
          symbol: 'circle',
          symbolSize: 6
        };
      });
      
      // 线图配置
      const option = {
        title: {
          text: '租金价格趋势',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          formatter: function(params) {
            const date = new Date(params[0].value[0]).toLocaleDateString();
            let result = `${date}<br/>`;
            params.forEach(param => {
              result += `${param.seriesName}: ${param.value[1]}元<br/>`;
            });
            return result;
          }
        },
        legend: {
          data: districts,
          top: 30
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'time',
          axisLabel: {
            formatter: '{MM}-{dd}'
          }
        },
        yAxis: {
          type: 'value',
          name: '平均租金(元/月)'
        },
        series: seriesData
      };
      
      // 渲染图表
      try {
        charts['price-trend-chart'].setOption(option);
        console.log('价格趋势图表渲染成功');
      } catch (error) {
        console.error('价格趋势图表渲染失败:', error);
        try {
          // 尝试使用简化配置
          const simpleOption = {
            title: { text: '租金价格趋势' },
            xAxis: { type: 'time' },
            yAxis: { type: 'value' },
            series: seriesData.map(s => ({
              name: s.name,
              type: 'line',
              data: s.data
            }))
          };
          charts['price-trend-chart'].setOption(simpleOption);
          console.log('价格趋势图表使用简化配置渲染成功');
        } catch (e) {
          console.error('价格趋势图表简化配置也渲染失败:', e);
        }
      }

      // 窗口大小变化时自动调整图表大小
      window.addEventListener('resize', () => {
        if (charts['price-trend-chart']) {
          charts['price-trend-chart'].resize();
        }
      });
    };
    
    // 渲染价格变化分析图表
    const renderPriceChangesChart = () => {
      if (!analysisData.price_changes) return;
      
      // 价格变化总体趋势
      priceChangeSummary.value = analysisData.price_changes.summary || {};
      
      // 价格变化分布饼图
      if (analysisData.price_changes.distribution && 
          Array.isArray(analysisData.price_changes.distribution) && 
          analysisData.price_changes.distribution.length > 0) {
        renderPieChart({
          elementId: 'price-change-pie-chart',
          title: '价格变化分布',
          data: analysisData.price_changes.distribution,
          xKey: 'price_range',
          yKey: 'house_count',
          type: 'pie'
        });
      } else {
        console.warn('价格变化分布数据为空或格式不正确');
      }
      
      // 区域价格变化图表
      if (analysisData.price_changes.district_changes && 
          Array.isArray(analysisData.price_changes.district_changes) && 
          analysisData.price_changes.district_changes.length > 0) {
        
        const chartDom = document.getElementById('district-price-change-chart');
        if (chartDom) {
          if (charts['district-price-change-chart']) {
            charts['district-price-change-chart'].dispose();
          }
          charts['district-price-change-chart'] = echarts.init(chartDom);
          
          const districts = analysisData.price_changes.district_changes.map(item => item.location_qu);
          const increaseData = analysisData.price_changes.district_changes.map(item => item.increaseCount);
          const decreaseData = analysisData.price_changes.district_changes.map(item => item.decreaseCount);
          
          const option = {
            title: {
              text: '各区域价格变化情况',
              left: 'center'
            },
            tooltip: {
              trigger: 'axis',
              axisPointer: {
                type: 'shadow'
              }
            },
            legend: {
              data: ['上涨房源', '下跌房源'],
              top: 30
            },
            grid: {
              left: '3%',
              right: '4%',
              bottom: '3%',
              containLabel: true
            },
            xAxis: {
              type: 'category',
              data: districts,
              axisLabel: {
                interval: 0,
                rotate: 30
              }
            },
            yAxis: {
              type: 'value'
            },
            series: [
              {
                name: '上涨房源',
                type: 'bar',
                stack: '总量',
                data: increaseData
              },
              {
                name: '下跌房源',
                type: 'bar',
                stack: '总量',
                data: decreaseData
              }
            ]
          };
          
          try {
            charts['district-price-change-chart'].setOption(option);
            console.log('区域价格变化图表渲染成功');
          } catch (error) {
            console.error('渲染区域价格变化图表失败:', error);
            try {
              // 尝试使用简化配置
              const simpleOption = {
                title: { text: '各区域价格变化情况' },
                xAxis: { type: 'category', data: districts },
                yAxis: { type: 'value' },
                series: [
                  {
                    name: '上涨房源',
                    type: 'bar',
                    data: increaseData
                  },
                  {
                    name: '下跌房源',
                    type: 'bar',
                    data: decreaseData
                  }
                ]
              };
              charts['district-price-change-chart'].setOption(simpleOption);
              console.log('区域价格变化图表使用简化配置渲染成功');
            } catch (e) {
              console.error('区域价格变化图表简化配置也渲染失败:', e);
            }
          }
        }
      }
      
      // 按区域统计价格变化
      districtChanges.value = analysisData.price_changes.district_changes || [];
      
      // 价格变化详情表格
      priceChangeDetails.value = analysisData.price_changes.details || [];
    };
    
    // 渲染特征分析图表
    const renderFeaturesAnalysisChart = () => {
      if (!analysisData.features_analysis) return;
      
      renderPieChart({
        elementId: 'features-chart',
        title: '特征标签分析',
        data: analysisData.features_analysis,
        xKey: 'feature',
        yKey: 'count',
        type: 'pie'
      });
    };
    
    // 渲染特征组合分析图表
    const renderFeatureCombinationsChart = () => {
      if (!analysisData.feature_combinations) return;
      
      renderPieChart({
        elementId: 'feature-combo-table',
        title: '特征组合分析',
        data: analysisData.feature_combinations,
        xKey: 'features',
        yKey: 'count',
        type: 'pie'
      });
    };
    
    // 渲染地铁影响分析图表
    const renderMetroPriceImpactChart = () => {
      if (!analysisData.metro_price_impact) return;
      
      renderPieChart({
        elementId: 'metro-impact-chart',
        title: '地铁影响分析',
        data: analysisData.metro_price_impact,
        xKey: 'location_qu',
        yKey: 'percentage',
        type: 'pie'
      });
    };
    
    // 渲染热门特征价格影响图表
    const renderPopularFeaturesPriceChart = () => {
      if (!analysisData.popular_features_price) return;
      
      renderPieChart({
        elementId: 'popular-features-chart',
        title: '热门特征价格影响',
        data: analysisData.popular_features_price,
        xKey: 'feature',
        yKey: 'percentage',
        type: 'pie'
      });
    };
    
    // 通用图表渲染函数
    const renderChart = ({ elementId, title, data, xKey, yKey, type = 'bar', secondYKey = null }) => {
      try {
      const chartDom = document.getElementById(elementId);
        if (!chartDom) {
          console.error(`找不到DOM元素: ${elementId}`);
          return;
        }
        
        // 验证数据是否有效
        if (!data || !Array.isArray(data) || data.length === 0) {
          console.error(`${elementId} 没有有效数据`, data);
          return;
        }
      
      // 如果已存在图表实例，则销毁
      if (charts[elementId]) {
        charts[elementId].dispose();
      }
      
      // 创建新的图表实例
      charts[elementId] = echarts.init(chartDom);
      
      // 准备数据
        const xAxis = data.map(item => item[xKey] || '未知');
        const seriesData = data.map(item => item[yKey] || 0);
      
      // 图表配置
      const option = {
        title: {
          text: title,
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow'
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: xAxis,
          axisLabel: {
            interval: 0,
            rotate: 30
          }
        },
        yAxis: {
          type: 'value'
        },
        series: [
          {
              name: yKey === 'avg_price' ? '平均租金' : 
                    yKey === 'house_count' ? '房源数量' : 
                    yKey === 'avg_unit_price' ? '单位面积租金' : yKey,
            type: type,
            data: seriesData
          }
        ]
      };
        
        // 如果提供了第二个Y轴数据，添加到图表中
        if (secondYKey) {
          const secondSeriesData = data.map(item => item[secondYKey] || 0);
          option.yAxis = [
            { type: 'value', name: yKey },
            { type: 'value', name: secondYKey }
          ];
          option.series.push({
            name: secondYKey,
            type: type,
            yAxisIndex: 1,
            data: secondSeriesData
          });
        }
        
        // 对特定图表类型进行配置调整
        if (elementId === 'price-trend-chart') {
          option.xAxis.type = 'time';
          option.series[0].smooth = true;
          option.series[0].symbolSize = 6;
        }
      
      // 渲染图表
      charts[elementId].setOption(option);
        console.log(`${elementId} 图表渲染成功`);
      } catch (error) {
        console.error(`${elementId} 图表渲染失败:`, error);
      }
    };
    
    // 渲染饼图
    const renderPieChart = ({ elementId, title, data, xKey, yKey, type = 'pie' }) => {
      try {
        const chartDom = document.getElementById(elementId);
        if (!chartDom) {
          console.error(`找不到DOM元素: ${elementId}`);
          return;
        }
        
        // 验证数据是否有效
        if (!data || !Array.isArray(data) || data.length === 0) {
          console.error(`${elementId} 没有有效数据`, data);
          return;
        }
        
        // 如果已存在图表实例，则销毁
        if (charts[elementId]) {
          charts[elementId].dispose();
        }
        
        // 创建新的图表实例
        charts[elementId] = echarts.init(chartDom);
        
        // 准备数据
        const seriesData = data.map(item => ({
          name: item[xKey] || '未知',
          value: item[yKey] || 0
        }));
        
        // 图表配置
        const option = {
          title: {
            text: title,
            left: 'center'
          },
          tooltip: {
            trigger: 'item',
            formatter: function(params) {
              return `${params.name}: ${params.value} (${params.percent}%)`;
            }
          },
          legend: {
            orient: 'vertical',
            left: 'left',
            data: seriesData.map(item => item.name)
          },
          series: [
            {
              name: title,
              type: type,
              radius: ['50%', '70%'],
              data: seriesData,
              label: {
                show: true,
                formatter: '{b}: {c} ({d}%)'
              },
              emphasis: {
                itemStyle: {
                  shadowBlur: 10,
                  shadowColor: 'rgba(0, 0, 0, 0.5)'
                }
              }
            }
          ]
        };
        
        // 渲染图表
        try {
          charts[elementId].setOption(option);
          console.log(`${elementId} 饼图渲染成功`);
        } catch (renderError) {
          console.error(`${elementId} 饼图渲染失败:`, renderError);
          
          // 尝试使用简化的配置
          try {
            const simpleOption = {
              title: { text: title },
              series: [{
                type: type,
                data: seriesData
              }]
            };
            charts[elementId].setOption(simpleOption);
            console.log(`${elementId} 使用简化配置渲染成功`);
          } catch (fallbackError) {
            console.error(`${elementId} 简化配置也渲染失败:`, fallbackError);
          }
        }
      } catch (error) {
        console.error(`${elementId} 饼图整体渲染失败:`, error);
      }
    };
    
    // 运行数据分析
    const runAnalysisNow = async () => {
      if (analysisLoading.value) return;
      
      try {
        analysisLoading.value = true;
        
        const params = {
          city: selectedCity.value || '',
          analysis_types: []  // 空数组表示分析所有类型
        };
        
        await api.runAnalysis(params);
        ElMessage.success('数据分析任务已启动，请稍后刷新查看结果');
        
        // 3秒后自动刷新数据
        setTimeout(() => {
          refreshData();
        }, 3000);
      } catch (error) {
        console.error('启动数据分析任务失败:', error);
        ElMessage.error('启动数据分析任务失败');
      } finally {
        analysisLoading.value = false;
      }
    };
    
    // 针对特定任务运行数据分析
    const runTaskAnalysis = async (taskId, city) => {
      if (analysisLoading.value) return;
      
      try {
        analysisLoading.value = true;
        
        const params = {
          city: city || '',
          task_id: taskId,
          analysis_types: []  // 空数组表示分析所有类型
        };
        
        await api.runAnalysis(params);
        ElMessage.success(`任务 ${taskId} 的数据分析已启动，请稍后刷新查看结果`);
        
        // 3秒后自动刷新数据
        setTimeout(() => {
          refreshData();
        }, 3000);
      } catch (error) {
        console.error('启动特定任务数据分析失败:', error);
        ElMessage.error('启动数据分析任务失败');
      } finally {
        analysisLoading.value = false;
      }
    };
    
    // 监听路由参数变化
    watch(() => route.query, (query) => {
      if (query.city) {
        selectedCity.value = query.city;
      }
      
      // 检查是否有任务ID，以及是否需要立即分析
      if (query.taskId && query.immediate === 'true') {
        // 立即运行该任务的分析
        runTaskAnalysis(query.taskId, query.city);
      } else {
        // 常规加载分析数据
        fetchData();
      }
    }, { immediate: true });
    
    // 组件挂载时初始化
    onMounted(() => {
      // 添加ECharts全局错误处理
      window.addEventListener('error', function(e) {
        if (e && e.message && typeof e.message === 'string' && e.message.indexOf('echarts') !== -1) {
          console.error('ECharts错误被全局捕获:', e.message);
          e.preventDefault(); // 阻止错误冒泡
          return true;
        }
      }, true);

      getCities();
      
      // 如果URL中包含城市参数，则使用该城市
      if (route.query.city) {
        selectedCity.value = route.query.city;
      }
      
      fetchData().then(() => {
        // 给DOM足够的时间更新并确保所有数据都加载完成
        setTimeout(() => {
          console.log('开始渲染所有图表，当前标签页:', activeTab.value);
          // 先渲染当前标签页
          renderCharts();
          
          // 再延迟渲染其他标签页数据
          setTimeout(() => {
            // 保存当前标签页
            const currentTab = activeTab.value;
            
            // 依次渲染每个标签页
            const allTabs = [
              'district_analysis', 'room_type_analysis', 'direction_analysis',
              'floor_analysis', 'price_distribution', 'community_analysis',
              'features_analysis', 'feature_combinations', 'metro_price_impact',
              'popular_features_price'
            ];
            
            // 只渲染基本图表，复杂图表等用户点击时再渲染
            for (const tab of allTabs) {
              if (tab !== currentTab) {
                activeTab.value = tab;
                renderCharts();
              }
            }
            
            // 恢复当前标签页
            activeTab.value = currentTab;
            console.log('所有图表已逐个渲染完成');
          }, 500);
        }, 800);
      });
      
      // 监听窗口大小变化，调整图表
      window.addEventListener('resize', () => {
        Object.values(charts).forEach(chart => {
          if (chart) {
            try {
              chart.resize();
            } catch (error) {
              console.error('图表调整大小失败:', error);
            }
          }
        });
      });
    });
    
    // 组件卸载时清理
    onUnmounted(() => {
      // 清理图表实例
      Object.values(charts).forEach(chart => {
        if (chart) {
          chart.dispose();
        }
      });
      
      // 移除事件监听
      window.removeEventListener('resize', () => {});
    });
    
    // 格式化特征数组
    const formatFeatures = (featuresArray) => {
      if (!featuresArray) return [];
      
      // 如果是字符串，尝试解析JSON
      if (typeof featuresArray === 'string') {
        try {
          return JSON.parse(featuresArray);
        } catch (e) {
          return [featuresArray];
        }
      }
      
      return featuresArray;
    };
    
    // 转换热门特征数据格式，计算有无特征的价格差异
    const transformPopularFeaturesData = () => {
      if (!analysisData.popular_features_price) return [];
      
      const result = [];
      const featuresMap = new Map();
      
      // 首先按特征分组
      analysisData.popular_features_price.forEach(item => {
        if (!featuresMap.has(item.feature)) {
          featuresMap.set(item.feature, []);
        }
        featuresMap.get(item.feature).push({
          ...item,
          has_feature: !!item[`has_${item.feature}`]
        });
      });
      
      // 然后计算每个特征的有无差异
      featuresMap.forEach((items, _feature) => {
        if (items.length < 2) return;
        
        const withFeature = items.find(item => item.has_feature);
        const withoutFeature = items.find(item => !item.has_feature);
        
        if (withFeature && withoutFeature) {
          const priceDiff = withFeature.avg_price - withoutFeature.avg_price;
          
          // 更新两条记录
          withFeature.price_diff = priceDiff;
          withoutFeature.price_diff = -priceDiff;
        }
        
        items.forEach(item => result.push(item));
      });
      
      return result;
    };
    
    // 返回方法和数据
    return {
      loading,
      analysisLoading,
      cities,
      selectedCity,
      summaryData,
      analysisData,
      activeTab,
      analysisTime,
      districtChanges,
      priceChangeDetails,
      priceChangeSummary,
      handleCityChange,
      handleTabClick,
      refreshData,
      getTopDistrict,
      formatAnalysisTime,
      runAnalysisNow,
      runTaskAnalysis,
      formatFeatures,
      transformPopularFeaturesData
    };
  }
};
</script>

<style scoped>
.analysis-results {
  margin-bottom: 20px;
}

/* 页面标题样式 */
:deep(.el-main) .el-page-header__title {
  font-size: 24px;
  color: #303133;
  font-weight: 600;
  margin-bottom: 30px;
  padding-bottom: 15px;
  border-bottom: 2px solid #f0f2f5;
}

/* 卡片标题样式 */
.section-title {
  font-size: 20px;
  color: #409EFF;
  font-weight: 500;
  margin: 0;
}

/* 概览标题样式 */
.overview-title {
  font-size: 18px;
  color: #606266;
  margin: 25px 0 20px;
  padding-left: 12px;
  border-left: 4px solid #409EFF;
  position: relative;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-actions {
  display: flex;
  gap: 10px;
}

.summary-section {
  margin-bottom: 30px;
  background-color: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
}

.stat-card {
  text-align: center;
  padding: 15px;
  transition: all 0.3s;
  border-radius: 8px;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.stat-card h2 {
  font-size: 24px;
  margin: 0;
  color: #409EFF;
  font-weight: bold;
}

.stat-card p {
  margin: 5px 0 0;
  color: #606266;
  font-size: 14px;
}

.chart-container {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 20px;
  margin-top: 20px;
}

.chart {
  height: 400px;
  width: 100%;
  margin-bottom: 20px;
  background-color: #fff;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
}

.chart:hover {
  box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.1);
}

.stats-table {
  width: 100%;
  margin-bottom: 20px;
}

.stats-table h4 {
  margin-bottom: 15px;
  color: #303133;
  font-weight: 500;
}

/* 响应式布局 */
@media (min-width: 992px) {
  .chart {
    width: calc(50% - 10px);
  }
}

@media (max-width: 768px) {
  .summary-section .el-row {
    flex-direction: column;
  }
  
  .summary-section .el-col {
    width: 100%;
    margin-bottom: 10px;
  }
  
  .filter-actions {
    flex-direction: column;
    width: 100%;
  }
}

/* 自定义标签页样式 */
.analysis-tabs {
  margin-top: 20px;
  overflow: auto;
}

:deep(.el-tabs__nav-wrap) {
  padding-bottom: 15px;
  overflow-x: auto;
  white-space: nowrap;
}

:deep(.el-tabs__nav) {
  display: flex;
  flex-wrap: wrap;
  padding-bottom: 5px;
}

:deep(.el-tabs__item) {
  font-size: 15px;
  padding: 0 20px;
  margin-right: 5px;
  margin-bottom: 5px;
  flex-shrink: 0;
}

:deep(.el-tabs__item.is-active) {
  font-weight: bold;
}

:deep(.el-tabs__active-bar) {
  height: 3px;
}

:deep(.el-tabs__content) {
  padding: 20px 0;
}

/* 通用动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 当前城市指示器 */
.current-city-indicator {
  background-color: #f0f8ff;
  padding: 8px 15px;
  margin: 15px 0 -5px 0;
  border-radius: 4px;
  display: flex;
  align-items: center;
  font-size: 14px;
  color: #606266;
  border-left: 3px solid #409EFF;
}

.city-name {
  font-weight: 600;
  color: #409EFF;
  margin-left: 5px;
  font-size: 16px;
}

/* 城市选择器样式 */
.city-selector {
  display: flex;
  align-items: center;
  background-color: #f5f7fa;
  padding: 5px 12px;
  border-radius: 4px;
  margin-right: 10px;
  border: 1px solid #e4e7ed;
}

.selector-label {
  margin-right: 10px;
  font-weight: 500;
  color: #606266;
}

/* 刷新按钮样式 */
:deep(.el-button) {
  display: flex;
  align-items: center;
}

:deep(.el-button--primary) {
  font-weight: 500;
  letter-spacing: 1px;
}

:deep(.el-select) {
  min-width: 150px;
}

/* 分析时间样式 */
.analysis-time {
  margin-left: 10px;
  font-size: 14px;
  color: #909399;
}

.chart-row {
  display: flex;
  margin-bottom: 20px;
}

.chart-column {
  flex: 1;
  min-height: 300px;
}

.analysis-card {
  background: #fff;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 20px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.summary-stats {
  display: flex;
  justify-content: space-around;
  margin: 15px 0;
}

.stat-item {
  text-align: center;
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
}

.stat-label {
  font-size: 13px;
  color: #606266;
  margin-top: 5px;
}

.price-increase {
  color: #f56c6c;
}

.price-decrease {
  color: #67c23a;
}
</style> 