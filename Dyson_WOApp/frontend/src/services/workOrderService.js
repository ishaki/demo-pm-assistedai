import api from './api';

export const workOrderService = {
  /**
   * Get all work orders with optional filters
   */
  getAllWorkOrders: async (params = {}) => {
    const response = await api.get('/work-orders/', { params });
    return response.data;
  },

  /**
   * Get work order by ID
   */
  getWorkOrderById: async (woId) => {
    const response = await api.get(`/work-orders/${woId}`);
    return response.data;
  },

  /**
   * Create a new work order
   */
  createWorkOrder: async (workOrderData) => {
    const response = await api.post('/work-orders', workOrderData);
    return response.data;
  },

  /**
   * Update an existing work order
   */
  updateWorkOrder: async (woId, workOrderData) => {
    const response = await api.put(`/work-orders/${woId}`, workOrderData);
    return response.data;
  },

  /**
   * Approve a work order
   */
  approveWorkOrder: async (woId, approvedBy) => {
    const response = await api.post(`/work-orders/${woId}/approve`, {
      approved_by: approvedBy
    });
    return response.data;
  },

  /**
   * Complete a work order
   */
  completeWorkOrder: async (woId) => {
    const response = await api.post(`/work-orders/${woId}/complete`);
    return response.data;
  },

  /**
   * Cancel a work order
   */
  cancelWorkOrder: async (woId) => {
    const response = await api.post(`/work-orders/${woId}/cancel`);
    return response.data;
  },

  /**
   * Delete a work order
   */
  deleteWorkOrder: async (woId) => {
    await api.delete(`/work-orders/${woId}`);
  },
};

export default workOrderService;
