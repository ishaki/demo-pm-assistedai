import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Grid,
  Typography,
  Chip,
  Button,
  Box,
  CircularProgress,
  Alert,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TablePagination,
  IconButton,
  Tooltip,
} from '@mui/material';
import { Visibility, Refresh, Search } from '@mui/icons-material';

import useMachines from '../hooks/useMachines';
import { formatDate, formatDaysUntilPM } from '../utils/dateUtils';
import { getPMStatusColor, getPMStatusLabel } from '../utils/statusUtils';

const MachineDashboard = () => {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [orderBy, setOrderBy] = useState('machine_id');
  const [order, setOrder] = useState('asc');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const filters = statusFilter === 'all' ? {} : { pm_status: statusFilter };
  const { machines, loading, error, refetch } = useMachines(filters);

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

  // Calculate summary statistics
  const summary = machines.reduce(
    (acc, machine) => {
      acc[machine.pm_status] = (acc[machine.pm_status] || 0) + 1;
      acc.total++;
      return acc;
    },
    { overdue: 0, due_soon: 0, ok: 0, total: 0 }
  );

  // Sorting handler
  const handleSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  // Filter and sort machines
  const filteredAndSortedMachines = useMemo(() => {
    let filtered = machines.filter((machine) => {
      if (!searchTerm) return true;
      const searchLower = searchTerm.toLowerCase();
      return (
        machine.machine_id?.toLowerCase().includes(searchLower) ||
        machine.name?.toLowerCase().includes(searchLower) ||
        machine.location?.toLowerCase().includes(searchLower) ||
        machine.assigned_supplier?.toLowerCase().includes(searchLower)
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

      // Number comparison
      return order === 'asc' ? aValue - bValue : bValue - aValue;
    });

    return filtered;
  }, [machines, searchTerm, orderBy, order]);

  // Paginate the filtered and sorted machines
  const paginatedMachines = useMemo(() => {
    const startIndex = page * rowsPerPage;
    return filteredAndSortedMachines.slice(startIndex, startIndex + rowsPerPage);
  }, [filteredAndSortedMachines, page, rowsPerPage]);

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
          Machine Dashboard
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={refetch}
        >
          Refresh
        </Button>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={2} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper
            elevation={2}
            sx={{
              p: 2,
              backgroundColor: 'error.light',
              color: 'error.contrastText',
            }}
          >
            <Typography variant="h3" align="center">
              {summary.overdue}
            </Typography>
            <Typography variant="subtitle1" align="center">
              Overdue
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Paper
            elevation={2}
            sx={{
              p: 2,
              backgroundColor: 'warning.light',
              color: 'warning.contrastText',
            }}
          >
            <Typography variant="h3" align="center">
              {summary.due_soon}
            </Typography>
            <Typography variant="subtitle1" align="center">
              Due Soon (≤30 days)
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Paper
            elevation={2}
            sx={{
              p: 2,
              backgroundColor: 'success.light',
              color: 'success.contrastText',
            }}
          >
            <Typography variant="h3" align="center">
              {summary.ok}
            </Typography>
            <Typography variant="subtitle1" align="center">
              OK
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Paper elevation={2} sx={{ p: 2 }}>
            <Typography variant="h3" align="center" color="primary">
              {summary.total}
            </Typography>
            <Typography variant="subtitle1" align="center">
              Total Machines
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Filter and Search Controls */}
      <Box mb={3} display="flex" gap={2} flexWrap="wrap">
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Filter by Status</InputLabel>
          <Select
            value={statusFilter}
            label="Filter by Status"
            onChange={handleFilterChange}
          >
            <MenuItem value="all">All Machines</MenuItem>
            <MenuItem value="overdue">Overdue</MenuItem>
            <MenuItem value="due_soon">Due Soon</MenuItem>
            <MenuItem value="ok">OK</MenuItem>
          </Select>
        </FormControl>

        <TextField
          label="Search"
          placeholder="Search by ID, name, location, or supplier..."
          value={searchTerm}
          onChange={handleSearchChange}
          sx={{ minWidth: 300 }}
          InputProps={{
            startAdornment: <Search sx={{ mr: 1, color: 'action.active' }} />,
          }}
        />
      </Box>

      {/* Machine Table */}
      {filteredAndSortedMachines.length === 0 ? (
        <Alert severity="info">
          No machines found matching the selected filter{searchTerm && ' and search criteria'}.
        </Alert>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'machine_id'}
                    direction={orderBy === 'machine_id' ? order : 'asc'}
                    onClick={() => handleSort('machine_id')}
                  >
                    Machine ID
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'name'}
                    direction={orderBy === 'name' ? order : 'asc'}
                    onClick={() => handleSort('name')}
                  >
                    Name
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'location'}
                    direction={orderBy === 'location' ? order : 'asc'}
                    onClick={() => handleSort('location')}
                  >
                    Location
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'pm_frequency'}
                    direction={orderBy === 'pm_frequency' ? order : 'asc'}
                    onClick={() => handleSort('pm_frequency')}
                  >
                    PM Frequency
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'next_pm_date'}
                    direction={orderBy === 'next_pm_date' ? order : 'asc'}
                    onClick={() => handleSort('next_pm_date')}
                  >
                    Next PM Date
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={orderBy === 'days_until_pm'}
                    direction={orderBy === 'days_until_pm' ? order : 'asc'}
                    onClick={() => handleSort('days_until_pm')}
                  >
                    Days Until PM
                  </TableSortLabel>
                </TableCell>
                <TableCell>PM Status</TableCell>
                <TableCell>Supplier</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedMachines.map((machine) => (
                <TableRow
                  key={machine.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/machines/${machine.id}`)}
                >
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {machine.machine_id}
                    </Typography>
                  </TableCell>
                  <TableCell>{machine.name}</TableCell>
                  <TableCell>{machine.location}</TableCell>
                  <TableCell>{machine.pm_frequency}</TableCell>
                  <TableCell>{formatDate(machine.next_pm_date)}</TableCell>
                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      color={machine.days_until_pm < 0 ? 'error' : 'text.primary'}
                      fontWeight={machine.days_until_pm < 0 ? 'bold' : 'normal'}
                    >
                      {formatDaysUntilPM(machine.days_until_pm)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={getPMStatusLabel(machine.pm_status)}
                      color={getPMStatusColor(machine.pm_status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" noWrap>
                      {machine.assigned_supplier || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell align="center" onClick={(e) => e.stopPropagation()}>
                    <Tooltip title="View Details">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => navigate(`/machines/${machine.id}`)}
                      >
                        <Visibility />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            rowsPerPageOptions={[5, 10, 25, 50]}
            component="div"
            count={filteredAndSortedMachines.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
          />
        </TableContainer>
      )}
    </Box>
  );
};

export default MachineDashboard;
