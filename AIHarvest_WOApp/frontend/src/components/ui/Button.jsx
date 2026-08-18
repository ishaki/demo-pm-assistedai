import React from 'react';
import clsx from 'clsx';

export const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  startIcon,
  disabled = false,
  onClick,
  className = '',
  type = 'button',
  ...props
}) => {
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2';

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  const variantClasses = {
    primary: 'bg-primary text-white hover:bg-primary-600 focus:ring-primary disabled:bg-gray-300',
    outlined: 'border border-primary text-primary bg-white hover:bg-primary-50 focus:ring-primary disabled:border-gray-300 disabled:text-gray-400',
    text: 'text-primary hover:bg-primary-50 focus:ring-primary disabled:text-gray-400',
    success: 'bg-success text-white hover:bg-green-600 focus:ring-success disabled:bg-gray-300',
    error: 'bg-error text-white hover:bg-red-600 focus:ring-error disabled:bg-gray-300',
    warning: 'bg-warning text-white hover:bg-yellow-600 focus:ring-warning disabled:bg-gray-300',
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        baseClasses,
        sizeClasses[size],
        variantClasses[variant],
        disabled && 'cursor-not-allowed opacity-60',
        className
      )}
      {...props}
    >
      {startIcon && <span className="material-icons-round text-xl mr-2">{startIcon}</span>}
      {children}
    </button>
  );
};
