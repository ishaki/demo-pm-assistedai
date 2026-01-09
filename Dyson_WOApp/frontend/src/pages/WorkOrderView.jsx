import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TablePagination,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tooltip,
} from '@mui/material';
import {
  Refresh,
  CheckCircle,
  Cancel,
  Visibility,
  SmartToy,
  Search,
  Event,
  CalendarToday,
} from '@mui/icons-material';

import useWorkOrders from '../hooks/useWorkOrders';
import workOrderService from '../services/workOrderService';
import machineService from '../services/machineService';
import { formatDateTime, formatDate } from '../utils/dateUtils';
import {
  getWorkOrderStatusColor,
  getWorkOrderStatusLabel,
  getPriorityColor,
} from '../utils/statusUtils';

const WorkOrderView = () => {
  const navigate = useNavigate();
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
      alert('Please enter approver name');
      return;
    }

    try {
      setApproving(true);
      await workOrderService.approveWorkOrder(selectedWO.id, approverName);
      setApprovalDialogOpen(false);
      setSelectedWO(null);
      setApproverName('');
      refetch();
      alert(`Work Order ${selectedWO.wo_number} approved successfully!`);
    } catch (err) {
      alert('Failed to approve work order: ' + (err.response?.data?.detail || err.message));
    } finally {
      setApproving(false);
    }
  };

  const handleComplete = async (woId, woNumber) => {
    if (!window.confirm(`Complete work order ${woNumber}?`)) return;

    try {
      await workOrderService.completeWorkOrder(woId);
      refetch();
      alert(`Work Order ${woNumber} marked as completed!`);
    } catch (err) {
      alert('Failed to complete work order: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleCancel = async (woId, woNumber) => {
    if (!window.confirm(`Cancel work order ${woNumber}?`)) return;

    try {
      await workOrderService.cancelWorkOrder(woId);
      refetch();
      alert(`Work Order ${woNumber} cancelled!`);
    } catch (err) {
      alert('Failed to cancel work order: ' + (err.response?.data?.detail || err.message));
    }
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
      alert('Failed to load machine data: ' + (err.response?.data?.detail || err.message));

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
      alert('Please select a scheduled date');
      return;
    }

    // Validate that date is not in the past
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const selectedDate = new Date(scheduledDate);
    selectedDate.setHours(0, 0, 0, 0);

    if (selectedDate < today) {
      alert('Scheduled date cannot be in the past. Please select today or a future date.');
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

      alert(`Scheduled date updated successfully for ${selectedWOForSchedule.wo_number}!`);
    } catch (err) {
      alert('Failed to update scheduled date: ' + (err.response?.data?.detail || err.message));
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

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" action={
        <Button color="inherit" size="small" onClick={refetch}>
          Retry
        </Button>
      }>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      {/* Page Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Work Orders
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={refetch}
        >
          Refresh
        </Button>
      </Box>

      {/* Filter and Search Controls */}
      <Box mb={3} display="flex" gap={2} flexWrap="wrap">
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Filter by Status</InputLabel>
          <Select
            value={statusFilter}
            label="Filter by Status"
            onChange={handleFilterChange}
          >
            <MenuItem value="all">All Work Orders</MenuItem>
            <MenuItem value="Draft">Draft</MenuItem>
            <MenuItem value="Pending_Approval">Pending Approval</MenuItem>
            <MenuItem value="Approved">Approved</MenuItem>
            <MenuItem value="Completed">Completed</MenuItem>
            <MenuItem value="Cancelled">Cancelled</MenuItem>
          </Select>
        </FormControl>

        <TextField
          label="Search"
          placeholder="Search by WO number, machine name, status, priority..."
          value={searchTerm}
          onChange={handleSearchChange}
          sx={{ minWidth: 350 }}
          InputProps={{
            startAdornment: <Search sx={{ mr: 1, color: 'action.active' }} />,
          }}
        />
      </Box>

      {/* Work Orders Table */}
      {filteredAndSortedWorkOrders.length === 0 ? (
        <Alert severity="info">
          No work orders found matching the selected filter{searchTerm && ' and search criteria'}.
        </Alert>
      ) : (
        <TableContainer component={Paper} elevation={3}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'wo_number'}
                    direction={orderBy === 'wo_number' ? order : 'asc'}
                    onClick={() => handleSort('wo_number')}
                  >
                    WO Number
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'machine_name'}
                    direction={orderBy === 'machine_name' ? order : 'asc'}
                    onClick={() => handleSort('machine_name')}
                  >
                    Machine
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'status'}
                    direction={orderBy === 'status' ? order : 'asc'}
                    onClick={() => handleSort('status')}
                  >
                    Status
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'priority'}
                    direction={orderBy === 'priority' ? order : 'asc'}
                    onClick={() => handleSort('priority')}
                  >
                    Priority
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'creation_source'}
                    direction={orderBy === 'creation_source' ? order : 'asc'}
                    onClick={() => handleSort('creation_source')}
                  >
                    Source
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'created_at'}
                    direction={orderBy === 'created_at' ? order : 'asc'}
                    onClick={() => handleSort('created_at')}
                  >
                    Created
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'scheduled_date'}
                    direction={orderBy === 'scheduled_date' ? order : 'asc'}
                    onClick={() => handleSort('scheduled_date')}
                  >
                    Scheduled
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedWorkOrders.map((wo) => (
                <TableRow key={wo.id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {wo.wo_number}
                    </Typography>
                  </TableCell>

                  <TableCell>
                    <Button
                      size="small"
                      onClick={() => navigate(`/machines/${wo.machine_id}`)}
                    >
                      {wo.machine_name || `Machine #${wo.machine_id}`}
                    </Button>
                  </TableCell>

                  <TableCell>
                    <Chip
                      label={getWorkOrderStatusLabel(wo.status)}
                      color={getWorkOrderStatusColor(wo.status)}
                      size="small"
                    />
                  </TableCell>

                  <TableCell>
                    {wo.priority ? (
                      <Chip
                        label={wo.priority}
                        color={getPriorityColor(wo.priority)}
                        size="small"
                      />
                    ) : (
                      'N/A'
                    )}
                  </TableCell>

                  <TableCell>
                    <Chip
                      icon={wo.creation_source === 'AI' ? <SmartToy /> : undefined}
                      label={wo.creation_source}
                      size="small"
                      variant={wo.creation_source === 'AI' ? 'filled' : 'outlined'}
                      color={wo.creation_source === 'AI' ? 'secondary' : 'default'}
                    />
                  </TableCell>

                  <TableCell>{formatDateTime(wo.created_at)}</TableCell>

                  <TableCell>
                    {wo.scheduled_date ? formatDateTime(wo.scheduled_date) : 'Not scheduled'}
                  </TableCell>

                  <TableCell align="center">
                    <Box display="flex" gap={1} justifyContent="center">
                      {/* Approve Button */}
                      {(wo.status === 'Draft' || wo.status === 'Pending_Approval') && (
                        <Tooltip title="Approve">
                          <IconButton
                            color="success"
                            size="small"
                            onClick={() => handleOpenApproval(wo)}
                          >
                            <CheckCircle />
                          </IconButton>
                        </Tooltip>
                      )}

                      {/* Complete Button */}
                      {wo.status === 'Approved' && (
                        <Tooltip title="Complete">
                          <IconButton
                            color="primary"
                            size="small"
                            onClick={() => handleComplete(wo.id, wo.wo_number)}
                          >
                            <CheckCircle />
                          </IconButton>
                        </Tooltip>
                      )}

                      {/* Update Schedule Button - Only for Approved status */}
                      {wo.status === 'Approved' && (
                        <Tooltip title="Update Schedule">
                          <IconButton
                            color="warning"
                            size="small"
                            onClick={() => handleOpenScheduleDialog(wo)}
                          >
                            <CalendarToday />
                          </IconButton>
                        </Tooltip>
                      )}

                      {/* Cancel Button */}
                      {wo.status !== 'Completed' && wo.status !== 'Cancelled' && (
                        <Tooltip title="Cancel">
                          <IconButton
                            color="error"
                            size="small"
                            onClick={() => handleCancel(wo.id, wo.wo_number)}
                          >
                            <Cancel />
                          </IconButton>
                        </Tooltip>
                      )}

                      {/* View Details Button */}
                      <Tooltip title="View Machine">
                        <IconButton
                          color="info"
                          size="small"
                          onClick={() => navigate(`/machines/${wo.machine_id}`)}
                        >
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            rowsPerPageOptions={[5, 10, 25, 50]}
            component="div"
            count={filteredAndSortedWorkOrders.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
          />
        </TableContainer>
      )}

      {/* Approval Dialog */}
      <Dialog
        open={approvalDialogOpen}
        onClose={() => !approving && setApprovalDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Approve Work Order</DialogTitle>
        <DialogContent>
          {selectedWO && (
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Work Order Number
              </Typography>
              <Typography variant="h6" gutterBottom>
                {selectedWO.wo_number}
              </Typography>

              <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                Current Status
              </Typography>
              <Chip
                label={getWorkOrderStatusLabel(selectedWO.status)}
                color={getWorkOrderStatusColor(selectedWO.status)}
                sx={{ mb: 2 }}
              />

              {selectedWO.notes && (
                <>
                  <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                    Notes
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, mb: 2, backgroundColor: 'grey.50' }}>
                    <Typography variant="body2">
                      {selectedWO.notes}
                    </Typography>
                  </Paper>
                </>
              )}

              <TextField
                label="Approver Name"
                fullWidth
                value={approverName}
                onChange={(e) => setApproverName(e.target.value)}
                placeholder="Enter your name"
                required
                disabled={approving}
                sx={{ mt: 2 }}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApprovalDialogOpen(false)} disabled={approving}>
            Cancel
          </Button>
          <Button
            onClick={handleApprove}
            variant="contained"
            color="success"
            disabled={approving}
            startIcon={approving ? <CircularProgress size={20} /> : <CheckCircle />}
          >
            {approving ? 'Approving...' : 'Approve'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Schedule Update Dialog */}
      <Dialog
        open={scheduleDialogOpen}
        onClose={handleCloseScheduleDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Update Scheduled Date</DialogTitle>
        <DialogContent>
          {selectedWOForSchedule && (
            <Box>
              {/* Work Order Info */}
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Work Order Number
              </Typography>
              <Typography variant="h6" gutterBottom>
                {selectedWOForSchedule.wo_number}
              </Typography>

              {/* Machine Info */}
              <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                Machine
              </Typography>
              <Typography variant="body1" gutterBottom>
                Machine #{selectedWOForSchedule.machine_id}
                {machineData && ` - ${machineData.name}`}
              </Typography>

              {/* Current Status */}
              <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                Status
              </Typography>
              <Chip
                label={getWorkOrderStatusLabel(selectedWOForSchedule.status)}
                color={getWorkOrderStatusColor(selectedWOForSchedule.status)}
                sx={{ mb: 2 }}
              />

              {/* Current Scheduled Date */}
              {selectedWOForSchedule.scheduled_date && (
                <>
                  <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                    Current Scheduled Date
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    {formatDate(selectedWOForSchedule.scheduled_date)}
                  </Typography>
                </>
              )}

              {/* Machine Next PM Date Info */}
              {machineData && machineData.next_pm_date && (
                <Paper variant="outlined" sx={{ p: 2, mt: 2, mb: 2, backgroundColor: 'grey.50' }}>
                  <Typography variant="body2" color="text.secondary">
                    Machine Next PM Date: <strong>{formatDate(machineData.next_pm_date)}</strong>
                  </Typography>
                </Paper>
              )}

              {/* Date Picker */}
              <TextField
                label="New Scheduled Date"
                type="date"
                fullWidth
                value={scheduledDate}
                onChange={(e) => setScheduledDate(e.target.value)}
                disabled={loadingMachine || updatingSchedule}
                required
                sx={{ mt: 2 }}
                InputLabelProps={{
                  shrink: true,
                }}
                inputProps={{
                  min: new Date().toISOString().split('T')[0], // Prevent selecting past dates
                }}
                helperText="Select today or a future date"
              />

              {/* Loading state */}
              {loadingMachine && (
                <Box display="flex" alignItems="center" gap={1} mt={2}>
                  <CircularProgress size={20} />
                  <Typography variant="body2" color="text.secondary">
                    Loading machine data...
                  </Typography>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseScheduleDialog} disabled={updatingSchedule}>
            Cancel
          </Button>
          <Button
            onClick={handleUpdateSchedule}
            variant="contained"
            color="primary"
            disabled={loadingMachine || updatingSchedule || !scheduledDate}
            startIcon={updatingSchedule ? <CircularProgress size={20} /> : <CalendarToday />}
          >
            {updatingSchedule ? 'Updating...' : 'Update Schedule'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default WorkOrderView;
