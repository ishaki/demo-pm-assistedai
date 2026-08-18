import React from 'react';
import clsx from 'clsx';

export const Card = ({ children, className = '', hover = false }) => {
  return (
    <div className={clsx(
      'bg-surface rounded-lg shadow-card border border-line',
      hover && 'hover:shadow-card-hover transition-shadow duration-200',
      className
    )}>
      {children}
    </div>
  );
};

export const CardHeader = ({ children, className = '' }) => {
  return <div className={clsx('px-6 py-4 border-b border-line', className)}>{children}</div>;
};

export const CardContent = ({ children, className = '' }) => {
  return <div className={clsx('px-6 py-4', className)}>{children}</div>;
};
