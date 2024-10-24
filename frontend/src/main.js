import { createApp } from 'vue';
import App from './App.vue';
import router from './router'; 
import './assets/output.css'; 
import store from './store';  // Import the store
import axios from 'axios';

axios.defaults.withCredentials = true;
axios.defaults.headers.common['Content-Type'] = 'application/json';

const app = createApp(App);

// Check authentication status before mounting the app
store.dispatch('checkAuth').then(() => {
  app.use(store).use(router).mount('#app')
});