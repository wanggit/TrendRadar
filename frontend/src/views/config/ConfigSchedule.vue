<template>
  <div>
    <div class="module-header">
      <h3>调度设置</h3>
    </div>

    <el-alert
      title="调度设置控制采集、分析、推送的执行时间和频率"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <el-form :model="form" label-width="120px" style="max-width: 600px">
      <el-form-item label="启用调度">
        <el-switch v-model="form.enabled" />
      </el-form-item>

      <el-form-item label="预设模板">
        <el-select v-model="form.preset" style="width: 250px">
          <el-option label="早晚汇总 (推荐)" value="morning_evening">
            <div>
              <div>早晚汇总</div>
              <div style="color: #909399; font-size: 12px">早 8 点 + 晚 8 点推送</div>
            </div>
          </el-option>
          <el-option label="全天候" value="always_on">
            <div>
              <div>全天候</div>
              <div style="color: #909399; font-size: 12px">每小时采集推送</div>
            </div>
          </el-option>
          <el-option label="办公时间" value="office_hours">
            <div>
              <div>办公时间</div>
              <div style="color: #909399; font-size: 12px">工作日 9:00-18:00</div>
            </div>
          </el-option>
          <el-option label="夜猫子" value="night_owl">
            <div>
              <div>夜猫子</div>
              <div style="color: #909399; font-size: 12px">晚间 20:00 - 凌晨 1:00</div>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <el-divider content-position="left">调度说明</el-divider>

      <div class="schedule-info">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="当前预设">{{ form.preset }}</el-descriptions-item>
          <el-descriptions-item label="调度状态">
            <el-tag :type="form.enabled ? 'success' : 'info'">
              {{ form.enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <el-form-item style="margin-top: 20px">
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { configApi } from '@/api/config'
import { ElMessage } from 'element-plus'

const saving = ref(false)

const form = reactive({
  enabled: true,
  preset: 'morning_evening',
})

let originalConfig = null

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  const config = await configApi.getSchedule()
  Object.assign(form, {
    enabled: config.enabled ?? true,
    preset: config.preset || 'morning_evening',
  })
  originalConfig = { ...form }
}

async function save() {
  saving.value = true
  try {
    await configApi.updateSchedule({ ...form })
    ElMessage.success('调度配置已保存')
    originalConfig = { ...form }
  } finally {
    saving.value = false
  }
}

function reset() {
  Object.assign(form, originalConfig)
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

.schedule-info {
  max-width: 400px;
}
</style>
