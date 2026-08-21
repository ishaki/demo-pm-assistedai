import React from 'react';
import clsx from 'clsx';

export const Badge = ({ children, variant = 'default', size = 'md', className = '' }) => {
  const baseClasses = 'inline-flex items-center font-medium rounded-full';

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
  };

  // Each fill carries its matching `contrast` token: status colors go bright in
  // dark mode, where white text on them would be unreadable.
  const variantClasses = {
    default: 'bg-line text-content',
    primary: 'bg-primary text-primary-contrast',
    error: 'bg-error text-error-contrast',
    warning: 'bg-warning text-warning-contrast',
    success: 'bg-success text-success-contrast',
    info: 'bg-info text-info-contrast',
    pending: 'bg-pending text-pending-contrast',
    gray: 'bg-line-strong text-content',
  };

  return (
    <span className={clsx(baseClasses, sizeClasses[size], variantClasses[variant], className)}>
      {children}
    </span>
  );
};
