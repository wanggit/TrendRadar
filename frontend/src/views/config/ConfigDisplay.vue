<template>
  <div>
    <div class="module-header">
      <h3>推送内容控制</h3>
    </div>

    <el-alert
      title="控制推送消息中展示哪些区域，以及独立展示区的配置"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <el-form :model="form" label-width="160px" style="max-width: 700px">
      <el-divider content-position="left">区域开关与排序</el-divider>

      <el-form-item label="推送区域">
        <draggable
          v-model="regionOrder"
          item-key="key"
          class="region-list"
          handle=".drag-handle"
        >
          <template #item="{ element }">
            <div class="region-item" :class="{ disabled: !form.regions[element.key] }">
              <el-icon class="drag-handle"><Rank /></el-icon>
              <span class="region-name">{{ regionLabels[element.key] }}</span>
              <el-switch
                v-model="form.regions[element.key]"
                size="small"
              />
            </div>
          </template>
        </draggable>
        <div style="color: #909399; font-size: 12px; margin-top: 4px">
          拖拽调整顺序，开关控制是否展示
        </div>
      </el-form-item>

      <el-divider content-position="left">独立展示区配置</el-divider>

      <el-form-item label="每源最多展示">
        <el-input-number v-model="form.standalone.max_items" :min="1" :max="50" style="width: 120px" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">每个源最多展示的条目数</span>
      </el-form-item>

      <el-form-item label="展示的热榜平台">
        <div class="checkbox-grid">
          <el-checkbox
            v-for="p in platforms"
            :key="p.source_id"
            v-model="form.standalone.platforms"
            :label="p.source_id"
          >
            {{ p.name }}
          </el-checkbox>
        </div>
      </el-form-item>

      <el-form-item label="展示的 RSS 源">
        <div class="checkbox-grid">
          <el-checkbox
            v-for="feed in rssFeeds"
            :key="feed.id"
            v-model="form.standalone.rss_feeds"
            :label="feed.id"
          >
            {{ feed.name }}
          </el-checkbox>
        </div>
        <div v-if="rssFeeds.length === 0" style="color: #909399; font-size: 12px">
          暂无 RSS 源，请先在 RSS 订阅 页面添加
        </div>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Rank } from '@element-plus/icons-vue'
import { configApi } from '@/api/config'
import { dataApi } from '@/api/data'
import { ElMessage } from 'element-plus'

import draggable from 'vuedraggable'

const saving = ref(false)
const platforms = ref([])
const rssFeeds = ref([])

const regionLabels = {
  hotlist: '热榜区域',
  new_items: '新增热点',
  rss: 'RSS 订阅',
  standalone: '独立展示',
  ai_analysis: 'AI 分析',
}

const defaultRegions = {
  hotlist: true,
  new_items: true,
  rss: true,
  standalone: false,
  ai_analysis: false,
}

const form = reactive({
  region_order: ['hotlist', 'new_items', 'rss', 'standalone', 'ai_analysis'],
  regions: { ...defaultRegions },
  standalone: {
    max_items: 5,
    platforms: [],
    rss_feeds: [],
  },
})

const regionOrder = ref([])

let originalConfig = null

onMounted(async () => {
  await loadConfig()
  platforms.value = await dataApi.getPlatforms()
})

async function loadConfig() {
  const config = await configApi.getFullConfig()
  const display = config.display || {}

  const regions = display.regions || {}
  const regionOrder = display.region_order || ['hotlist', 'new_items', 'rss', 'standalone', 'ai_analysis']
  const standalone = display.standalone || { max_items: 5, platforms: [], rss_feeds: [] }

  form.region_order = regionOrder
  regionOrder.value = [...regionOrder]
  form.regions = { ...defaultRegions, ...regions }
  form.standalone = { ...standalone }

  rssFeeds.value = (await dataApi.getRssFeeds()).filter(f => f.enabled).map(f => ({
    id: f.feed_key,
    name: f.name,
  }))

  originalConfig = JSON.parse(JSON.stringify({
    region_order: form.region_order,
    regions: form.regions,
    standalone: form.standalone,
  }))
}

async function save() {
  saving.value = true
  try {
    form.region_order = [...regionOrder.value]
    const config = await configApi.getFullConfig()
    config.display = {
      region_order: form.region_order,
      regions: form.regions,
      standalone: form.standalone,
    }
    await configApi.updateFullConfig(config)
    ElMessage.success('推送内容配置已保存')
    originalConfig = JSON.parse(JSON.stringify({
      region_order: form.region_order,
      regions: form.regions,
      standalone: form.standalone,
    }))
  } finally {
    saving.value = false
  }
}

function reset() {
  Object.assign(form, JSON.parse(JSON.stringify(originalConfig)))
  regionOrder.value = [...form.region_order]
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

.region-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.region-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #f5f7fa;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  transition: all 0.2s;
}

.region-item.disabled {
  opacity: 0.5;
}

.drag-handle {
  cursor: grab;
  color: #909399;
}

.drag-handle:active {
  cursor: grabbing;
}

.region-name {
  flex: 1;
  font-size: 13px;
  color: #303133;
}

.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
</style>
