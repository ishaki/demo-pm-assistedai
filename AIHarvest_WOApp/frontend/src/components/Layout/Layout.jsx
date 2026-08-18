import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

const Layout = ({ children }) => {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const navigation = [
    { name: 'Machines', href: '/machines', icon: 'precision_manufacturing' },
    { name: 'Work Orders', href: '/work-orders', icon: 'assignment' },
  ];

  const isActive = (path) => location.pathname.startsWith(path);

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-gray-600 bg-opacity-75 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-30 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out
        lg:translate-x-0 lg:static lg:inset-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Logo/Branding */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200">
          <div className="flex items-center">
            <span className="material-icons-round text-primary text-3xl">precision_manufacturing</span>
            <span className="ml-2 text-xl font-semibold text-gray-800">InnoMaint</span>
          </div>
          {/* Mobile close button */}
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-gray-500 hover:text-gray-700"
          >
            <span className="material-icons-round">close</span>
          </button>
        </div>

        {/* Navigation */}
        <nav className="mt-6 px-3">
          {navigation.map((item) => (
            <Link
              key={item.name}
              to={item.href}
              className={`
                flex items-center px-4 py-3 mb-1 rounded-lg transition-colors duration-200
                ${isActive(item.href)
                  ? 'bg-primary text-white shadow-md'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800'
                }
              `}
              onClick={() => setSidebarOpen(false)}
            >
              <span className="material-icons-round text-xl">{item.icon}</span>
              <span className="ml-3 font-medium">{item.name}</span>
            </Link>
          ))}
        </nav>

        {/* Footer info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <p className="text-xs text-gray-500 text-center">
            AI-Assisted POC © {new Date().getFullYear()}
          </p>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar (mobile only) */}
        <header className="lg:hidden h-16 bg-white border-b border-gray-200 flex items-center px-4 shadow-sm">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-gray-500 hover:text-gray-700"
          >
            <span className="material-icons-round">menu</span>
          </button>
          <span className="ml-4 text-lg font-semibold text-gray-800">InnoMaint</span>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-gray-100 p-6">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
