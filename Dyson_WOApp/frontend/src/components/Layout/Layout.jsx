import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Tabs,
  Tab,
} from '@mui/material';
import { Build, Assignment } from '@mui/icons-material';

const Layout = ({ children }) => {
  const location = useLocation();

  const getTabValue = () => {
    if (location.pathname.startsWith('/machines')) return 0;
    if (location.pathname.startsWith('/work-orders')) return 1;
    return false;
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* App Bar */}
      <AppBar position="static" elevation={2}>
        <Toolbar>
          <Build sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ mr: 4 }}>
            AI-Assisted Preventive Maintenance
          </Typography>

          {/* Navigation Tabs - Inline with Header */}
          <Tabs
            value={getTabValue()}
            indicatorColor="secondary"
            textColor="inherit"
            sx={{ flexGrow: 1 }}
          >
            <Tab
              label="Machines"
              component={Link}
              to="/machines"
              icon={<Build />}
              iconPosition="start"
            />
            <Tab
              label="Work Orders"
              component={Link}
              to="/work-orders"
              icon={<Assignment />}
              iconPosition="start"
            />
          </Tabs>

          <Typography variant="body2" color="inherit" sx={{ opacity: 0.8 }}>
            Innoark - AI-Assisted POC
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
        {children}
      </Container>

      {/* Footer */}
      <Box
        component="footer"
        sx={{
          py: 2,
          px: 2,
          mt: 'auto',
          backgroundColor: (theme) =>
            theme.palette.mode === 'light'
              ? theme.palette.grey[200]
              : theme.palette.grey[800],
        }}
      >
        <Container maxWidth="xl">
          <Typography variant="body2" color="text.secondary" align="center">
            AI-Assisted Preventive Maintenance POC © {new Date().getFullYear()}
          </Typography>
        </Container>
      </Box>
    </Box>
  );
};

export default Layout;
