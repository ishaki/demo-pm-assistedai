import { useState, useEffect, useCallback } from 'react';
import workOrderService from '../services/workOrderService';

/**
 * Custom hook for fetching and managing work orders data
 */
export const useWorkOrders = (filters = {}) => {
  const [workOrders, setWorkOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Stringify filters for stable comparison
  const filtersKey = JSON.stringify(filters);

  const fetchWorkOrders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await workOrderService.getAllWorkOrders(filters);
      setWorkOrders(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch work orders');
      console.error('Error fetching work orders:', err);
    } finally {
      setLoading(false);
    }
  }, [filtersKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchWorkOrders();
  }, [fetchWorkOrders]);

  return {
    workOrders,
    loading,
    error,
    refetch: fetchWorkOrders
  };
};

export default useWorkOrders;
