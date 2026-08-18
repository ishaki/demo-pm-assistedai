import React from 'react';
import clsx from 'clsx';

export const Input = ({
  label,
  type = 'text',
  placeholder,
  value,
  onChange,
  startIcon,
  disabled = false,
  className = '',
  error = false,
  helperText,
  required = false,
  ...props
}) => {
  return (
    <div className={clsx('flex flex-col', className)}>
      {label && (
        <label className="text-sm font-medium text-content mb-1">
          {label}
          {required && <span className="text-error-on-soft ml-1">*</span>}
        </label>
      )}
      <div className="relative">
        {startIcon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="material-icons-round text-content-subtle text-xl">{startIcon}</span>
          </div>
        )}
        <input
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          className={clsx(
            'w-full px-3 py-2 border rounded-lg focus:outline-none focus-visible:ring-2 transition-colors',
            startIcon && 'pl-10',
            error
              ? 'border-error focus-visible:ring-error focus-visible:border-error'
              : 'border-line-strong focus-visible:ring-primary focus-visible:border-primary',
            disabled && 'bg-sunken cursor-not-allowed',
            'bg-surface text-content placeholder-content-subtle'
          )}
          {...props}
        />
      </div>
      {helperText && (
        <p className={clsx('text-sm mt-1', error ? 'text-error-on-soft' : 'text-content-muted')}>
          {helperText}
        </p>
      )}
    </div>
  );
};
