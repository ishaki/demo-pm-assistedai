import { useState, useEffect, useCallback } from 'react';
import machineService from '../services/machineService';

/**
 * Custom hook for fetching and managing machines data
 */
export const useMachines = (filters = {}) => {
  const [machines, setMachines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Stringify filters for stable comparison
  const filtersKey = JSON.stringify(filters);

  const fetchMachines = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await machineService.getAllMachines(filters);
      setMachines(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch machines');
      console.error('Error fetching machines:', err);
    } finally {
      setLoading(false);
    }
  }, [filtersKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchMachines();
  }, [fetchMachines]);

  return {
    machines,
    loading,
    error,
    refetch: fetchMachines
  };
};

export default useMachines;
