<template>
  <div>
    <div class="module-header">
      <h3>调度时间线</h3>
      <div class="header-actions">
        <el-button @click="loadPresets" :loading="loadingPresets">
          <el-icon><Refresh /></el-icon> 加载预设
        </el-button>
        <el-button type="primary" @click="showNewPresetDialog = true">
          <el-icon><Plus /></el-icon> 新建调度模式
        </el-button>
      </div>
    </div>

    <el-alert
      title="调度时间线控制采集、分析、推送的执行时间。选择预设模板或自定义调度规则。"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <!-- 当前激活的预设 -->
    <el-card class="active-preset-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>当前调度模式</span>
          <el-select v-model="activePresetKey" @change="saveActivePreset" style="width: 200px">
            <el-option
              v-for="p in availablePresets"
              :key="p.key"
              :label="p.name"
              :value="p.key"
            >
              <span>{{ p.icon }} {{ p.name }}</span>
            </el-option>
          </el-select>
        </div>
      </template>
      <div class="preset-summary">
        <div v-if="activePreset" class="preset-info">
          <div class="preset-name">{{ activePreset.icon }} {{ activePreset.name }}</div>
          <div class="preset-desc">{{ activePreset.description }}</div>
        </div>
        <div v-if="activePreset" class="period-timeline">
          <div
            v-for="period in activePresetPeriods"
            :key="period.key"
            class="period-block"
            :class="periodColorClass(period)"
            :title="periodLabel(period)"
          >
            <div class="period-time">{{ period.start }}</div>
            <div class="period-label">{{ period.name }}</div>
            <div class="period-icons">
              <span v-if="period.collect" title="采集">📥</span>
              <span v-if="period.analyze" title="分析">🧠</span>
              <span v-if="period.push" title="推送">📤</span>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 预设模板列表 -->
    <div class="section-title">预设模板</div>
    <div class="preset-grid">
      <div
        v-for="preset in availablePresets"
        :key="preset.key"
        class="preset-card"
        :class="{ active: preset.key === activePresetKey }"
        @click="selectPreset(preset.key)"
      >
        <div class="preset-card-header">
          <span class="preset-icon">{{ preset.icon }}</span>
          <div class="preset-card-info">
            <div class="preset-card-name">{{ preset.name }}</div>
            <div class="preset-card-desc">{{ preset.description }}</div>
          </div>
          <el-tag v-if="preset.key === activePresetKey" size="small" type="success">当前</el-tag>
        </div>
        <div class="preset-card-periods">
          <div v-for="period in getPresetPeriods(preset)" :key="period.key" class="mini-period">
            <span class="mini-time">{{ period.start }}-{{ period.end }}</span>
            <span class="mini-actions">
              <span v-if="period.collect" class="mini-collect">采集</span>
              <span v-if="period.analyze" class="mini-analyze">分析</span>
              <span v-if="period.push" class="mini-push">推送</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 当前预设的详细编辑 -->
    <div v-if="editingPreset" class="section-title">
      编辑预设: {{ editingPreset.name }}
      <el-button size="small" type="primary" @click="showAddPeriodDialog = true">
        <el-icon><Plus /></el-icon> 添加时间段
      </el-button>
    </div>

    <div v-if="editingPreset" class="period-editor">
      <div
        v-for="(period, idx) in editingPresetPeriods"
        :key="idx"
        class="period-edit-card"
      >
        <div class="period-edit-header">
          <span class="period-edit-name">{{ period.name }}</span>
          <div class="period-edit-actions">
            <el-button size="small" @click="editPeriod(idx)">编辑</el-button>
            <el-button size="small" type="danger" @click="deletePeriod(idx)">删除</el-button>
          </div>
        </div>
        <div class="period-edit-body">
          <div class="period-time-range">{{ period.start }} ~ {{ period.end }}</div>
          <div class="period-toggles">
            <el-tag size="small" :type="period.collect ? 'success' : 'info'">
              {{ period.collect ? '📥 采集' : '采集关闭' }}
            </el-tag>
            <el-tag size="small" :type="period.analyze ? 'warning' : 'info'">
              {{ period.analyze ? '🧠 分析' : '分析关闭' }}
            </el-tag>
            <el-tag size="small" :type="period.push ? 'primary' : 'info'">
              {{ period.push ? '📤 推送' : '推送关闭' }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建预设弹窗 -->
    <el-dialog v-model="showNewPresetDialog" title="新建调度模式" width="500px">
      <el-form :model="newPresetForm" label-width="100px">
        <el-form-item label="模式标识">
          <el-input v-model="newPresetForm.key" placeholder="例如: my_schedule" />
          <div style="color: #909399; font-size: 12px; margin-top: 4px">仅支持英文、数字和下划线</div>
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="newPresetForm.name" placeholder="例如: 我的调度" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newPresetForm.description" type="textarea" :rows="2" placeholder="简短描述" />
        </el-form-item>
        <el-form-item label="基于模板">
          <el-select v-model="newPresetForm.template" style="width: 100%">
            <el-option label="空白模板" value="" />
            <el-option
              v-for="p in availablePresets"
              :key="p.key"
              :label="p.name"
              :value="p.key"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNewPresetDialog = false">取消</el-button>
        <el-button type="primary" @click="createPreset">创建</el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑时间段弹窗 -->
    <el-dialog
      v-model="showAddPeriodDialog"
      :title="editingPeriodIdx >= 0 ? '编辑时间段' : '新增时间段'"
      width="500px"
    >
      <el-form :model="periodForm" label-width="100px">
        <el-form-item label="时间段标识">
          <el-input v-model="periodForm.key" placeholder="例如: morning_push" :disabled="editingPeriodIdx >= 0" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="periodForm.name" placeholder="例如: 晨间推送" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-time-picker v-model="periodForm.start" format="HH:mm" value-format="HH:mm" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker v-model="periodForm.end" format="HH:mm" value-format="HH:mm" style="width: 100%" />
        </el-form-item>
        <el-divider content-position="left">操作</el-divider>
        <el-form-item label="采集">
          <el-switch v-model="periodForm.collect" />
        </el-form-item>
        <el-form-item label="分析">
          <el-switch v-model="periodForm.analyze" />
        </el-form-item>
        <el-form-item label="推送">
          <el-switch v-model="periodForm.push" />
        </el-form-item>
        <el-form-item label="报告模式" v-if="periodForm.push">
          <el-select v-model="periodForm.report_mode" style="width: 100%">
            <el-option label="current - 当前快照" value="current" />
            <el-option label="daily - 每日汇总" value="daily" />
            <el-option label="incremental - 增量推送" value="incremental" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddPeriodDialog = false">取消</el-button>
        <el-button type="primary" @click="savePeriod">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { Refresh, Plus } from '@element-plus/icons-vue'
import { configApi } from '@/api/config'
import { ElMessage, ElMessageBox } from 'element-plus'

const loadingPresets = ref(false)
const showNewPresetDialog = ref(false)
const showAddPeriodDialog = ref(false)
const editingPeriodIdx = ref(-1)

const activePresetKey = ref('morning_evening')
const timelineConfig = ref({ presets: {}, custom: {} })

const newPresetForm = reactive({
  key: '',
  name: '',
  description: '',
  template: '',
})

const periodForm = reactive({
  key: '',
  name: '',
  start: '09:00',
  end: '11:00',
  collect: true,
  analyze: false,
  push: false,
  report_mode: 'current',
})

const BUILTIN_PRESETS = {
  morning_evening: {
    name: '早晚汇总',
    description: '早 8 点 + 晚 8 点推送，适合日常资讯',
    icon: '☀️',
    default: { collect: true, analyze: true, push: false, report_mode: 'current' },
    periods: {
      morning: { name: '晨间采集', start: '08:00', end: '08:30', collect: true, analyze: true, push: true, report_mode: 'current' },
      evening: { name: '晚间汇总', start: '20:00', end: '20:30', collect: true, analyze: true, push: true, report_mode: 'daily' },
    },
  },
  always_on: {
    name: '全天候',
    description: '每小时采集推送，不错过任何热点',
    icon: '⚡',
    default: { collect: true, analyze: false, push: true, report_mode: 'current' },
    periods: {
      h00: { name: '00:00', start: '00:00', end: '01:00', collect: true, analyze: false, push: true },
      h02: { name: '02:00', start: '02:00', end: '03:00', collect: true, analyze: false, push: true },
      h04: { name: '04:00', start: '04:00', end: '05:00', collect: true, analyze: false, push: true },
      h06: { name: '06:00', start: '06:00', end: '07:00', collect: true, analyze: false, push: true },
      h08: { name: '08:00', start: '08:00', end: '09:00', collect: true, analyze: true, push: true },
      h10: { name: '10:00', start: '10:00', end: '11:00', collect: true, analyze: false, push: true },
      h12: { name: '12:00', start: '12:00', end: '13:00', collect: true, analyze: true, push: true },
      h14: { name: '14:00', start: '14:00', end: '15:00', collect: true, analyze: false, push: true },
      h16: { name: '16:00', start: '16:00', end: '17:00', collect: true, analyze: false, push: true },
      h18: { name: '18:00', start: '18:00', end: '19:00', collect: true, analyze: true, push: true },
      h20: { name: '20:00', start: '20:00', end: '21:00', collect: true, analyze: false, push: true },
      h22: { name: '22:00', start: '22:00', end: '23:00', collect: true, analyze: false, push: true },
    },
  },
  office_hours: {
    name: '办公时间',
    description: '工作日 9:00-18:00，每 2 小时推送',
    icon: '💼',
    default: { collect: true, analyze: false, push: true, report_mode: 'current' },
    periods: {
      morning: { name: '早间', start: '09:00', end: '09:30', collect: true, analyze: true, push: true },
      noon: { name: '午间', start: '12:00', end: '12:30', collect: true, analyze: false, push: true },
      afternoon: { name: '下午', start: '15:00', end: '15:30', collect: true, analyze: false, push: true },
      evening: { name: '下班前', start: '18:00', end: '18:30', collect: true, analyze: true, push: true, report_mode: 'daily' },
    },
  },
  night_owl: {
    name: '夜猫子',
    description: '晚间 20:00 - 凌晨 1:00，适合夜间浏览',
    icon: '🌙',
    default: { collect: true, analyze: true, push: true, report_mode: 'current' },
    periods: {
      evening: { name: '晚间', start: '20:00', end: '21:00', collect: true, analyze: true, push: true },
      night: { name: '深夜', start: '22:00', end: '23:00', collect: true, analyze: false, push: true },
      midnight: { name: '午夜', start: '00:00', end: '01:00', collect: true, analyze: true, push: true, report_mode: 'daily' },
    },
  },
}

const availablePresets = computed(() => {
  const allPresets = { ...BUILTIN_PRESETS, ...timelineConfig.value.presets, ...timelineConfig.value.custom }
  return Object.entries(allPresets).map(([key, val]) => ({
    key,
    name: val.name || key,
    description: val.description || '',
    icon: val.icon || '📋',
    ...val,
  }))
})

const activePreset = computed(() => {
  return availablePresets.value.find(p => p.key === activePresetKey.value)
})

const activePresetPeriods = computed(() => {
  if (!activePreset.value) return []
  const periods = activePreset.value.periods || {}
  return Object.entries(periods).map(([key, val]) => ({ key, ...val }))
    .sort((a, b) => a.start.localeCompare(b.start))
})

const editingPreset = computed(() => {
  const key = activePresetKey.value
  if (BUILTIN_PRESETS[key]) return null
  if (timelineConfig.value.presets[key]) return { key, ...timelineConfig.value.presets[key] }
  if (timelineConfig.value.custom[key]) return { key, ...timelineConfig.value.custom[key] }
  return null
})

const editingPresetPeriods = computed(() => {
  if (!editingPreset.value) return []
  const periods = editingPreset.value.periods || {}
  return Object.entries(periods).map(([key, val]) => ({ key, ...val }))
    .sort((a, b) => a.start.localeCompare(b.start))
})

onMounted(async () => {
  await loadTimeline()
})

async function loadTimeline() {
  const config = await configApi.getFullConfig()
  timelineConfig.value = config.timeline || { presets: {}, custom: {} }
  const schedule = await configApi.getSchedule()
  activePresetKey.value = schedule.preset || 'morning_evening'
}

async function loadPresets() {
  loadingPresets.value = true
  try {
    await loadTimeline()
    ElMessage.success('预设已刷新')
  } finally {
    loadingPresets.value = false
  }
}

function selectPreset(key) {
  activePresetKey.value = key
  saveActivePreset()
}

async function saveActivePreset() {
  const schedule = await configApi.getSchedule()
  schedule.preset = activePresetKey.value
  await configApi.updateSchedule(schedule)
  ElMessage.success('已切换调度模式')
}

function getPresetPeriods(preset) {
  const periods = preset.periods || {}
  return Object.entries(periods).map(([key, val]) => ({ key, ...val }))
    .sort((a, b) => a.start.localeCompare(b.start))
}

function periodColorClass(period) {
  if (period.push && period.analyze) return 'gradient-blue-purple'
  if (period.push) return 'bg-blue'
  if (period.analyze) return 'bg-purple'
  if (period.collect) return 'bg-gray'
  return 'bg-white'
}

function periodLabel(period) {
  const actions = []
  if (period.collect) actions.push('采集')
  if (period.analyze) actions.push('分析')
  if (period.push) actions.push('推送')
  return `${period.name} (${period.start}-${period.end}): ${actions.join(' + ')}`
}

function createPreset() {
  if (!newPresetForm.key || !newPresetForm.name) {
    ElMessage.warning('请填写模式标识和显示名称')
    return
  }

  let basePreset
  if (newPresetForm.template) {
    const allPresets = { ...BUILTIN_PRESETS, ...timelineConfig.value.presets, ...timelineConfig.value.custom }
    basePreset = JSON.parse(JSON.stringify(allPresets[newPresetForm.template] || {}))
  } else {
    basePreset = {
      name: newPresetForm.name,
      description: newPresetForm.description,
      icon: '📋',
      default: { collect: true, analyze: false, push: false, report_mode: 'current' },
      periods: {},
    }
  }

  basePreset.name = newPresetForm.name
  basePreset.description = newPresetForm.description

  timelineConfig.value.presets[newPresetForm.key] = basePreset
  saveTimeline()

  showNewPresetDialog.value = false
  newPresetForm.key = ''
  newPresetForm.name = ''
  newPresetForm.description = ''
  newPresetForm.template = ''
  ElMessage.success('调度模式已创建')
}

function editPeriod(idx) {
  editingPeriodIdx.value = idx
  const period = editingPresetPeriods.value[idx]
  Object.assign(periodForm, {
    key: period.key,
    name: period.name,
    start: period.start,
    end: period.end,
    collect: period.collect || false,
    analyze: period.analyze || false,
    push: period.push || false,
    report_mode: period.report_mode || 'current',
  })
  showAddPeriodDialog.value = true
}

function deletePeriod(idx) {
  ElMessageBox.confirm('确定删除此时间段吗？', '确认', { type: 'warning' })
    .then(() => {
      const periods = editingPreset.value.periods
      const periodKey = editingPresetPeriods.value[idx].key
      delete periods[periodKey]
      saveTimeline()
      ElMessage.success('已删除')
    })
    .catch(() => {})
}

function savePeriod() {
  if (!periodForm.key || !periodForm.name) {
    ElMessage.warning('请填写时间段标识和名称')
    return
  }

  const preset = editingPreset.value
  if (!preset) return

  if (!preset.periods) preset.periods = {}
  preset.periods[periodForm.key] = {
    name: periodForm.name,
    start: periodForm.start,
    end: periodForm.end,
    collect: periodForm.collect,
    analyze: periodForm.analyze,
    push: periodForm.push,
    report_mode: periodForm.report_mode,
  }

  if (timelineConfig.value.presets[preset.key]) {
    timelineConfig.value.presets[preset.key] = preset
  } else if (timelineConfig.value.custom[preset.key]) {
    timelineConfig.value.custom[preset.key] = preset
  }

  saveTimeline()
  showAddPeriodDialog.value = false
  editingPeriodIdx.value = -1
  ElMessage.success('时间段已保存')
}

async function saveTimeline() {
  const config = await configApi.getFullConfig()
  config.timeline = {
    presets: timelineConfig.value.presets,
    custom: timelineConfig.value.custom,
  }
  await configApi.updateFullConfig(config)
}

watch(showAddPeriodDialog, (val) => {
  if (!val) {
    editingPeriodIdx.value = -1
    Object.assign(periodForm, {
      key: '',
      name: '',
      start: '09:00',
      end: '11:00',
      collect: true,
      analyze: false,
      push: false,
      report_mode: 'current',
    })
  }
})
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

.header-actions {
  display: flex;
  gap: 8px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 20px 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.active-preset-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preset-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.preset-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.preset-name {
  font-size: 16px;
  font-weight: 600;
}

.preset-desc {
  font-size: 13px;
  color: #909399;
}

.period-timeline {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.period-block {
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  min-width: 100px;
  text-align: center;
}

.period-block.bg-blue { background: #ecf5ff; border-color: #b3d8ff; }
.period-block.bg-purple { background: #f3e8ff; border-color: #d8b3ff; }
.period-block.bg-gray { background: #f5f7fa; border-color: #e4e7ed; }
.period-block.bg-white { background: #fff; border-color: #e4e7ed; }
.period-block.gradient-blue-purple { background: linear-gradient(135deg, #ecf5ff, #f3e8ff); border-color: #b3d8ff; }

.period-time {
  font-size: 12px;
  font-weight: 600;
  color: #303133;
}

.period-label {
  font-size: 11px;
  color: #606266;
  margin: 2px 0;
}

.period-icons {
  font-size: 12px;
  display: flex;
  justify-content: center;
  gap: 4px;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.preset-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
}

.preset-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}

.preset-card.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.preset-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.preset-icon {
  font-size: 24px;
}

.preset-card-info {
  flex: 1;
  min-width: 0;
}

.preset-card-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.preset-card-desc {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preset-card-periods {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mini-period {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  padding: 3px 6px;
  background: #f5f7fa;
  border-radius: 4px;
}

.mini-time {
  color: #606266;
  font-weight: 500;
}

.mini-actions {
  display: flex;
  gap: 4px;
}

.mini-collect { color: #67c23a; }
.mini-analyze { color: #e6a23c; }
.mini-push { color: #409eff; }

.period-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.period-edit-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.period-edit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #fafbfc;
}

.period-edit-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.period-edit-actions {
  display: flex;
  gap: 4px;
}

.period-edit-body {
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.period-time-range {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}

.period-toggles {
  display: flex;
  gap: 6px;
}
</style>
