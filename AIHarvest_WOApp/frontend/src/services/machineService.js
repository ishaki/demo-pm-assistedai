import api from './api';

export const machineService = {
  /**
   * Get all machines with optional filters
   */
  getAllMachines: async (params = {}) => {
    const response = await api.get('/machines/', { params });
    return response.data;
  },

  /**
   * Get machine by ID with full details
   */
  getMachineById: async (machineId) => {
    const response = await api.get(`/machines/${machineId}`);
    return response.data;
  },

  /**
   * Get maintenance history for a machine
   */
  getMaintenanceHistory: async (machineId, limit = 20) => {
    const response = await api.get(`/machines/${machineId}/maintenance-history`, {
      params: { limit }
    });
    return response.data;
  },

  /**
   * Create a new machine
   */
  createMachine: async (machineData) => {
    const response = await api.post('/machines', machineData);
    return response.data;
  },

  /**
   * Update an existing machine
   */
  updateMachine: async (machineId, machineData) => {
    const response = await api.put(`/machines/${machineId}`, machineData);
    return response.data;
  },

  /**
   * Delete a machine
   */
  deleteMachine: async (machineId) => {
    await api.delete(`/machines/${machineId}`);
  },
};

export default machineService;
