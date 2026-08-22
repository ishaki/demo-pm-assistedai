import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';

// Pages
import MachineDashboard from './pages/MachineDashboard';
import MachineDetail from './pages/MachineDetail';
import WorkOrderView from './pages/WorkOrderView';
import DemoReset from './pages/DemoReset';

// Layout
import Layout from './components/Layout/Layout';

// Toast notifications
import { ToastProvider } from './components/ui/Toast';

/**
 * The chrome every application page shares. A layout route rather than a
 * wrapper around <Routes>, so a page can opt out by sitting outside it --
 * which /demo-reset does, deliberately: it is an internal utility and should
 * not carry the demo's navigation.
 */
const AppLayout = () => (
  <Layout>
    <Outlet />
  </Layout>
);

function App() {
  return (
    <ToastProvider>
      <Router>
        <Routes>
          {/* Standalone, no sidebar. Opened in its own tab from the sidebar
              copyright. */}
          <Route path="/demo-reset" element={<DemoReset />} />

          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/machines" replace />} />
            <Route path="/machines" element={<MachineDashboard />} />
            <Route path="/machines/:id" element={<MachineDetail />} />
            <Route path="/work-orders" element={<WorkOrderView />} />
          </Route>
        </Routes>
      </Router>
    </ToastProvider>
  );
}

export default App;
