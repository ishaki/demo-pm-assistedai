import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { ThemeToggle } from '../ui/ThemeToggle';

const Layout = ({ children }) => {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const navigation = [
    { name: 'Machines', href: '/machines', icon: 'precision_manufacturing' },
    { name: 'Work Orders', href: '/work-orders', icon: 'assignment' },
  ];

  const isActive = (path) => location.pathname.startsWith(path);

  return (
    <div className="flex h-screen bg-canvas overflow-hidden">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-slate-900 bg-opacity-60 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-30 w-64 bg-raised shadow-raised transform transition-transform duration-300 ease-in-out
        lg:translate-x-0 lg:static lg:inset-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Logo/Branding */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-line">
          <div className="flex items-center">
            <span className="material-icons-round text-primary text-3xl">precision_manufacturing</span>
            <span className="ml-2 text-xl font-semibold text-content">InnoMaint</span>
          </div>
          {/* Mobile close button */}
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-content-subtle hover:text-content"
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
                  ? 'bg-primary text-primary-contrast shadow-card'
                  : 'text-content-muted hover:bg-sunken hover:text-content'
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
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-line">
          <p className="text-xs text-content-subtle text-center">
            AI-Assisted POC © {new Date().getFullYear()}
          </p>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar. The brand and menu button are mobile-only — on desktop the
            sidebar already shows both — leaving the bar to carry the theme
            toggle. No page title here: each page renders its own <h1>. */}
        <header className="h-16 flex-shrink-0 bg-raised border-b border-line flex items-center px-4 lg:px-6 shadow-card">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden text-content-subtle hover:text-content"
            aria-label="Open navigation menu"
          >
            <span className="material-icons-round">menu</span>
          </button>
          <span className="lg:hidden ml-4 text-lg font-semibold text-content">InnoMaint</span>

          <div className="ml-auto flex items-center">
            <ThemeToggle />
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-canvas p-6">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
