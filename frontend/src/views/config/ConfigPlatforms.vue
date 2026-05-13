<template>
  <div>
    <div class="module-header">
      <h3>热榜平台配置</h3>
      <el-button type="primary" @click="showAddDialog = true" :disabled="atLimit">
        <el-icon><Plus /></el-icon> 添加平台
      </el-button>
    </div>

    <el-alert
      v-if="atLimit"
      :title="`免费版最多 ${maxPlatforms} 个平台，请升级到专业版解锁更多`"
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
      title="提示"
      type="info"
      :closable="false"
      show-icon
      class="mb-4"
      style="margin-bottom: 16px"
    >
      配置要抓取的热榜平台，拖拽表格行可调整优先级顺序。
    </el-alert>

    <el-table :data="platforms" style="width: 100%" row-key="source_id">
      <el-table-column prop="source_id" label="平台 ID" width="180" />
      <el-table-column prop="name" label="名称" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'danger'">
            {{ row.enabled ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click="togglePlatform(row)">
            {{ row.enabled ? '禁用' : '启用' }}
          </el-button>
          <el-button size="small" type="danger" @click="deletePlatform(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAddDialog" title="添加平台" width="450px">
      <div class="preset-list">
        <div
          v-for="p in availablePresets"
          :key="p.source_id"
          class="preset-item"
          :class="{ selected: selectedPresets.includes(p.source_id) }"
          @click="togglePreset(p.source_id)"
        >
          <el-checkbox :model-value="selectedPresets.includes(p.source_id)" />
          <span>{{ p.name }}</span>
          <span class="preset-rate" :class="getRateClass(p.rate)">{{ p.rate }}</span>
          <span class="preset-id">{{ p.source_id }}</span>
        </div>
      </div>
      <div v-if="availablePresets.length === 0" class="empty-tip">
        所有预设平台已添加
      </div>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addPlatforms" :disabled="selectedPresets.length === 0">
          确定 ({{ selectedPresets.length }})
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Plus } from '@element-plus/icons-vue'
import { dataApi } from '@/api/data'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const platforms = ref([])
const showAddDialog = ref(false)
const selectedPresets = ref([])

const maxPlatforms = computed(() => {
  const tier = authStore.user?.tier
  if (tier === 'pro' || tier === 'enterprise') return 999
  return 3
})

const atLimit = computed(() => {
  const enabled = platforms.value.filter(p => p.enabled).length
  return enabled >= maxPlatforms.value
})

const PRESET_PLATFORMS = [
  // 高成功率平台（推荐）
  { source_id: '36kr', name: '36氪', rate: '100%' },
  { source_id: 'coolapk', name: '酷安', rate: '100%' },
  { source_id: 'github', name: 'GitHub Trending', rate: '100%' },
  { source_id: 'tieba', name: '百度贴吧', rate: '69%' },
  { source_id: 'sspai', name: '少数派', rate: '67%' },
  { source_id: 'v2ex', name: 'V2EX', rate: '67%' },
  { source_id: 'ithome', name: 'IT之家', rate: '待测试' },
  { source_id: 'huxiu', name: '虎嗅', rate: '待测试' },
  
  // 低成功率平台（不推荐）
  { source_id: 'zhihu', name: '知乎热榜', rate: '0%' },
  { source_id: 'douyin', name: '抖音热搜', rate: '0%' },
  { source_id: 'toutiao', name: '今日头条', rate: '0%' },
  { source_id: 'producthunt', name: 'Product Hunt', rate: '0%' },
  
  // 搜索链接平台（仅标题）
  { source_id: 'weibo', name: '微博热搜', rate: '标题' },
  { source_id: 'baidu', name: '百度热搜', rate: '标题' },
  { source_id: 'bilibili', name: 'B站热搜', rate: '标题' },
]

const availablePresets = computed(() => {
  const existingIds = new Set(platforms.value.map(p => p.source_id))
  return PRESET_PLATFORMS.filter(p => !existingIds.has(p.source_id))
})

onMounted(async () => {
  await loadPlatforms()
})

async function loadPlatforms() {
  platforms.value = await dataApi.getPlatforms()
}

async function togglePlatform(row) {
  row.enabled = !row.enabled
  await dataApi.createPlatform({ source_id: row.source_id, name: row.name, enabled: row.enabled })
  ElMessage.success(`已${row.enabled ? '启用' : '禁用'} ${row.name}`)
}

async function deletePlatform(row) {
  await ElMessageBox.confirm(`确定删除平台 "${row.name}" 吗？`, '确认', { type: 'warning' })
  await dataApi.deletePlatform(row.source_id)
  platforms.value = platforms.value.filter(p => p.source_id !== row.source_id)
  ElMessage.success('已删除')
}

function togglePreset(sourceId) {
  const idx = selectedPresets.value.indexOf(sourceId)
  if (idx === -1) {
    selectedPresets.value.push(sourceId)
  } else {
    selectedPresets.value.splice(idx, 1)
  }
}

function getRateClass(rate) {
  if (rate === '标题') return 'rate-search'
  if (rate === '待测试') return 'rate-testing'
  if (rate === '0%') return 'rate-fail'
  if (parseInt(rate) >= 60) return 'rate-success'
  return 'rate-partial'
}

async function addPlatforms() {
  if (selectedPresets.value.length === 0) {
    ElMessage.warning('请至少选择一个平台')
    return
  }

  const toAdd = PRESET_PLATFORMS.filter(p => selectedPresets.value.includes(p.source_id))
  for (const p of toAdd) {
    await dataApi.createPlatform({ ...p, enabled: true })
  }

  showAddDialog.value = false
  selectedPresets.value = []
  await loadPlatforms()
  ElMessage.success(`成功添加 ${toAdd.length} 个平台`)
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

.preset-list {
  max-height: 300px;
  overflow-y: auto;
}

.preset-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.preset-item:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.preset-item.selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.preset-id {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
}

.preset-rate {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.preset-rate.rate-success {
  background: #f0f9ff;
  color: #67c23a;
}

.preset-rate.rate-partial {
  background: #fdf6ec;
  color: #e6a23c;
}

.preset-rate.rate-fail {
  background: #fef0f0;
  color: #f56c6c;
}

.preset-rate.rate-search {
  background: #f4f4f5;
  color: #909399;
}

.preset-rate.rate-testing {
  background: #e6f7ff;
  color: #1890ff;
}

.empty-tip {
  text-align: center;
  color: #909399;
  padding: 20px;
}
</style>
