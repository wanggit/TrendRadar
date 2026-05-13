<template>
  <div class="news-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>新闻浏览</span>
          <el-tabs v-model="activeTab" style="width: auto" @tab-change="onTabChange">
            <el-tab-pane label="平台热榜" name="platform" />
            <el-tab-pane label="RSS 订阅" name="rss" />
          </el-tabs>
        </div>
      </template>

      <!-- Platform Hot Lists -->
      <div v-if="activeTab === 'platform'">
        <div class="filters">
          <el-input v-model="keyword" placeholder="搜索关键词" style="width: 200px" @keyup.enter="loadPlatformNews" />
          <el-select v-model="platformFilter" placeholder="平台" style="width: 150px" @change="loadPlatformNews">
            <el-option label="全部" :value="null" />
            <el-option v-for="p in platforms" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-button type="primary" @click="loadPlatformNews">搜索</el-button>
          <el-button
            type="danger"
            :disabled="selectedNews.length === 0"
            @click="handleBulkDeleteNews"
          >批量删除 ({{ selectedNews.length }})</el-button>
        </div>

        <el-table
          :data="news"
          style="width: 100%"
          v-loading="loading"
          @selection-change="onNewsSelectionChange"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="title" label="标题" min-width="300" show-overflow-tooltip />
          <el-table-column prop="rank" label="排名" width="80" />
          <el-table-column label="平台" width="120">
            <template #default="{ row }">
              {{ getPlatformName(row.platform_id) }}
            </template>
          </el-table-column>
          <el-table-column label="抓取时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.crawl_time) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-link :href="row.url" target="_blank">查看</el-link>
              <el-button link type="danger" @click="deleteNews(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination">
          <el-pagination
            v-model:current-page="page"
            :page-size="limit"
            :total="total"
            layout="prev, pager, next"
            @current-change="loadPlatformNews"
          />
        </div>
      </div>

      <!-- RSS Items -->
      <div v-else>
        <div class="filters">
          <el-input v-model="rssKeyword" placeholder="搜索关键词" style="width: 200px" @keyup.enter="loadRssItems" />
          <el-select v-model="rssFeedFilter" placeholder="RSS 源" style="width: 180px" @change="loadRssItems">
            <el-option label="全部" :value="null" />
            <el-option v-for="f in rssFeeds" :key="f.id" :label="f.name" :value="f.id" />
          </el-select>
          <el-button type="primary" @click="loadRssItems">搜索</el-button>
          <el-button
            type="danger"
            :disabled="selectedRss.length === 0"
            @click="handleBulkDeleteRss"
          >批量删除 ({{ selectedRss.length }})</el-button>
        </div>

        <el-table
          :data="rssItems"
          style="width: 100%"
          v-loading="rssLoading"
          @selection-change="onRssSelectionChange"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="title" label="标题" min-width="300" show-overflow-tooltip />
          <el-table-column label="来源" width="150">
            <template #default="{ row }">
              {{ getFeedName(row.feed_id) }}
            </template>
          </el-table-column>
          <el-table-column label="发布时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.published_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-link :href="row.url" target="_blank">查看</el-link>
              <el-button link type="danger" @click="deleteRssItem(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination">
          <el-pagination
            v-model:current-page="rssPage"
            :page-size="limit"
            :total="rssTotal"
            layout="prev, pager, next"
            @current-change="loadRssItems"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { dataApi } from '@/api/data'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const activeTab = ref('platform')

// Platform news
const news = ref([])
const platforms = ref([])
const loading = ref(false)
const keyword = ref('')
const platformFilter = ref(null)
const page = ref(1)
const limit = 20
const total = ref(0)
const selectedNews = ref([])

// RSS items
const rssItems = ref([])
const rssFeeds = ref([])
const rssLoading = ref(false)
const rssKeyword = ref('')
const rssFeedFilter = ref(null)
const rssPage = ref(1)
const rssTotal = ref(0)
const selectedRss = ref([])

onMounted(async () => {
  platforms.value = await dataApi.getPlatforms()
  rssFeeds.value = await dataApi.getRssFeeds()
  await loadPlatformNews()
})

async function onTabChange(tab) {
  if (tab === 'rss' && rssItems.value.length === 0) {
    await loadRssItems()
  }
}

async function loadPlatformNews() {
  loading.value = true
  try {
    const data = await dataApi.getNews({
      limit,
      offset: (page.value - 1) * limit,
      keyword: keyword.value || undefined,
      platform_id: platformFilter.value,
    })
    news.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadRssItems() {
  rssLoading.value = true
  try {
    const data = await dataApi.getRssItems({
      limit,
      offset: (rssPage.value - 1) * limit,
      keyword: rssKeyword.value || undefined,
      feed_id: rssFeedFilter.value,
    })
    rssItems.value = data.items
    rssTotal.value = data.total
  } finally {
    rssLoading.value = false
  }
}

function getPlatformName(platformId) {
  const p = platforms.value.find(x => x.id === platformId)
  return p ? p.name : '-'
}

function getFeedName(feedId) {
  const f = rssFeeds.value.find(x => x.id === feedId)
  return f ? f.name : '-'
}

function formatTime(time) {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}

function onNewsSelectionChange(selection) {
  selectedNews.value = selection
}

function onRssSelectionChange(selection) {
  selectedRss.value = selection
}

async function deleteNews(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」吗？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await dataApi.deleteNewsItem(row.id)
    ElMessage.success('已删除')
    loadPlatformNews()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function deleteRssItem(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」吗？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await dataApi.deleteRssItem(row.id)
    ElMessage.success('已删除')
    loadRssItems()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function handleBulkDeleteNews() {
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedNews.value.length} 条新闻吗？`,
      '批量删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    const ids = selectedNews.value.map(x => x.id)
    await dataApi.bulkDeleteNewsItems(ids)
    ElMessage.success(`已删除 ${ids.length} 条新闻`)
    loadPlatformNews()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('批量删除失败')
    }
  }
}

async function handleBulkDeleteRss() {
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedRss.value.length} 条 RSS 内容吗？`,
      '批量删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    const ids = selectedRss.value.map(x => x.id)
    await dataApi.bulkDeleteRssItems(ids)
    ElMessage.success(`已删除 ${ids.length} 条 RSS 内容`)
    loadRssItems()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('批量删除失败')
    }
  }
}
</script>

<style scoped>
.news-page {
  padding: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>
