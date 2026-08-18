import React from 'react';
import clsx from 'clsx';

import { useTheme } from '../../contexts/ThemeContext';

/**
 * Light/dark switch. Exposed as role="switch" rather than a plain button so
 * screen readers announce the current state, not just the action.
 */
export const ThemeToggle = ({ className = '' }) => {
  const { isDark, toggleTheme } = useTheme();
  const label = isDark ? 'Switch to light mode' : 'Switch to dark mode';

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label={label}
      title={label}
      onClick={toggleTheme}
      className={clsx(
        'inline-flex h-10 w-10 items-center justify-center rounded-lg',
        'text-content-muted transition-colors duration-200',
        'hover:bg-sunken hover:text-content',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-raised',
        className
      )}
    >
      <span className="material-icons-round text-xl">
        {isDark ? 'light_mode' : 'dark_mode'}
      </span>
    </button>
  );
};

export default ThemeToggle;
