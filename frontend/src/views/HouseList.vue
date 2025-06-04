<template>
  <div class="house-list-view">
    <el-row :gutter="20">
      <el-col :span="24">
        <HouseList />
      </el-col>
    </el-row>
  </div>
</template>

<script>
import HouseList from '../components/HouseList.vue';

export default {
  name: 'HouseListView',
  
  components: {
    HouseList
  }
};
</script>

<style scoped>
.house-list-view {
  padding: 0 20px;
}

.page-title {
  font-size: 1.8rem;
  margin: 20px 0;
  color: #303133;
}
</style> 