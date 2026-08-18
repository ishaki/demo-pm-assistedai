import api from './api';

export const aiService = {
  /**
   * Get AI decision for a machine
   */
  getDecision: async (machineId) => {
    const response = await api.post(`/ai/decision/${machineId}`);
    return response.data;
  },

  /**
   * Execute an AI decision
   */
  executeDecision: async (aiDecisionId, force = false) => {
    const response = await api.post(`/ai/decision/${aiDecisionId}/execute`, null, {
      params: { force }
    });
    return response.data;
  },

  /**
   * Get recent AI decisions
   */
  getRecentDecisions: async (params = {}) => {
    const response = await api.get('/ai/decisions/recent', { params });
    return response.data;
  },

  /**
   * Get AI decision by ID
   */
  getDecisionById: async (aiDecisionId) => {
    const response = await api.get(`/ai/decisions/${aiDecisionId}`);
    return response.data;
  },

  /**
   * Get AI statistics
   */
  getStatistics: async () => {
    const response = await api.get('/ai/statistics');
    return response.data;
  },
};

export default aiService;
