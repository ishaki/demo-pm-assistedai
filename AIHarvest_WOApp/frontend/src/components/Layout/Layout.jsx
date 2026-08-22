import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { ThemeToggle } from '../ui/ThemeToggle';

/**
 * Single source of truth for the brand, so the sidebar and the mobile header
 * cannot drift apart. The browser tab title is static markup in
 * public/index.html and has to be kept in step by hand.
 */
const APP_NAME = 'AI Harvest®';
const APP_DESCRIPTOR = 'WO Automation';

/**
 * Stacked lockup: the full name is too long to sit on one line inside a 256px
 * sidebar at a readable size, so the descriptor drops beneath the name as a
 * tracked caption.
 */
const BrandLockup = () => (
  <div className="flex items-center min-w-0">
    <span className="material-icons-round text-primary text-3xl flex-shrink-0">
      precision_manufacturing
    </span>
    <div className="ml-2 min-w-0">
      <div className="text-[17px] font-semibold leading-tight text-content truncate">
        {APP_NAME}
      </div>
      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] leading-tight text-content-muted truncate">
        {APP_DESCRIPTOR}
      </div>
    </div>
  </div>
);

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
          <BrandLockup />
          {/* Mobile close button */}
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden ml-2 flex-shrink-0 text-content-subtle hover:text-content"
            aria-label="Close navigation menu"
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

        {/* Footer info. The descriptor is already in the lockup above, so this
            stays short rather than repeating the full name.

            The copyright doubles as the way in to the demo reset page. It is
            styled exactly as it reads -- no underline, no icon, no hover colour
            -- because an audience watching a demo should have no reason to
            notice it. Opens in its own tab so the demo keeps its place. */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-line">
          <p className="text-xs text-content-subtle text-center">
            <a
              href="/demo-reset"
              target="_blank"
              rel="noopener noreferrer"
              title="Demo database reset"
              className="focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
            >
              &copy; {new Date().getFullYear()} {APP_NAME}
            </a>
          </p>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar. The brand and menu button are mobile-only -- on desktop the
            sidebar already shows both -- leaving the bar to carry the theme
            toggle. No page title here: each page renders its own <h1>. */}
        <header className="h-16 flex-shrink-0 bg-raised border-b border-line flex items-center px-4 lg:px-6 shadow-card">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden flex-shrink-0 text-content-subtle hover:text-content"
            aria-label="Open navigation menu"
          >
            <span className="material-icons-round">menu</span>
          </button>
          <div className="lg:hidden ml-3 min-w-0">
            <BrandLockup />
          </div>

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
