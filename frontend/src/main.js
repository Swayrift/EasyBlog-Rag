import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { reveal } from './directives/reveal'

// 自托管字体（@fontsource），避免运行期依赖 Google Fonts CDN
import '@fontsource/noto-serif-sc/600.css'
import '@fontsource/noto-serif-sc/900.css'
import '@fontsource/noto-sans-sc/400.css'
import '@fontsource/noto-sans-sc/500.css'
import '@fontsource/noto-sans-sc/700.css'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/600.css'
import '@fontsource/jetbrains-mono/400-italic.css'

import './assets/main.css'

const app = createApp(App)
const pinia = createPinia()

app.directive('reveal', reveal)
app.use(pinia)
app.use(router)

app.mount('#app')
