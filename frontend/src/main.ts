import { createApp } from 'vue'
import { VueQueryPlugin } from '@tanstack/vue-query'

import App from './App.vue'
import router from './router'
import './styles.css'
import { pinia } from '@/core/stores/pinia'

const app = createApp(App)

app.use(VueQueryPlugin)
app.use(pinia)
app.use(router)

app.mount('#app')
