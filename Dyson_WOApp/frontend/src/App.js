import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Pages
import MachineDashboard from './pages/MachineDashboard';
import MachineDetail from './pages/MachineDetail';
import WorkOrderView from './pages/WorkOrderView';

// Layout
import Layout from './components/Layout/Layout';

// Toast notifications
import { ToastProvider } from './components/ui/Toast';

function App() {
  return (
    <ToastProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/machines" replace />} />
            <Route path="/machines" element={<MachineDashboard />} />
            <Route path="/machines/:id" element={<MachineDetail />} />
            <Route path="/work-orders" element={<WorkOrderView />} />
          </Routes>
        </Layout>
      </Router>
    </ToastProvider>
  );
}

export default App;
