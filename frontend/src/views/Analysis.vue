<template>
  <div class="analysis-view">
    <el-row :gutter="20">
      <el-col :span="24">
        <h1 class="page-title">租房市场数据分析</h1>
        <p class="page-desc">分析租房市场数据，包括区域、户型、朝向、楼层、价格分布、小区分析以及房源特征对价格的影响</p>
        <AnalysisResults />
      </el-col>
    </el-row>
  </div>
</template>

<script>
import AnalysisResults from '../components/AnalysisResults.vue';

export default {
  name: 'AnalysisView',
  
  components: {
    AnalysisResults
  }
};
</script>

<style scoped>
.analysis-view {
  padding: 0 20px;
}

.page-title {
  font-size: 1.8rem;
  margin: 20px 0 10px;
  color: #303133;
}

.page-desc {
  color: #606266;
  margin-bottom: 20px;
  font-size: 14px;
}
</style>