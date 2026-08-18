import React from 'react';
import clsx from 'clsx';

export const Select = ({
  label,
  value,
  onChange,
  options = [],
  disabled = false,
  className = '',
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
      <select
        value={value}
        onChange={onChange}
        disabled={disabled}
        className={clsx(
          'w-full px-3 py-2 border border-line-strong rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:border-primary transition-colors',
          'text-content bg-surface',
          disabled && 'bg-sunken cursor-not-allowed'
        )}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};
