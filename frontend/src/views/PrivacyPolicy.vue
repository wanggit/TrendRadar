<template>
  <div class="policy-page">
    <el-card class="policy-card">
      <template #header>
        <h1>隐私政策</h1>
      </template>

      <div class="policy-content">
        <p class="last-updated">最后更新日期：2025年1月1日</p>

        <h2>1. 信息收集</h2>
        <p>TrendRadar 收集以下类型的信息：</p>
        <ul>
          <li><strong>账户信息</strong>：注册时提供的邮箱地址和昵称</li>
          <li><strong>使用数据</strong>：平台配置、关键词设置、推送渠道配置</li>
          <li><strong>日志数据</strong>：IP地址、浏览器类型、访问时间</li>
        </ul>

        <h2>2. 信息使用</h2>
        <p>我们收集的信息用于：</p>
        <ul>
          <li>提供和改进 TrendRadar 服务</li>
          <li>处理支付和订阅管理</li>
          <li>发送服务通知和试用提醒</li>
          <li>保障账户安全</li>
        </ul>

        <h2>3. 信息存储</h2>
        <p>您的数据存储在安全的服务器上。Free 用户数据保留 7 天，Pro 用户数据保留 30 天。我们采取合理的安全措施保护您的数据。</p>

        <h2>4. 信息共享</h2>
        <p>我们不会将您的个人信息出售或分享给第三方，除非：</p>
        <ul>
          <li>获得您的明确同意</li>
          <li>法律法规要求</li>
          <li>为保护 TrendRadar 的权利或安全</li>
        </ul>

        <h2>5. 支付信息</h2>
        <p>支付通过 Z-Pay 统一支付网关处理。我们不存储您的支付卡信息或支付账户凭据。</p>

        <h2>6. 您的权利</h2>
        <p>您有权：</p>
        <ul>
          <li>访问和导出您的个人数据</li>
          <li>更正不准确的个人信息</li>
          <li>删除您的账户和相关数据</li>
          <li>撤回同意（不影响撤回前的处理合法性）</li>
        </ul>

        <h2>7. 联系我们</h2>
        <p>如有任何隐私相关问题，请通过 support@trendradar.com 联系我们。</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
</script>

<style scoped>
.policy-page {
  min-height: 100vh;
  background: #f0f2f5;
  padding: 40px 20px;
}

.policy-card {
  max-width: 800px;
  margin: 0 auto;
}

.policy-card h1 {
  margin: 0;
  font-size: 28px;
}

.policy-content {
  line-height: 1.8;
  color: #303133;
}

.policy-content h2 {
  font-size: 20px;
  margin-top: 24px;
  margin-bottom: 12px;
  color: #303133;
}

.policy-content p {
  margin-bottom: 12px;
}

.policy-content ul {
  margin-bottom: 12px;
  padding-left: 24px;
}

.policy-content li {
  margin-bottom: 6px;
}

.last-updated {
  color: #909399;
  font-size: 14px;
}
</style>
