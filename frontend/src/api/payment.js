import api from './index'

export const paymentApi = {
  createOrder(data) {
    return api.post('/payment/create', data)
  },
  getOrders() {
    return api.get('/payment/orders')
  },
  getOrder(orderId) {
    return api.get(`/payment/orders/${orderId}`)
  },
  getOrderStatus(orderId) {
    return api.get(`/payment/orders/${orderId}/status`)
  },
}
