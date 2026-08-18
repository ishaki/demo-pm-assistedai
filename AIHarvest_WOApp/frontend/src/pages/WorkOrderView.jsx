import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Dialog, DialogContent, DialogActions } from '../components/ui/Dialog';
import { Table, TableHead, TableBody, TableRow, TableCell, TableSortLabel, TablePagination } from '../components/ui/Table';
import { useToast } from '../components/ui/Toast';

import useWorkOrders from '../hooks/useWorkOrders';
import workOrderService from '../services/workOrderService';
import machineService from '../services/machineService';
import { formatDateTime, formatDate } from '../utils/dateUtils';
import {
  getWorkOrderStatusLabel,
  getWorkOrderStatusVariant,
  getPriorityVariant,
} from '../utils/statusUtils';

const WorkOrderView = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [orderBy, setOrderBy] = useState('created_at');
  const [order, setOrder] = useState('desc');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const filters = statusFilter === 'all' ? {} : { status: statusFilter };
  const { workOrders, loading, error, refetch } = useWorkOrders(filters);

  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const [selectedWO, setSelectedWO] = useState(null);
  const [approverName, setApproverName] = useState('');
  const [approving, setApproving] = useState(false);

  // Schedule update dialog state
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [selectedWOForSchedule, setSelectedWOForSchedule] = useState(null);
  const [scheduledDate, setScheduledDate] = useState('');
  const [machineData, setMachineData] = useState(null);
  const [loadingMachine, setLoadingMachine] = useState(false);
  const [updatingSchedule, setUpdatingSchedule] = useState(false);

  // Confirmation dialog state
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null);
  const [confirmMessage, setConfirmMessage] = useState('');
  const [confirming, setConfirming] = useState(false);

  // Complete work order dialog state
  const [completeDialogOpen, setCompleteDialogOpen] = useState(false);
  const [selectedWOForComplete, setSelectedWOForComplete] = useState(null);
  const [completedDate, setCompletedDate] = useState('');
  const [completingWorkOrder, setCompletingWorkOrder] = useState(false);

  // Reset to first page when search or filter changes
  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
    setPage(0);
  };

  const handleFilterChange = (e) => {
    setStatusFilter(e.target.value);
    setPage(0);
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Sorting handler
  const handleSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  // Filter and sort work orders
  const filteredAndSortedWorkOrders = useMemo(() => {
    let filtered = workOrders.filter((wo) => {
      if (!searchTerm) return true;
      const searchLower = searchTerm.toLowerCase();
      return (
        wo.wo_number?.toLowerCase().includes(searchLower) ||
        wo.status?.toLowerCase().includes(searchLower) ||
        wo.priority?.toLowerCase().includes(searchLower) ||
        wo.creation_source?.toLowerCase().includes(searchLower) ||
        wo.machine_id?.toString().includes(searchLower) ||
        wo.machine_name?.toLowerCase().includes(searchLower)
      );
    });

    // Sort
    filtered.sort((a, b) => {
      let aValue = a[orderBy];
      let bValue = b[orderBy];

      // Handle null/undefined
      if (aValue == null) aValue = '';
      if (bValue == null) bValue = '';

      // String comparison
      if (typeof aValue === 'string') {
        return order === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      // Number/Date comparison
      return order === 'asc' ? aValue - bValue : bValue - aValue;
    });

    return filtered;
  }, [workOrders, searchTerm, orderBy, order]);

  // Paginate the filtered and sorted work orders
  const paginatedWorkOrders = useMemo(() => {
    const startIndex = page * rowsPerPage;
    return filteredAndSortedWorkOrders.slice(startIndex, startIndex + rowsPerPage);
  }, [filteredAndSortedWorkOrders, page, rowsPerPage]);

  const handleOpenApproval = (wo) => {
    setSelectedWO(wo);
    setApproverName('');
    setApprovalDialogOpen(true);
  };

  const handleApprove = async () => {
    if (!approverName.trim()) {
      toast.warning('Please enter approver name to continue.');
      return;
    }

    try {
      setApproving(true);
      await workOrderService.approveWorkOrder(selectedWO.id, approverName);
      setApprovalDialogOpen(false);
      setSelectedWO(null);
      setApproverName('');
      refetch();
      toast.success(`Work Order ${selectedWO.wo_number} has been approved successfully.`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Unable to approve work order. Please try again.');
    } finally {
      setApproving(false);
    }
  };

  // Calculate default completed date based on scheduled date
  const calculateDefaultCompletedDate = (scheduledDate) => {
    const today = new Date().toISOString().split('T')[0];

    if (scheduledDate) {
      const scheduled = new Date(scheduledDate);
      scheduled.setHours(0, 0, 0, 0);
      const todayDate = new Date();
      todayDate.setHours(0, 0, 0, 0);

      // If scheduled date is today or in the past, use it as default
      if (scheduled <= todayDate) {
        return scheduledDate;
      }
    }

    // Otherwise default to today
    return today;
  };

  const handleOpenCompleteDialog = async (wo) => {
    setSelectedWOForComplete(wo);
    const defaultDate = calculateDefaultCompletedDate(wo.scheduled_date);
    setCompletedDate(defaultDate);
    setCompleteDialogOpen(true);
  };

  const handleCloseCompleteDialog = () => {
    setCompleteDialogOpen(false);
    setSelectedWOForComplete(null);
    setCompletedDate('');
  };

  const handleCompleteWorkOrder = async () => {
    // Validate completed_date is not empty
    if (!completedDate) {
      toast.warning('Please select a completion date');
      return;
    }

    // Validate completed_date is not in the future
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const completed = new Date(completedDate);
    completed.setHours(0, 0, 0, 0);

    if (completed > today) {
      toast.warning('Completion date cannot be in the future');
      return;
    }

    // Validate completed_date is not before scheduled_date
    if (selectedWOForComplete.scheduled_date) {
      const scheduled = new Date(selectedWOForComplete.scheduled_date);
      scheduled.setHours(0, 0, 0, 0);

      if (completed < scheduled) {
        toast.warning('Completion date cannot be before scheduled date');
        return;
      }
    }

    try {
      setCompletingWorkOrder(true);
      await workOrderService.completeWorkOrder(selectedWOForComplete.id, completedDate);
      handleCloseCompleteDialog();
      refetch();
      toast.success(`Work Order ${selectedWOForComplete.wo_number} marked as completed!`);
    } catch (err) {
      toast.error('Failed to complete work order: ' + (err.response?.data?.detail || err.message));
    } finally {
      setCompletingWorkOrder(false);
    }
  };

  const handleCancel = async (woId, woNumber) => {
    setConfirmMessage(`Cancel work order ${woNumber}?`);
    setConfirmAction(() => async () => {
      try {
        await workOrderService.cancelWorkOrder(woId);
        refetch();
        toast.success(`Work Order ${woNumber} cancelled!`);
      } catch (err) {
        toast.error('Failed to cancel work order: ' + (err.response?.data?.detail || err.message));
      }
    });
    setConfirmDialogOpen(true);
  };

  // Calculate default scheduled date based on machine's next_pm_date
  const calculateDefaultScheduledDate = (machineNextPmDate, currentScheduledDate) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Reset time to start of day

    // If work order already has a scheduled date and it's in the future, use it
    if (currentScheduledDate) {
      const scheduled = new Date(currentScheduledDate);
      scheduled.setHours(0, 0, 0, 0);
      if (scheduled > today) {
        return currentScheduledDate;
      }
    }

    // Use machine's next_pm_date as default
    if (machineNextPmDate) {
      const nextPm = new Date(machineNextPmDate);
      nextPm.setHours(0, 0, 0, 0);

      // If next_pm_date is today or earlier (already due), use today + 2 days
      if (nextPm <= today) {
        const twoDaysLater = new Date(today);
        twoDaysLater.setDate(today.getDate() + 2);
        return twoDaysLater.toISOString().split('T')[0]; // Format: YYYY-MM-DD
      }

      // Otherwise, use next_pm_date
      return machineNextPmDate;
    }

    // Fallback: if no machine data, use today + 2
    const twoDaysLater = new Date(today);
    twoDaysLater.setDate(today.getDate() + 2);
    return twoDaysLater.toISOString().split('T')[0];
  };

  // Open schedule update dialog
  const handleOpenScheduleDialog = async (wo) => {
    setSelectedWOForSchedule(wo);
    setScheduleDialogOpen(true);
    setLoadingMachine(true);

    try {
      // Fetch machine details to get next_pm_date
      const machine = await machineService.getMachineById(wo.machine_id);
      setMachineData(machine);

      // Calculate and set default scheduled date
      const defaultDate = calculateDefaultScheduledDate(
        machine.next_pm_date,
        wo.scheduled_date
      );
      setScheduledDate(defaultDate);
    } catch (err) {
      console.error('Error fetching machine data:', err);
      toast.error('Failed to load machine data: ' + (err.response?.data?.detail || err.message));

      // Fallback: use current scheduled_date or today + 2
      if (wo.scheduled_date) {
        setScheduledDate(wo.scheduled_date);
      } else {
        const twoDaysLater = new Date();
        twoDaysLater.setDate(twoDaysLater.getDate() + 2);
        setScheduledDate(twoDaysLater.toISOString().split('T')[0]);
      }
    } finally {
      setLoadingMachine(false);
    }
  };

  // Update work order scheduled date
  const handleUpdateSchedule = async () => {
    if (!scheduledDate) {
      toast.warning('Please select a scheduled date');
      return;
    }

    // Validate that date is not in the past
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const selectedDate = new Date(scheduledDate);
    selectedDate.setHours(0, 0, 0, 0);

    if (selectedDate < today) {
      toast.warning('Scheduled date cannot be in the past. Please select today or a future date.');
      return;
    }

    try {
      setUpdatingSchedule(true);

      // Update work order with new scheduled_date
      await workOrderService.updateWorkOrder(selectedWOForSchedule.id, {
        scheduled_date: scheduledDate
      });

      // Close dialog and reset state
      setScheduleDialogOpen(false);
      setSelectedWOForSchedule(null);
      setScheduledDate('');
      setMachineData(null);

      // Refresh work orders list
      refetch();

      toast.success(`Scheduled date updated successfully for ${selectedWOForSchedule.wo_number}!`);
    } catch (err) {
      toast.error('Failed to update scheduled date: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUpdatingSchedule(false);
    }
  };

  // Close schedule dialog
  const handleCloseScheduleDialog = () => {
    if (updatingSchedule) return; // Prevent closing while updating

    setScheduleDialogOpen(false);
    setSelectedWOForSchedule(null);
    setScheduledDate('');
    setMachineData(null);
  };

  // Handle confirmation dialog
  const handleConfirm = async () => {
    if (confirmAction) {
      setConfirming(true);
      try {
        await confirmAction();
      } finally {
        setConfirming(false);
        setConfirmDialogOpen(false);
        setConfirmAction(null);
        setConfirmMessage('');
      }
    }
  };

  const handleCancelConfirm = () => {
    if (!confirming) {
      setConfirmDialogOpen(false);
      setConfirmAction(null);
      setConfirmMessage('');
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
        <Button variant="text" size="sm" onClick={refetch}>Retry</Button>
      </div>
    );
  }

  return (
    <div>
      {/* Page Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-800">Work Orders</h1>
        <Button variant="outlined" startIcon="refresh" onClick={refetch}>
          Refresh
        </Button>
      </div>

      {/* Filter and Search Controls */}
      <div className="flex flex-wrap gap-4 mb-6">
        <Select
          label="Filter by Status"
          value={statusFilter}
          onChange={handleFilterChange}
          options={[
            { value: 'all', label: 'All Work Orders' },
            { value: 'Draft', label: 'Draft' },
            { value: 'Pending_Approval', label: 'Pending Approval' },
            { value: 'Approved', label: 'Approved' },
            { value: 'Completed', label: 'Completed' },
            { value: 'Cancelled', label: 'Cancelled' },
          ]}
          className="min-w-[200px]"
        />

        <Input
          label="Search"
          placeholder="Search by WO number, machine name, status, priority..."
          value={searchTerm}
          onChange={handleSearchChange}
          startIcon="search"
          className="min-w-[350px]"
        />
      </div>

      {/* Work Orders Table */}
      {filteredAndSortedWorkOrders.length === 0 ? (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center gap-3">
          <span className="material-icons-round text-blue-600">info</span>
          <span className="text-blue-800">
            No work orders found matching the selected filter{searchTerm && ' and search criteria'}.
          </span>
        </div>
      ) : (
        <Card>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell header>
                  <TableSortLabel
                    active={orderBy === 'wo_number'}
                    direction={order}
                    onClick={() => handleSort('wo_number')}
                  >
                    WO Number
                  </TableSortLabel>
                </TableCell>
                <TableCell header>
                  <TableSortLabel
                    active={orderBy === 'machine_name'}
                    direction={order}
                    onClick={() => handleSort('machine_name')}
                  >
                    Machine
                  </TableSortLabel>
                </TableCell>
                <TableCell header>
                  <TableSortLabel
                    active={orderBy === 'status'}
                    direction={order}
                    onClick={() => handleSort('status')}
                  >
                    Status
                  </TableSortLabel>
                </TableCell>
                <TableCell header>
                  <TableSortLabel
                    active={orderBy === 'priority'}
                    direction={order}
                    onClick={() => handleSort('priority')}
                  >
                    Priority
                  </TableSortLabel>
                </TableCell>
                <TableCell header>
                  <TableSortLabel
                    active={orderBy === 'created_at'}
                    direction={order}
                    onClick={() => handleSort('created_at')}
                  >
                    Created
                  </TableSortLabel>
                </TableCell>
                <TableCell header>
                  <TableSortLabel
                    active={orderBy === 'scheduled_date'}
                    direction={order}
                    onClick={() => handleSort('scheduled_date')}
                  >
                    Scheduled
                  </TableSortLabel>
                </TableCell>
                <TableCell header align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedWorkOrders.map((wo) => (
                <TableRow key={wo.id} hover>
                  <TableCell>
                    <span className="font-bold text-gray-800">
                      {wo.wo_number}
                    </span>
                  </TableCell>

                  <TableCell>
                    <button
                      onClick={() => navigate(`/machines/${wo.machine_id}`)}
                      className="text-primary hover:underline font-medium"
                    >
                      {wo.machine_name || `Machine #${wo.machine_id}`}
                    </button>
                  </TableCell>

                  <TableCell>
                    <Badge variant={getWorkOrderStatusVariant(wo.status)} size="sm">
                      {getWorkOrderStatusLabel(wo.status)}
                    </Badge>
                  </TableCell>

                  <TableCell>
                    {wo.priority ? (
                      <Badge variant={getPriorityVariant(wo.priority)} size="sm">
                        {wo.priority}
                      </Badge>
                    ) : (
                      'N/A'
                    )}
                  </TableCell>

                  <TableCell>{formatDateTime(wo.created_at)}</TableCell>

                  <TableCell>
                    {wo.scheduled_date ? formatDateTime(wo.scheduled_date) : 'Not scheduled'}
                  </TableCell>

                  <TableCell align="center">
                    <div className="flex gap-1 justify-center">
                      {/* Approve Button */}
                      {(wo.status === 'Draft' || wo.status === 'Pending_Approval') && (
                        <button
                          onClick={() => handleOpenApproval(wo)}
                          className="p-2 rounded-full text-success hover:bg-success-light transition-colors"
                          title="Approve"
                        >
                          <span className="material-icons-round text-xl">check_circle</span>
                        </button>
                      )}

                      {/* Complete Button */}
                      {wo.status === 'Approved' && wo.scheduled_date && (
                        <button
                          onClick={() => handleOpenCompleteDialog(wo)}
                          className="p-2 rounded-full text-primary hover:bg-primary-50 transition-colors"
                          title="Complete"
                        >
                          <span className="material-icons-round text-xl">check_circle</span>
                        </button>
                      )}

                      {/* Update Schedule Button - Only for Approved status */}
                      {wo.status === 'Approved' && (
                        <button
                          onClick={() => handleOpenScheduleDialog(wo)}
                          className="p-2 rounded-full text-warning hover:bg-warning-light transition-colors"
                          title="Update Schedule"
                        >
                          <span className="material-icons-round text-xl">calendar_today</span>
                        </button>
                      )}

                      {/* Cancel Button */}
                      {wo.status !== 'Completed' && wo.status !== 'Cancelled' && (
                        <button
                          onClick={() => handleCancel(wo.id, wo.wo_number)}
                          className="p-2 rounded-full text-error hover:bg-error-light transition-colors"
                          title="Cancel"
                        >
                          <span className="material-icons-round text-xl">cancel</span>
                        </button>
                      )}

                      {/* View Details Button */}
                      <button
                        onClick={() => navigate(`/machines/${wo.machine_id}`)}
                        className="p-2 rounded-full text-blue-600 hover:bg-blue-50 transition-colors"
                        title="View Machine"
                      >
                        <span className="material-icons-round text-xl">visibility</span>
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            count={filteredAndSortedWorkOrders.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
            rowsPerPageOptions={[5, 10, 25, 50]}
          />
        </Card>
      )}

      {/* Approval Dialog */}
      <Dialog
        open={approvalDialogOpen}
        onClose={() => !approving && setApprovalDialogOpen(false)}
        title="Approve Work Order"
        maxWidth="sm"
      >
        <DialogContent>
          {selectedWO && (
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-600 mb-1">Work Order Number</p>
                <h3 className="text-xl font-semibold text-gray-800">{selectedWO.wo_number}</h3>
              </div>

              <div>
                <p className="text-sm text-gray-600 mb-1">Current Status</p>
                <Badge variant={getWorkOrderStatusVariant(selectedWO.status)}>
                  {getWorkOrderStatusLabel(selectedWO.status)}
                </Badge>
              </div>

              {selectedWO.notes && (
                <div>
                  <p className="text-sm text-gray-600 mb-1">Notes</p>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                    <p className="text-sm text-gray-700">{selectedWO.notes}</p>
                  </div>
                </div>
              )}

              <Input
                label="Approver Name"
                value={approverName}
                onChange={(e) => setApproverName(e.target.value)}
                placeholder="Enter your name"
                required
                disabled={approving}
              />
            </div>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            variant="outlined"
            onClick={() => setApprovalDialogOpen(false)}
            disabled={approving}
          >
            Cancel
          </Button>
          <Button
            variant="success"
            onClick={handleApprove}
            disabled={approving}
            startIcon={approving ? null : "check_circle"}
          >
            {approving ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                Approving...
              </div>
            ) : (
              'Approve'
            )}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Schedule Update Dialog */}
      <Dialog
        open={scheduleDialogOpen}
        onClose={handleCloseScheduleDialog}
        title="Update Scheduled Date"
        maxWidth="sm"
      >
        <DialogContent>
          {selectedWOForSchedule && (
            <div className="space-y-4">
              {/* Work Order Info */}
              <div>
                <p className="text-sm text-gray-600 mb-1">Work Order Number</p>
                <h3 className="text-xl font-semibold text-gray-800">{selectedWOForSchedule.wo_number}</h3>
              </div>

              {/* Machine Info */}
              <div>
                <p className="text-sm text-gray-600 mb-1">Machine</p>
                <p className="text-base font-medium text-gray-800">
                  Machine #{selectedWOForSchedule.machine_id}
                  {machineData && ` - ${machineData.name}`}
                </p>
              </div>

              {/* Current Status */}
              <div>
                <p className="text-sm text-gray-600 mb-1">Status</p>
                <Badge variant={getWorkOrderStatusVariant(selectedWOForSchedule.status)}>
                  {getWorkOrderStatusLabel(selectedWOForSchedule.status)}
                </Badge>
              </div>

              {/* Current Scheduled Date */}
              {selectedWOForSchedule.scheduled_date && (
                <div>
                  <p className="text-sm text-gray-600 mb-1">Current Scheduled Date</p>
                  <p className="text-base font-medium text-gray-800">
                    {formatDate(selectedWOForSchedule.scheduled_date)}
                  </p>
                </div>
              )}

              {/* Machine Next PM Date Info */}
              {machineData && machineData.next_pm_date && (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                  <p className="text-sm text-gray-600">
                    Machine Next PM Date: <strong className="text-gray-800">{formatDate(machineData.next_pm_date)}</strong>
                  </p>
                </div>
              )}

              {/* Date Picker */}
              <Input
                label="New Scheduled Date"
                type="date"
                value={scheduledDate}
                onChange={(e) => setScheduledDate(e.target.value)}
                disabled={loadingMachine || updatingSchedule}
                required
                helperText="Select today or a future date"
                inputProps={{
                  min: new Date().toISOString().split('T')[0],
                }}
              />

              {/* Loading state */}
              {loadingMachine && (
                <div className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-primary border-t-transparent"></div>
                  <p className="text-sm text-gray-600">Loading machine data...</p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            variant="outlined"
            onClick={handleCloseScheduleDialog}
            disabled={updatingSchedule}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleUpdateSchedule}
            disabled={loadingMachine || updatingSchedule || !scheduledDate}
            startIcon={updatingSchedule ? null : "calendar_today"}
          >
            {updatingSchedule ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                Updating...
              </div>
            ) : (
              'Update Schedule'
            )}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Complete Work Order Dialog */}
      <Dialog
        open={completeDialogOpen}
        onClose={handleCloseCompleteDialog}
        title="Complete Work Order"
        maxWidth="sm"
      >
        <DialogContent>
          {selectedWOForComplete && (
            <div className="flex flex-col gap-4">
              {/* Work Order Info */}
              <div>
                <p className="text-sm text-gray-600 mb-1">Work Order</p>
                <p className="text-lg font-bold text-gray-800">
                  {selectedWOForComplete.wo_number}
                </p>
              </div>

              <div>
                <p className="text-sm text-gray-600 mb-1">Machine</p>
                <p className="text-base font-medium text-gray-800">
                  {selectedWOForComplete.machine_name || `Machine #${selectedWOForComplete.machine_id}`}
                </p>
              </div>

              {/* Scheduled Date */}
              {selectedWOForComplete.scheduled_date && (
                <div>
                  <p className="text-sm text-gray-600 mb-1">Scheduled Date</p>
                  <p className="text-base font-medium text-gray-800">
                    {formatDate(selectedWOForComplete.scheduled_date)}
                  </p>
                </div>
              )}

              {/* Completion Date Picker */}
              <Input
                label="Completion Date"
                type="date"
                value={completedDate}
                onChange={(e) => setCompletedDate(e.target.value)}
                disabled={completingWorkOrder}
                required
                helperText="Select the date when work was completed"
                inputProps={{
                  min: selectedWOForComplete.scheduled_date || undefined,
                  max: new Date().toISOString().split('T')[0],
                }}
              />
            </div>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            variant="outlined"
            onClick={handleCloseCompleteDialog}
            disabled={completingWorkOrder}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleCompleteWorkOrder}
            disabled={completingWorkOrder || !completedDate}
            startIcon={completingWorkOrder ? null : "check_circle"}
          >
            {completingWorkOrder ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                Completing...
              </div>
            ) : (
              'Complete Work Order'
            )}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialogOpen}
        onClose={handleCancelConfirm}
        title="Confirm Action"
        maxWidth="sm"
      >
        <DialogContent>
          <p className="text-base text-gray-700">{confirmMessage}</p>
        </DialogContent>
        <DialogActions>
          <Button
            variant="outlined"
            onClick={handleCancelConfirm}
            disabled={confirming}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleConfirm}
            disabled={confirming}
            startIcon={confirming ? null : "check_circle"}
          >
            {confirming ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                Processing...
              </div>
            ) : (
              'Confirm'
            )}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default WorkOrderView;
