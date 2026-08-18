import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Card,
  CardContent,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  ArrowBack,
  Build,
  SmartToy,
  History,
  Assignment,
} from '@mui/icons-material';

import machineService from '../services/machineService';
import aiService from '../services/aiService';
import { formatDate, formatDateTime, formatDaysUntilPM } from '../utils/dateUtils';
import {
  getPMStatusColor,
  getPMStatusLabel,
  getWorkOrderStatusColor,
  getWorkOrderStatusLabel,
  getDecisionColor,
  getDecisionLabel,
  getConfidenceColor,
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
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" action={
        <Button color="inherit" size="small" onClick={fetchMachineDetails}>
          Retry
        </Button>
      }>
        {error}
      </Alert>
    );
  }

  if (!machine) {
    return <Alert severity="info">Machine not found</Alert>;
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center">
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/machines')}
            sx={{ mr: 2 }}
          >
            Back
          </Button>
          <Typography variant="h4" component="h1">
            {machine.machine_id}
          </Typography>
          <Chip
            label={getPMStatusLabel(machine.pm_status)}
            color={getPMStatusColor(machine.pm_status)}
            sx={{ ml: 2 }}
          />
        </Box>
        <Button
          variant="contained"
          startIcon={<SmartToy />}
          onClick={handleGetAIDecision}
          disabled={aiLoading}
        >
          {aiLoading ? 'Getting AI Decision...' : 'Get AI Decision'}
        </Button>
      </Box>

      <Grid container spacing={3}>
        {/* Machine Information */}
        <Grid item xs={12} md={6}>
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom display="flex" alignItems="center">
              <Build sx={{ mr: 1 }} />
              Machine Information
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Machine ID
                </Typography>
                <Typography variant="body1" fontWeight="bold">
                  {machine.machine_id}
                </Typography>
              </Grid>

              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Name
                </Typography>
                <Typography variant="body1" fontWeight="bold">
                  {machine.name}
                </Typography>
              </Grid>

              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Location
                </Typography>
                <Typography variant="body1" fontWeight="bold">
                  {machine.location}
                </Typography>
              </Grid>

              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Status
                </Typography>
                <Typography variant="body1" fontWeight="bold">
                  {machine.status}
                </Typography>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary">
                  Description
                </Typography>
                <Typography variant="body1">
                  {machine.description || 'N/A'}
                </Typography>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* PM Schedule Information */}
        <Grid item xs={12} md={6}>
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              PM Schedule
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  PM Frequency
                </Typography>
                <Typography variant="body1" fontWeight="bold">
                  {machine.pm_frequency}
                </Typography>
              </Grid>

              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  PM Status
                </Typography>
                <Chip
                  label={getPMStatusLabel(machine.pm_status)}
                  color={getPMStatusColor(machine.pm_status)}
                  size="small"
                />
              </Grid>

              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Last PM Date
                </Typography>
                <Typography variant="body1" fontWeight="bold">
                  {formatDate(machine.last_pm_date)}
                </Typography>
              </Grid>

              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Next PM Date
                </Typography>
                <Typography variant="body1" fontWeight="bold">
                  {formatDate(machine.next_pm_date)}
                </Typography>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary">
                  Days Until PM
                </Typography>
                <Typography
                  variant="h5"
                  fontWeight="bold"
                  color={machine.days_until_pm < 0 ? 'error' : 'primary'}
                >
                  {formatDaysUntilPM(machine.days_until_pm)}
                </Typography>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Supplier Information */}
        <Grid item xs={12} md={6}>
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Supplier Information
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary">
                  Assigned Supplier
                </Typography>
                <Typography variant="body1" fontWeight="bold">
                  {machine.assigned_supplier || 'N/A'}
                </Typography>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary">
                  Supplier Email
                </Typography>
                <Typography variant="body1" fontWeight="bold">
                  {machine.supplier_email || 'N/A'}
                </Typography>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Active Work Orders */}
        <Grid item xs={12} md={6}>
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom display="flex" alignItems="center">
              <Assignment sx={{ mr: 1 }} />
              Active Work Orders ({machine.work_orders?.length || 0})
            </Typography>
            <Divider sx={{ mb: 2 }} />

            {machine.work_orders && machine.work_orders.length > 0 ? (
              machine.work_orders.map((wo) => (
                <Card key={wo.id} variant="outlined" sx={{ mb: 1 }}>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography variant="subtitle2" fontWeight="bold">
                        {wo.wo_number}
                      </Typography>
                      <Chip
                        label={getWorkOrderStatusLabel(wo.status)}
                        color={getWorkOrderStatusColor(wo.status)}
                        size="small"
                      />
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      Created: {formatDateTime(wo.created_at)}
                    </Typography>
                    {wo.priority && (
                      <Typography variant="caption" display="block">
                        Priority: <strong>{wo.priority}</strong>
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              ))
            ) : (
              <Typography variant="body2" color="text.secondary">
                No active work orders
              </Typography>
            )}

            <Button
              variant="outlined"
              size="small"
              fullWidth
              sx={{ mt: 2 }}
              onClick={() => navigate('/work-orders')}
            >
              View All Work Orders
            </Button>
          </Paper>
        </Grid>

        {/* Maintenance History */}
        <Grid item xs={12}>
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom display="flex" alignItems="center">
              <History sx={{ mr: 1 }} />
              Maintenance History
            </Typography>
            <Divider sx={{ mb: 2 }} />

            {machine.maintenance_history && machine.maintenance_history.length > 0 ? (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Performed By</TableCell>
                      <TableCell>Notes</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {machine.maintenance_history.map((history) => (
                      <TableRow key={history.id}>
                        <TableCell>{formatDate(history.maintenance_date)}</TableCell>
                        <TableCell>
                          <Chip label={history.maintenance_type || 'N/A'} size="small" />
                        </TableCell>
                        <TableCell>{history.performed_by || 'N/A'}</TableCell>
                        <TableCell>{history.notes || 'N/A'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No maintenance history available
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* AI Decision Dialog */}
      <Dialog
        open={aiDialogOpen}
        onClose={() => setAiDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>AI Decision Result</DialogTitle>
        <DialogContent>
          {aiDecision && (
            <Box>
              <Box mb={2}>
                <Typography variant="body2" color="text.secondary">
                  Decision
                </Typography>
                <Chip
                  label={getDecisionLabel(aiDecision.decision)}
                  color={getDecisionColor(aiDecision.decision)}
                  sx={{ mt: 1 }}
                />
              </Box>

              <Box mb={2}>
                <Typography variant="body2" color="text.secondary">
                  Priority
                </Typography>
                <Typography variant="body1" fontWeight="bold">
                  {aiDecision.priority}
                </Typography>
              </Box>

              <Box mb={2}>
                <Typography variant="body2" color="text.secondary">
                  Confidence
                </Typography>
                <Chip
                  label={`${(aiDecision.confidence * 100).toFixed(0)}%`}
                  color={getConfidenceColor(aiDecision.confidence)}
                  sx={{ mt: 1 }}
                />
              </Box>

              <Box>
                <Typography variant="body2" color="text.secondary">
                  Explanation
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, mt: 1, backgroundColor: 'grey.50' }}>
                  <Typography variant="body2">
                    {aiDecision.explanation}
                  </Typography>
                </Paper>
              </Box>

              <Box mt={2}>
                <Typography variant="caption" color="text.secondary">
                  Provider: {aiDecision.llm_provider} | Model: {aiDecision.llm_model}
                </Typography>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAiDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MachineDetail;
