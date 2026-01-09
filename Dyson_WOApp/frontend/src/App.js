import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Pages
import MachineDashboard from './pages/MachineDashboard';
import MachineDetail from './pages/MachineDetail';
import WorkOrderView from './pages/WorkOrderView';

// Layout
import Layout from './components/Layout/Layout';

function App() {
  return (
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
  );
}

export default App;
