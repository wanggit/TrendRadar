<template>
  <footer class="app-footer">
    <div class="footer-content">
      <div class="footer-links">
        <router-link to="/privacy-policy">隐私政策</router-link>
        <span class="separator">|</span>
        <router-link to="/terms-of-service">服务条款</router-link>
        <span class="separator">|</span>
        <router-link to="/pricing">定价</router-link>
      </div>
      <div class="footer-copyright">
        &copy; {{ currentYear }} TrendRadar. All rights reserved.
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue'

const currentYear = computed(() => new Date().getFullYear())
</script>

<style scoped>
.app-footer {
  background: #304156;
  color: #bfcbd9;
  padding: 20px;
  text-align: center;
  font-size: 13px;
}

.footer-links {
  margin-bottom: 8px;
}

.footer-links a {
  color: #bfcbd9;
  text-decoration: none;
  margin: 0 8px;
}

.footer-links a:hover {
  color: #409eff;
}

.separator {
  color: #5a6a7e;
}

.footer-copyright {
  color: #5a6a7e;
}
</style>
