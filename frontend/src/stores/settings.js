import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useSettingsStore = defineStore('settings', () => {
  const language = ref(localStorage.getItem('language') || 'zh')
  const theme = ref(localStorage.getItem('theme') || 'light')
  const soundEnabled = ref(localStorage.getItem('soundEnabled') !== 'false')
  
  const languages = [
    { code: 'zh', name: '中文', nativeName: '中文' },
    { code: 'en', name: 'English', nativeName: 'English' },
    { code: 'ja', name: 'Japanese', nativeName: '日本語' },
    { code: 'ko', name: 'Korean', nativeName: '한국어' },
    { code: 'fr', name: 'French', nativeName: 'Français' },
    { code: 'de', name: 'German', nativeName: 'Deutsch' },
    { code: 'es', name: 'Spanish', nativeName: 'Español' },
    { code: 'pt', name: 'Portuguese', nativeName: 'Português' },
    { code: 'ar', name: 'Arabic', nativeName: 'العربية' },
    { code: 'ru', name: 'Russian', nativeName: 'Русский' }
  ]
  
  const setLanguage = (lang) => {
    language.value = lang
    localStorage.setItem('language', lang)
  }
  
  const setTheme = (newTheme) => {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)
    document.documentElement.setAttribute('data-theme', newTheme)
  }
  
  const toggleSound = () => {
    soundEnabled.value = !soundEnabled.value
    localStorage.setItem('soundEnabled', soundEnabled.value)
  }
  
  const getLanguageName = (code) => {
    const lang = languages.find(l => l.code === code)
    return lang ? lang.nativeName : code
  }
  
  return {
    language,
    theme,
    soundEnabled,
    languages,
    setLanguage,
    setTheme,
    toggleSound,
    getLanguageName
  }
})
