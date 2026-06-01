import Vue from 'vue'
import { ColorPicker, Option, Select } from 'element-ui'
import 'element-ui/lib/theme-chalk/index.css'
import App from './App.vue'
import router from './router'
import './styles.css'

Vue.config.productionTip = false
Vue.use(ColorPicker)
Vue.use(Select)
Vue.use(Option)

new Vue({
  router,
  render: h => h(App),
}).$mount('#app')
