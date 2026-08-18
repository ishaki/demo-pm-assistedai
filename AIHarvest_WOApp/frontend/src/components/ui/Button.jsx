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
  // focus-visible rather than focus: keyboard users still get the ring, mouse
  // users don't get one on every click.
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2';

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  // Solid fills pair with their own `contrast` token rather than a hardcoded
  // white, because the fills invert to light colors in dark mode.
  const variantClasses = {
    primary: 'bg-primary text-primary-contrast hover:bg-primary-hover focus-visible:ring-primary disabled:bg-line-strong disabled:text-content-subtle',
    outlined: 'border border-primary text-primary-on-soft bg-transparent hover:bg-primary-soft focus-visible:ring-primary disabled:border-line disabled:text-content-subtle',
    text: 'text-primary-on-soft hover:bg-primary-soft focus-visible:ring-primary disabled:text-content-subtle',
    success: 'bg-success text-success-contrast hover:bg-success-hover focus-visible:ring-success disabled:bg-line-strong disabled:text-content-subtle',
    error: 'bg-error text-error-contrast hover:bg-error-hover focus-visible:ring-error disabled:bg-line-strong disabled:text-content-subtle',
    warning: 'bg-warning text-warning-contrast hover:bg-warning-hover focus-visible:ring-warning disabled:bg-line-strong disabled:text-content-subtle',
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
