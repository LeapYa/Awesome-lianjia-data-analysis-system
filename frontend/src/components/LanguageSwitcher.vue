<template>
  <div class="lang-switcher">
    <el-dropdown @command="handleLanguageChange" trigger="click">
      <span class="lang-dropdown-link">
        {{ currentLanguageName }}
        <el-icon class="el-icon--right">
          <arrow-down />
        </el-icon>
      </span>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item 
            v-for="locale in availableLocales" 
            :key="locale.code"
            :command="locale.code"
            :class="{ 'is-active': currentLocale === locale.code }"
          >
            {{ locale.name }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ArrowDown } from '@element-plus/icons-vue';
import { availableLocales, setLocale } from '../i18n';

const { locale } = useI18n({ useScope: 'global' });

// 当前语言代码
const currentLocale = computed(() => locale.value);

// 本地存储当前选择的语言名称
const localeLabelRef = ref('');

// 当前语言名称
const currentLanguageName = computed(() => {
  if (localeLabelRef.value) return localeLabelRef.value;
  const current = availableLocales.find(l => l.code === currentLocale.value);
  return current ? current.name : '简体中文';
});

// 监听语言变化并更新显示名称
watch(currentLocale, (newLocale) => {
  const current = availableLocales.find(l => l.code === newLocale);
  if (current) {
    localeLabelRef.value = current.name;
  }
}, { immediate: true });

// 处理语言切换
const handleLanguageChange = (lang) => {
  setLocale(lang);
  const selected = availableLocales.find(l => l.code === lang);
  if (selected) {
    localeLabelRef.value = selected.name;
  }
};
</script>

<style scoped>
.lang-switcher {
  display: flex;
  align-items: center;
}

.lang-dropdown-link {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #666;
  padding: 0 12px;
  font-size: 14px;
  height: 32px;
  border-radius: 4px;
  transition: all 0.3s;
}

.lang-dropdown-link:hover {
  background-color: #f0f7ff;
  color: #0051c3;
}

:deep(.el-dropdown-menu__item.is-active) {
  color: #0051c3;
  background-color: #f0f7ff;
}
</style> 