import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import i18n, { setElementPlusLocaleCallback } from './i18n'

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 设置Element Plus的初始语言
let currentElementLocale = zhCn;
const savedLang = localStorage.getItem('language') || 'zh-CN';
if (savedLang.startsWith('en')) {
  import('element-plus/es/locale/lang/en').then(module => {
    currentElementLocale = module.default;
    updateElementUI();
  });
} else if (savedLang.startsWith('zh-TW')) {
  import('element-plus/es/locale/lang/zh-tw').then(module => {
    currentElementLocale = module.default;
    updateElementUI();
  });
}

// 注册Element Plus语言变更回调
setElementPlusLocaleCallback((locale) => {
  currentElementLocale = locale;
  updateElementUI();
});

function updateElementUI() {
  app.use(ElementPlus, {
    locale: currentElementLocale
  });
}

app.use(router)
app.use(i18n)
app.use(ElementPlus, {
  locale: currentElementLocale,
})

app.mount('#app') 