import { createI18n } from 'vue-i18n';
import zhCN from './locales/zh-CN';
import enUS from './locales/en-US';
import zhTW from './locales/zh-TW';

// 动态更新Element Plus的语言
let elementPlusLocale = null;

// 设置Element Plus语言的回调函数
export const setElementPlusLocaleCallback = (callback) => {
  elementPlusLocale = callback;
};

// 更新Element Plus的语言
const updateElementLanguage = (locale) => {
  if (typeof elementPlusLocale === 'function') {
    if (locale.startsWith('zh-CN')) {
      import('element-plus/es/locale/lang/zh-cn').then(module => {
        elementPlusLocale(module.default);
      });
    } else if (locale.startsWith('en')) {
      import('element-plus/es/locale/lang/en').then(module => {
        elementPlusLocale(module.default);
      });
    } else if (locale.startsWith('zh-TW')) {
      import('element-plus/es/locale/lang/zh-tw').then(module => {
        elementPlusLocale(module.default);
      });
    }
  }
};

// 获取浏览器的语言首选项
const getBrowserLanguage = () => {
  const navigatorLang = navigator.language || navigator.userLanguage;
  const lang = navigatorLang.toLowerCase();
  
  if (lang.includes('zh')) {
    if (lang.includes('tw') || lang.includes('hk')) {
      return 'zh-TW';
    }
    return 'zh-CN';
  }
  
  return 'en-US';
};

// 尝试从localStorage获取用户之前选择的语言
const getSavedLanguage = () => {
  return localStorage.getItem('language') || getBrowserLanguage();
};

// 可用的语言选项
export const availableLocales = [
  { code: 'zh-CN', name: '简体中文' },
  { code: 'en-US', name: 'English' },
  { code: 'zh-TW', name: '繁體中文' }
];

// 创建 i18n 实例
const i18n = createI18n({
  legacy: false, // 使用组合式API
  locale: getSavedLanguage(),
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
    'zh-TW': zhTW
  },
  globalInjection: true // 添加全局注入
});

// 语言切换函数
export const setLocale = (locale) => {
  i18n.global.locale.value = locale;
  localStorage.setItem('language', locale);
  document.querySelector('html').setAttribute('lang', locale);
  
  // 更新Element Plus的语言
  updateElementLanguage(locale);
};

export default i18n; 