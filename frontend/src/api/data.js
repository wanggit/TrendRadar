import api from './index'

export const dataApi = {
  getPlatforms() {
    return api.get('/data/platforms')
  },
  createPlatform(data) {
    return api.post('/data/platforms', data)
  },
  deletePlatform(sourceId) {
    return api.delete(`/data/platforms/${sourceId}`)
  },
  getNews(params) {
    return api.get('/data/news', { params })
  },
  getRssFeeds() {
    return api.get('/data/rss/feeds')
  },
  createRssFeed(data) {
    return api.post('/data/rss/feeds', data)
  },
  updateRssFeed(feedId, data) {
    return api.put(`/data/rss/feeds/${feedId}`, data)
  },
  deleteRssFeed(feedId) {
    return api.delete(`/data/rss/feeds/${feedId}`)
  },
  getRssItems(params) {
    return api.get('/data/rss/items', { params })
  },
  deleteNewsItem(itemId) {
    return api.delete(`/data/news/${itemId}`)
  },
  bulkDeleteNewsItems(ids) {
    return api.post('/data/news/bulk-delete', { ids })
  },
  deleteRssItem(itemId) {
    return api.delete(`/data/rss/items/${itemId}`)
  },
  bulkDeleteRssItems(ids) {
    return api.post('/data/rss/items/bulk-delete', { ids })
  },
}
