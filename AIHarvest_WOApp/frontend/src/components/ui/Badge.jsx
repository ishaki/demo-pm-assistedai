import React from 'react';
import clsx from 'clsx';

export const Badge = ({ children, variant = 'default', size = 'md', className = '' }) => {
  const baseClasses = 'inline-flex items-center font-medium rounded-full';

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
  };

  const variantClasses = {
    default: 'bg-gray-100 text-gray-700',
    primary: 'bg-primary text-white',
    error: 'bg-error text-white',
    warning: 'bg-warning text-white',
    success: 'bg-success text-white',
    info: 'bg-blue-500 text-white',
    gray: 'bg-gray-500 text-white',
  };

  return (
    <span className={clsx(baseClasses, sizeClasses[size], variantClasses[variant], className)}>
      {children}
    </span>
  );
};
