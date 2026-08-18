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
        <label className="text-sm font-medium text-gray-700 mb-1">
          {label}
          {required && <span className="text-error ml-1">*</span>}
        </label>
      )}
      <div className="relative">
        {startIcon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="material-icons-round text-gray-400 text-xl">{startIcon}</span>
          </div>
        )}
        <input
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          className={clsx(
            'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 transition-colors',
            startIcon && 'pl-10',
            error
              ? 'border-error focus:ring-error focus:border-error'
              : 'border-gray-300 focus:ring-primary focus:border-primary',
            disabled && 'bg-gray-100 cursor-not-allowed',
            'text-gray-800 placeholder-gray-400'
          )}
          {...props}
        />
      </div>
      {helperText && (
        <p className={clsx('text-sm mt-1', error ? 'text-error' : 'text-gray-600')}>
          {helperText}
        </p>
      )}
    </div>
  );
};
