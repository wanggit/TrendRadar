<template>
  <div>
    <div class="module-header">
      <h3>RSS 订阅管理</h3>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon> 添加 RSS 源
      </el-button>
    </div>

    <el-alert
      title="提示"
      type="info"
      :closable="false"
      show-icon
      class="mb-4"
      style="margin-bottom: 16px"
    >
      配置要抓取的 RSS 源，拖拽表格行可调整优先级顺序。
    </el-alert>

    <el-form :model="globalForm" label-width="160px" style="max-width: 600px; margin-bottom: 20px">
      <el-form-item label="启用 RSS 抓取">
        <el-switch v-model="globalForm.enabled" @change="saveGlobal" />
      </el-form-item>

      <el-form-item label="启用新鲜度过滤">
        <el-switch v-model="globalForm.freshness_filter.enabled" @change="saveGlobal" />
      </el-form-item>

      <el-form-item label="最大文章年龄 (天)" v-if="globalForm.freshness_filter.enabled">
        <el-input-number v-model="globalForm.freshness_filter.max_age_days" :min="1" :max="365" style="width: 120px" @change="saveGlobal" />
      </el-form-item>
    </el-form>

    <el-table :data="feeds" style="width: 100%" row-key="id">
      <el-table-column prop="feed_key" label="源 ID" width="150" />
      <el-table-column prop="name" label="名称" width="150" />
      <el-table-column prop="feed_url" label="URL" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'danger'">
            {{ row.enabled ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click="toggleFeed(row)">
            {{ row.enabled ? '禁用' : '启用' }}
          </el-button>
          <el-button size="small" type="danger" @click="deleteFeed(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAddDialog" title="添加 RSS 源" width="550px">
      <el-form :model="newFeed" label-width="100px">
        <el-form-item label="源 ID">
          <el-input v-model="newFeed.feed_key" placeholder="例如: my-blog" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="newFeed.name" placeholder="例如: 我的博客" />
        </el-form-item>
        <el-form-item label="RSS URL">
          <el-input v-model="newFeed.feed_url" placeholder="https://example.com/feed.xml" />
        </el-form-item>
        <el-form-item label="最大文章年龄">
          <el-input-number v-model="newFeed.max_age_days" :min="1" :max="365" placeholder="留空使用全局设置" style="width: 120px" />
          <span style="color: #909399; font-size: 12px; margin-left: 8px">天，留空使用全局设置</span>
        </el-form-item>
      </el-form>

      <el-divider content-position="left">RSS 灵感库</el-divider>
      <div class="rss-inspiration">
        <div class="inspiration-category">
          <div class="category-title">🔍 Bing 新闻（修改 q= 参数即可监控任何话题）</div>
          <div class="category-items">
            <div
              v-for="src in bingSources"
              :key="src.label"
              class="inspiration-item"
              @click="fillRssUrl(src.url)"
            >
              {{ src.label }}
            </div>
          </div>
        </div>
        <div class="inspiration-category">
          <div class="category-title">📰 常用 RSS 源</div>
          <div class="category-items">
            <div
              v-for="src in commonSources"
              :key="src.label"
              class="inspiration-item"
              @click="fillRssUrl(src.url)"
            >
              {{ src.label }}
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addFeed" :disabled="!newFeed.feed_key || !newFeed.name || !newFeed.feed_url">
          添加
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { configApi } from '@/api/config'
import { dataApi } from '@/api/data'
import { ElMessage, ElMessageBox } from 'element-plus'

const feeds = ref([])
const showAddDialog = ref(false)

const globalForm = reactive({
  enabled: true,
  freshness_filter: {
    enabled: false,
    max_age_days: 7,
  },
})

const newFeed = reactive({
  feed_key: '',
  name: '',
  feed_url: '',
  max_age_days: 1,
})

const bingSources = [
  { label: '🚀 科技/编程', url: 'https://www.bing.com/news/search?q=科技+编程&format=RSS' },
  { label: '🌍 全球新闻', url: 'https://www.bing.com/news/search?q=全球新闻&format=RSS' },
  { label: '🤖 人工智能', url: 'https://www.bing.com/news/search?q=人工智能&format=RSS' },
  { label: '💰 黄金/财经', url: 'https://www.bing.com/news/search?q=黄金价格+走势&format=RSS' },
]

const commonSources = [
  { label: '📱 36氪', url: 'https://36kr.com/feed' },
  { label: '💻 少数派', url: 'https://sspai.com/feed' },
  { label: '🐙 GitHub Trending', url: 'https://github.com/trending.atom' },
  { label: '🔥 Hacker News', url: 'https://hnrss.org/frontpage' },
  { label: '📦 Product Hunt', url: 'https://www.producthunt.com/feed' },
  { label: '🐦 V2EX', url: 'https://www.v2ex.com/index.xml' },
  { label: '📝 虎嗅', url: 'https://www.huxiu.com/rss/0' },
  { label: '🏠 IT之家', url: 'https://www.ithome.com/rss/' },
]

onMounted(async () => {
  await loadConfig()
  await loadFeeds()
})

async function loadConfig() {
  const config = await configApi.getFullConfig()
  const rss = config.rss || {}
  globalForm.enabled = rss.enabled ?? true
  globalForm.freshness_filter = rss.freshness_filter || { enabled: false, max_age_days: 7 }
}

async function loadFeeds() {
  feeds.value = await dataApi.getRssFeeds()
}

async function saveGlobal() {
  const config = await configApi.getFullConfig()
  config.rss = {
    ...config.rss,
    enabled: globalForm.enabled,
    freshness_filter: globalForm.freshness_filter,
  }
  await configApi.updateFullConfig(config)
  ElMessage.success('RSS 全局配置已保存')
}

async function toggleFeed(row) {
  row.enabled = !row.enabled
  await dataApi.updateRssFeed(row.id, {
    feed_url: row.feed_url,
    name: row.name,
    feed_key: row.feed_key,
    max_age_days: row.max_age_days,
    enabled: row.enabled,
  })
  ElMessage.success(`已${row.enabled ? '启用' : '禁用'} ${row.name}`)
}

async function deleteFeed(row) {
  await ElMessageBox.confirm(`确定删除 RSS 源 "${row.name}" 吗？`, '确认', { type: 'warning' })
  await dataApi.deleteRssFeed(row.id)
  feeds.value = feeds.value.filter(f => f.id !== row.id)
  ElMessage.success('已删除')
}

async function addFeed() {
  if (!newFeed.feed_key || !newFeed.name || !newFeed.feed_url) {
    ElMessage.warning('请填写源 ID、名称和 URL')
    return
  }

  if (!/^https?:\/\/.+/.test(newFeed.feed_url)) {
    ElMessage.warning('请输入有效的 URL 地址（以 http:// 或 https:// 开头）')
    return
  }

  if (!/^[a-z0-9_-]+$/.test(newFeed.feed_key)) {
    ElMessage.warning('源 ID 仅支持英文、数字、下划线和连字符')
    return
  }

  if (feeds.value.some(f => f.feed_key === newFeed.feed_key)) {
    ElMessage.warning('源 ID 已存在，请使用不同的 ID')
    return
  }

  await dataApi.createRssFeed({
    feed_key: newFeed.feed_key,
    name: newFeed.name,
    feed_url: newFeed.feed_url,
    max_age_days: newFeed.max_age_days,
  })

  showAddDialog.value = false
  newFeed.feed_key = ''
  newFeed.name = ''
  newFeed.feed_url = ''
  newFeed.max_age_days = 1
  await loadFeeds()
  ElMessage.success('RSS 源添加成功')
}

function fillRssUrl(url) {
  newFeed.feed_url = url
  ElMessage.success('已填入 RSS URL')
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

.rss-inspiration {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.inspiration-category {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 10px 12px;
}

.category-title {
  font-size: 12px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
}

.category-items {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.inspiration-item {
  padding: 4px 10px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  font-size: 11px;
  color: #409eff;
  cursor: pointer;
  transition: all 0.2s;
}

.inspiration-item:hover {
  background: #ecf5ff;
  border-color: #409eff;
}
</style>
