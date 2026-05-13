<template>
  <div>
    <div class="module-header">
      <h3>推送通知</h3>
    </div>

    <el-alert
      v-if="atLimit"
      :title="`免费版最多 ${maxChannels} 个推送渠道，请升级到专业版解锁更多`"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    >
      <template #default>
        <el-button size="small" type="primary" @click="$router.push('/purchase')">升级专业版</el-button>
      </template>
    </el-alert>

    <el-alert
      v-else
      title="推送时间由调度设置控制，此处仅配置通知渠道。可同时启用多个渠道。"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <el-form :model="form" label-width="140px" style="max-width: 700px">
      <el-form-item label="启用推送">
        <el-switch v-model="form.enabled" />
      </el-form-item>

      <el-divider content-position="left">通知渠道</el-divider>

      <div v-for="channel in channels" :key="channel.key" class="channel-card">
        <div class="channel-header">
          <el-checkbox v-model="form.channels[channel.key].enabled" :disabled="isChannelDisabled(channel.key)">
            <span class="channel-name">{{ channel.icon }} {{ channel.label }}</span>
          </el-checkbox>
        </div>
        <div v-if="form.channels[channel.key].enabled" class="channel-fields">
          <div v-for="field in channel.fields" :key="field.key" class="field-row">
            <label>{{ field.label }}</label>
            <el-input
              v-model="form.channels[channel.key][field.key]"
              :placeholder="field.placeholder"
              :type="field.type || 'text'"
              style="width: 300px"
            />
          </div>
        </div>
      </div>

      <el-form-item style="margin-top: 20px">
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { configApi } from '@/api/config'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const saving = ref(false)

const maxChannels = computed(() => {
  const tier = authStore.user?.tier
  if (tier === 'pro' || tier === 'enterprise') return 999
  return 1
})

const atLimit = computed(() => {
  const enabled = Object.values(form.channels).filter(ch => ch.enabled).length
  return enabled >= maxChannels.value
})

function isChannelDisabled(channelKey) {
  if (form.channels[channelKey].enabled) return false
  const enabledCount = Object.values(form.channels).filter(ch => ch.enabled).length
  return enabledCount >= maxChannels.value
}

const channels = [
  {
    key: 'telegram',
    icon: '📱',
    label: 'Telegram',
    fields: [
      { key: 'bot_token', label: 'Bot Token', placeholder: '123456:ABC-DEF...' },
      { key: 'chat_id', label: 'Chat ID', placeholder: '-1001234567890' },
    ],
  },
  {
    key: 'wework',
    icon: '💼',
    label: '企业微信',
    fields: [
      { key: 'webhook_url', label: 'Webhook URL', placeholder: 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...' },
      { key: 'msg_type', label: '消息类型', placeholder: 'markdown' },
    ],
  },
  {
    key: 'feishu',
    icon: '🚀',
    label: '飞书',
    fields: [
      { key: 'webhook_url', label: 'Webhook URL', placeholder: 'https://open.feishu.cn/open-apis/bot/v2/hook/...' },
    ],
  },
  {
    key: 'dingtalk',
    icon: '🔔',
    label: '钉钉',
    fields: [
      { key: 'webhook_url', label: 'Webhook URL', placeholder: 'https://oapi.dingtalk.com/robot/send?access_token=...' },
    ],
  },
  {
    key: 'bark',
    icon: '🐕',
    label: 'Bark',
    fields: [
      { key: 'url', label: 'URL', placeholder: 'https://api.day.app/your_key/...' },
    ],
  },
  {
    key: 'ntfy',
    icon: '📡',
    label: 'ntfy',
    fields: [
      { key: 'server_url', label: 'Server URL', placeholder: 'https://ntfy.sh' },
      { key: 'topic', label: 'Topic', placeholder: 'trendradar' },
      { key: 'token', label: 'Token (可选)', placeholder: 'tk_...' },
    ],
  },
  {
    key: 'slack',
    icon: '💬',
    label: 'Slack',
    fields: [
      { key: 'webhook_url', label: 'Webhook URL', placeholder: 'https://hooks.slack.com/services/T00/B00/XXX' },
    ],
  },
  {
    key: 'email',
    icon: '📧',
    label: '邮件',
    fields: [
      { key: 'smtp_server', label: 'SMTP 服务器', placeholder: 'smtp.gmail.com' },
      { key: 'smtp_port', label: 'SMTP 端口', placeholder: '587' },
      { key: 'from', label: '发件人', placeholder: 'your@email.com' },
      { key: 'password', label: '密码', type: 'password', placeholder: '应用专用密码' },
      { key: 'to', label: '收件人', placeholder: 'recipient@email.com' },
    ],
  },
  {
    key: 'generic_webhook',
    icon: '🔗',
    label: '通用 Webhook',
    fields: [
      { key: 'webhook_url', label: 'URL', placeholder: 'https://your-webhook.com/endpoint' },
      { key: 'payload_template', label: 'Payload 模板 (JSON)', placeholder: '{"text": "{{message}}"}' },
    ],
  },
]

const defaultChannels = {}
for (const ch of channels) {
  defaultChannels[ch.key] = { enabled: false }
  for (const field of ch.fields) {
    defaultChannels[ch.key][field.key] = ''
  }
}

const form = reactive({
  enabled: true,
  channels: JSON.parse(JSON.stringify(defaultChannels)),
})

let originalConfig = null

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  const config = await configApi.getNotification()
  form.enabled = config.enabled ?? true
  for (const ch of channels) {
    const saved = config.channels?.[ch.key] || {}
    form.channels[ch.key] = { ...defaultChannels[ch.key], ...saved }
  }
  originalConfig = JSON.parse(JSON.stringify(form))
}

async function save() {
  saving.value = true
  try {
    for (const ch of channels) {
      const channelData = form.channels[ch.key]
      if (!channelData.enabled) continue

      for (const field of ch.fields) {
        const value = channelData[field.key]
        if (!value) continue

        if (field.key.includes('url') || field.key.includes('webhook') || field.key === 'server_url') {
          if (!/^https?:\/\/.+/.test(value)) {
            ElMessage.warning(`${ch.label} 的 ${field.label} 格式不正确`)
            return
          }
        }
      }
    }

    await configApi.updateNotification({
      enabled: form.enabled,
      channels: form.channels,
    })
    ElMessage.success('通知配置已保存')
    originalConfig = JSON.parse(JSON.stringify(form))
  } finally {
    saving.value = false
  }
}

function reset() {
  Object.assign(form, JSON.parse(JSON.stringify(originalConfig)))
  ElMessage.info('已重置为上次保存的配置')
}
</script>

<style scoped>
.module-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.module-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.channel-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}

.channel-header {
  padding: 12px 16px;
  background: #fafbfc;
}

.channel-name {
  font-weight: 500;
}

.channel-fields {
  padding: 12px 16px 16px 40px;
  border-top: 1px solid #f0f0f0;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.field-row label {
  width: 100px;
  font-size: 13px;
  color: #606266;
  flex-shrink: 0;
}
</style>
