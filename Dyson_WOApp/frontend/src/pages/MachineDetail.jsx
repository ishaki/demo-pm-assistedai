import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Dialog, DialogContent, DialogActions } from '../components/ui/Dialog';
import { Table, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

import machineService from '../services/machineService';
import aiService from '../services/aiService';
import { formatDate, formatDateTime, formatDaysUntilPM } from '../utils/dateUtils';
import {
  getPMStatusLabel,
  getPMStatusVariant,
  getWorkOrderStatusLabel,
  getWorkOrderStatusVariant,
  getDecisionLabel,
  getDecisionVariant,
  getConfidenceVariant,
} from '../utils/statusUtils';

const MachineDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [machine, setMachine] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [aiDialogOpen, setAiDialogOpen] = useState(false);
  const [aiDecision, setAiDecision] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  const fetchMachineDetails = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await machineService.getMachineById(id);
      setMachine(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch machine details');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchMachineDetails();
  }, [fetchMachineDetails]);

  const handleGetAIDecision = async () => {
    try {
      setAiLoading(true);
      const decision = await aiService.getDecision(id);
      setAiDecision(decision);
      setAiDialogOpen(true);
      // Refresh machine data to show new AI decision
      await fetchMachineDetails();
    } catch (err) {
      alert('Failed to get AI decision: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAiLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-error-light border border-error rounded-lg p-4 flex items-start justify-between">
        <div className="flex items-start gap-3">
          <span className="material-icons-round text-error">error</span>
          <span className="text-error font-medium">{error}</span>
        </div>
        <Button variant="text" size="sm" onClick={fetchMachineDetails}>Retry</Button>
      </div>
    );
  }

  if (!machine) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center gap-3">
        <span className="material-icons-round text-blue-600">info</span>
        <span className="text-blue-800">Machine not found</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 -mx-6 -mt-6 px-6 py-4 sticky top-0 z-10">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <button
              onClick={() => navigate('/machines')}
              className="inline-flex items-center text-sm font-medium text-gray-600 hover:text-primary transition-colors mb-2"
            >
              <span className="material-icons-round text-base mr-1">arrow_back</span>
              BACK TO LIST
            </button>
            <div className="flex items-center gap-4">
              <h1 className="text-3xl font-bold text-gray-800">{machine.machine_id}</h1>
              <Badge variant={getPMStatusVariant(machine.pm_status)}>
                {getPMStatusLabel(machine.pm_status)}
              </Badge>
            </div>
          </div>
          <Button
            variant="primary"
            startIcon="smart_toy"
            onClick={handleGetAIDecision}
            disabled={aiLoading}
          >
            {aiLoading ? 'Getting AI Decision...' : 'Get AI Decision'}
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Machine Information */}
        <Card>
          <CardContent>
            <div className="flex items-center border-b border-gray-200 pb-4 mb-6">
              <span className="material-icons-round text-gray-600 mr-2">precision_manufacturing</span>
              <h2 className="text-lg font-semibold text-gray-800">Machine Information</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-y-6 gap-x-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">Machine ID</label>
                <p className="text-base font-medium text-gray-800">{machine.machine_id}</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">Name</label>
                <p className="text-base font-medium text-gray-800">{machine.name}</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">Location</label>
                <p className="text-base font-medium text-gray-800">{machine.location}</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">Status</label>
                <span className="inline-flex items-center text-sm font-medium text-success">
                  <span className="w-2 h-2 bg-success rounded-full mr-2"></span>
                  Active
                </span>
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">Description</label>
                <p className="text-sm text-gray-600">{machine.description || 'N/A'}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* PM Schedule */}
        <Card>
          <CardContent>
            <div className="flex items-center justify-between border-b border-gray-200 pb-4 mb-6">
              <div className="flex items-center">
                <span className="material-icons-round text-gray-600 mr-2">schedule</span>
                <h2 className="text-lg font-semibold text-gray-800">PM Schedule</h2>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-y-6 gap-x-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">PM Frequency</label>
                <p className="text-base font-medium text-gray-800">{machine.pm_frequency}</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">PM Status</label>
                <Badge variant={getPMStatusVariant(machine.pm_status)}>
                  {getPMStatusLabel(machine.pm_status)}
                </Badge>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">Last PM Date</label>
                <p className="text-base font-medium text-gray-800">{formatDate(machine.last_pm_date)}</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">Next PM Date</label>
                <p className="text-base font-medium text-gray-800">{formatDate(machine.next_pm_date)}</p>
              </div>
              <div className="md:col-span-2 mt-2">
                <div className="bg-blue-50 rounded-lg p-4 border border-blue-100 flex items-center justify-between">
                  <div>
                    <label className="block text-xs font-medium text-blue-600 uppercase tracking-wider">Days Until PM</label>
                    <p className="text-3xl font-bold text-primary">{formatDaysUntilPM(machine.days_until_pm)}</p>
                  </div>
                  <span className="material-icons-round text-primary opacity-20 text-5xl">hourglass_empty</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Supplier Information */}
        <Card>
          <CardContent className="flex flex-col h-full">
            <div className="flex items-center border-b border-gray-200 pb-4 mb-6">
              <span className="material-icons-round text-gray-600 mr-2">business</span>
              <h2 className="text-lg font-semibold text-gray-800">Supplier Information</h2>
            </div>
            <div className="grid grid-cols-1 gap-y-6">
              <div>
                <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">Assigned Supplier</label>
                <div className="flex items-center">
                  <div className="w-8 h-8 rounded bg-gray-200 flex items-center justify-center text-xs font-bold text-gray-500 mr-3">
                    {machine.assigned_supplier?.substring(0, 2).toUpperCase() || 'N/A'}
                  </div>
                  <p className="text-base font-medium text-gray-800">{machine.assigned_supplier || 'N/A'}</p>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">Supplier Email</label>
                <a
                  href={`mailto:${machine.supplier_email}`}
                  className="text-base font-medium text-primary hover:underline"
                >
                  {machine.supplier_email || 'N/A'}
                </a>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Active Work Orders */}
        <Card>
          <CardContent className="flex flex-col h-full">
            <div className="flex items-center justify-between border-b border-gray-200 pb-4 mb-6">
              <div className="flex items-center">
                <span className="material-icons-round text-gray-600 mr-2">assignment</span>
                <h2 className="text-lg font-semibold text-gray-800">
                  Active Work Orders ({machine.work_orders?.length || 0})
                </h2>
              </div>
            </div>
            <div className="flex-grow">
              {machine.work_orders && machine.work_orders.length > 0 ? (
                machine.work_orders.map((wo) => (
                  <div
                    key={wo.id}
                    className="border border-gray-200 rounded-lg p-4 bg-gray-50 hover:bg-gray-100 transition-colors cursor-pointer group mb-3"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="text-sm font-bold text-gray-800 group-hover:text-primary transition-colors">
                        {wo.wo_number}
                      </h3>
                      <Badge variant={getWorkOrderStatusVariant(wo.status)} size="sm">
                        {getWorkOrderStatusLabel(wo.status)}
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-600 mb-2">Created: {formatDateTime(wo.created_at)}</p>
                    {wo.priority && (
                      <div className="flex items-center">
                        <span className="text-xs font-medium text-gray-600 mr-2">Priority:</span>
                        <span className="text-xs font-bold text-error">{wo.priority}</span>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-600">No active work orders</p>
              )}
            </div>
            <div className="mt-6 pt-4 border-t border-gray-200">
              <button
                onClick={() => navigate('/work-orders')}
                className="w-full py-2 px-4 border border-primary text-primary hover:bg-primary hover:text-white rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary uppercase tracking-wide"
              >
                View All Work Orders
              </button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Maintenance History */}
      <Card>
        <div className="px-6 py-5 border-b border-gray-200 flex items-center">
          <span className="material-icons-round text-gray-600 mr-2">history</span>
          <h2 className="text-lg font-semibold text-gray-800">Maintenance History</h2>
        </div>
        {machine.maintenance_history && machine.maintenance_history.length > 0 ? (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell header>Date</TableCell>
                <TableCell header>Type</TableCell>
                <TableCell header>Performed By</TableCell>
                <TableCell header>Notes</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {machine.maintenance_history.map((history) => (
                <TableRow key={history.id} hover>
                  <TableCell>
                    <span className="font-medium">{formatDate(history.maintenance_date)}</span>
                  </TableCell>
                  <TableCell>
                    <Badge variant={history.maintenance_type === 'Preventive' ? 'info' : 'warning'} size="sm">
                      {history.maintenance_type || 'N/A'}
                    </Badge>
                  </TableCell>
                  <TableCell>{history.performed_by || 'N/A'}</TableCell>
                  <TableCell>
                    <span className="text-sm text-gray-600">{history.notes || 'N/A'}</span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="px-6 py-8 text-center">
            <p className="text-sm text-gray-600">No maintenance history available</p>
          </div>
        )}
      </Card>

      {/* AI Decision Dialog */}
      <Dialog
        open={aiDialogOpen}
        onClose={() => setAiDialogOpen(false)}
        title="AI Decision Result"
        maxWidth="sm"
      >
        <DialogContent>
          {aiDecision && (
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-600 mb-1">Decision</p>
                <Badge variant={getDecisionVariant(aiDecision.decision)}>
                  {getDecisionLabel(aiDecision.decision)}
                </Badge>
              </div>

              <div>
                <p className="text-sm text-gray-600 mb-1">Priority</p>
                <p className="text-base font-semibold text-gray-800">{aiDecision.priority}</p>
              </div>

              <div>
                <p className="text-sm text-gray-600 mb-1">Confidence</p>
                <Badge variant={getConfidenceVariant(aiDecision.confidence)}>
                  {(aiDecision.confidence * 100).toFixed(0)}%
                </Badge>
              </div>

              <div>
                <p className="text-sm text-gray-600 mb-1">Explanation</p>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                  <p className="text-sm text-gray-700">{aiDecision.explanation}</p>
                </div>
              </div>

              <div className="pt-2 border-t border-gray-200">
                <p className="text-xs text-gray-500">
                  Provider: {aiDecision.llm_provider} | Model: {aiDecision.llm_model}
                </p>
              </div>
            </div>
          )}
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={() => setAiDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default MachineDetail;
