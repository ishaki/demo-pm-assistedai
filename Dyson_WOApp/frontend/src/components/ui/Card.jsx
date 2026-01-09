import React from 'react';
import clsx from 'clsx';

export const Card = ({ children, className = '', hover = false }) => {
  return (
    <div className={clsx(
      'bg-white rounded-lg shadow-card border border-gray-200',
      hover && 'hover:shadow-card-hover transition-shadow duration-200',
      className
    )}>
      {children}
    </div>
  );
};

export const CardHeader = ({ children, className = '' }) => {
  return <div className={clsx('px-6 py-4 border-b border-gray-200', className)}>{children}</div>;
};

export const CardContent = ({ children, className = '' }) => {
  return <div className={clsx('px-6 py-4', className)}>{children}</div>;
};
