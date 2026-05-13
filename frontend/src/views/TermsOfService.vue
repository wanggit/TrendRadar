<template>
  <div class="terms-page">
    <el-card class="terms-card">
      <template #header>
        <h1>服务条款</h1>
      </template>

      <div class="terms-content">
        <p class="last-updated">最后更新日期：2025年1月1日</p>

        <h2>1. 服务说明</h2>
        <p>TrendRadar 是一个热榜资讯聚合与分析平台，提供多平台热榜抓取、AI 深度分析、智能推送等功能。</p>

        <h2>2. 账户注册</h2>
        <ul>
          <li>您需要提供真实有效的邮箱地址进行注册</li>
          <li>每个邮箱地址只能注册一个账户</li>
          <li>您有责任保护账户凭据的安全</li>
        </ul>

        <h2>3. 免费试用</h2>
        <ul>
          <li>新用户注册后自动获得 7 天专业版免费试用</li>
          <li>每个用户仅限一次试用机会</li>
          <li>试用到期后自动降级为免费版</li>
          <li>试用期间享受专业版全部功能</li>
        </ul>

        <h2>4. 付费方案</h2>
        <ul>
          <li>专业版：¥49/月、¥129/季、¥399/年</li>
          <li>支付完成后即时生效</li>
          <li>到期后未续费将自动降级为免费版</li>
          <li>已支付费用不予退款</li>
        </ul>

        <h2>5. 使用限制</h2>
        <p>免费版用户受以下限制：</p>
        <ul>
          <li>最多 3 个热榜平台</li>
          <li>最多 5 个关键词组</li>
          <li>每日最多 4 次推送</li>
          <li>最多 1 个推送渠道</li>
          <li>不可使用 AI 功能</li>
          <li>数据保留 7 天</li>
        </ul>

        <h2>6. 免责声明</h2>
        <p>TrendRadar 不对以下情况负责：</p>
        <ul>
          <li>因网络故障导致的数据延迟或丢失</li>
          <li>第三方平台内容变更导致的信息不准确</li>
          <li>AI 分析结果的主观性和局限性</li>
          <li>用户不当使用服务导致的后果</li>
        </ul>

        <h2>7. 服务变更与终止</h2>
        <p>我们保留随时修改服务条款的权利。重大变更将通过邮件或站内通知告知用户。继续使用服务即视为接受新条款。</p>

        <h2>8. 联系我们</h2>
        <p>如有任何问题，请通过 support@trendradar.com 联系我们。</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
</script>

<style scoped>
.terms-page {
  min-height: 100vh;
  background: #f0f2f5;
  padding: 40px 20px;
}

.terms-card {
  max-width: 800px;
  margin: 0 auto;
}

.terms-card h1 {
  margin: 0;
  font-size: 28px;
}

.terms-content {
  line-height: 1.8;
  color: #303133;
}

.terms-content h2 {
  font-size: 20px;
  margin-top: 24px;
  margin-bottom: 12px;
  color: #303133;
}

.terms-content p {
  margin-bottom: 12px;
}

.terms-content ul {
  margin-bottom: 12px;
  padding-left: 24px;
}

.terms-content li {
  margin-bottom: 6px;
}

.last-updated {
  color: #909399;
  font-size: 14px;
}
</style>
