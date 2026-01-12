import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Table, TableHead, TableBody, TableRow, TableCell, TableSortLabel, TablePagination } from '../components/ui/Table';

import useMachines from '../hooks/useMachines';
import { formatDate, formatDaysUntilPM } from '../utils/dateUtils';
import { getPMStatusLabel, getPMStatusVariant } from '../utils/statusUtils';

const MachineDashboard = () => {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [orderBy, setOrderBy] = useState('days_until_pm');
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
        <h1 className="text-3xl font-bold text-gray-800">Machine Dashboard</h1>
        <Button variant="outlined" startIcon="refresh" onClick={refetch}>
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card className="bg-error-light border-error">
          <CardContent className="text-center">
            <div className="text-4xl font-bold text-error">{summary.overdue}</div>
            <div className="text-sm text-gray-700 mt-1 font-medium">Overdue</div>
          </CardContent>
        </Card>

        <Card className="bg-warning-light border-warning">
          <CardContent className="text-center">
            <div className="text-4xl font-bold text-warning">{summary.due_soon}</div>
            <div className="text-sm text-gray-700 mt-1 font-medium">Due Soon (≤30 days)</div>
          </CardContent>
        </Card>

        <Card className="bg-success-light border-success">
          <CardContent className="text-center">
            <div className="text-4xl font-bold text-success">{summary.ok}</div>
            <div className="text-sm text-gray-700 mt-1 font-medium">OK</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="text-center">
            <div className="text-4xl font-bold text-primary">{summary.total}</div>
            <div className="text-sm text-gray-700 mt-1 font-medium">Total Machines</div>
          </CardContent>
        </Card>
      </div>

      {/* Filter and Search Controls */}
      <div className="flex flex-wrap gap-4 mb-6">
        <Select
          label="Filter by Status"
          value={statusFilter}
          onChange={handleFilterChange}
          options={[
            { value: 'all', label: 'All Machines' },
            { value: 'overdue', label: 'Overdue' },
            { value: 'due_soon', label: 'Due Soon' },
            { value: 'ok', label: 'OK' },
          ]}
          className="min-w-[200px]"
        />

        <Input
          label="Search"
          placeholder="Search by ID, name, location, or supplier..."
          value={searchTerm}
          onChange={handleSearchChange}
          startIcon="search"
          className="min-w-[300px]"
        />
      </div>

      {/* Machine Table */}
      {filteredAndSortedMachines.length === 0 ? (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center gap-3">
          <span className="material-icons-round text-blue-600">info</span>
          <span className="text-blue-800">
            No machines found matching the selected filter{searchTerm && ' and search criteria'}.
          </span>
        </div>
      ) : (
        <Card>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell header>
                  <TableSortLabel
                    active={orderBy === 'machine_id'}
                    direction={order}
                    onClick={() => handleSort('machine_id')}
                  >
                    Machine ID
                  </TableSortLabel>
                </TableCell>
                <TableCell header>
                  <TableSortLabel
                    active={orderBy === 'name'}
                    direction={order}
                    onClick={() => handleSort('name')}
                  >
                    Name
                  </TableSortLabel>
                </TableCell>
                <TableCell header>
                  <TableSortLabel
                    active={orderBy === 'location'}
                    direction={order}
                    onClick={() => handleSort('location')}
                  >
                    Location
                  </TableSortLabel>
                </TableCell>
                <TableCell header>
                  <TableSortLabel
                    active={orderBy === 'pm_frequency'}
                    direction={order}
                    onClick={() => handleSort('pm_frequency')}
                  >
                    PM Frequency
                  </TableSortLabel>
                </TableCell>
                <TableCell header>
                  <TableSortLabel
                    active={orderBy === 'next_pm_date'}
                    direction={order}
                    onClick={() => handleSort('next_pm_date')}
                  >
                    Next PM Date
                  </TableSortLabel>
                </TableCell>
                <TableCell header align="right">
                  <TableSortLabel
                    active={orderBy === 'days_until_pm'}
                    direction={order}
                    onClick={() => handleSort('days_until_pm')}
                  >
                    Days Until PM
                  </TableSortLabel>
                </TableCell>
                <TableCell header>PM Status</TableCell>
                <TableCell header>Supplier</TableCell>
                <TableCell header align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedMachines.map((machine) => (
                <TableRow
                  key={machine.id}
                  hover
                  onClick={() => navigate(`/machines/${machine.id}`)}
                >
                  <TableCell>
                    <span className="font-medium text-gray-800">
                      {machine.machine_id}
                    </span>
                  </TableCell>
                  <TableCell>{machine.name}</TableCell>
                  <TableCell>{machine.location}</TableCell>
                  <TableCell>{machine.pm_frequency}</TableCell>
                  <TableCell>{formatDate(machine.next_pm_date)}</TableCell>
                  <TableCell align="right">
                    <span className={`font-${machine.days_until_pm < 0 ? 'bold' : 'normal'} ${machine.days_until_pm < 0 ? 'text-error' : 'text-gray-800'}`}>
                      {formatDaysUntilPM(machine.days_until_pm)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge variant={getPMStatusVariant(machine.pm_status)} size="sm">
                      {getPMStatusLabel(machine.pm_status)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-gray-600 truncate">
                      {machine.assigned_supplier || '-'}
                    </span>
                  </TableCell>
                  <TableCell align="center" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => navigate(`/machines/${machine.id}`)}
                      className="p-2 rounded-full text-primary hover:bg-primary-50 transition-colors"
                      title="View Details"
                    >
                      <span className="material-icons-round text-xl">visibility</span>
                    </button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            count={filteredAndSortedMachines.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
            rowsPerPageOptions={[5, 10, 25, 50]}
          />
        </Card>
      )}
    </div>
  );
};

export default MachineDashboard;
