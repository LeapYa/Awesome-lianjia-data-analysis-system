<template>
  <div class="task-list-view">
    <el-row :gutter="20">
      <el-col :span="24">
        <TaskList />
      </el-col>
    </el-row>
  </div>
</template>

<script>
import TaskList from '../components/TaskList.vue';

export default {
  name: 'TaskListView',
  
  components: {
    TaskList
  }
};
</script>

<style scoped>
.task-list-view {
  padding: 0 20px;
}

.page-title {
  font-size: 1.8rem;
  margin: 20px 0;
  color: #303133;
}
</style> 