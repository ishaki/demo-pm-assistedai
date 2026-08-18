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
        <label className="text-sm font-medium text-gray-700 mb-1">
          {label}
          {required && <span className="text-error ml-1">*</span>}
        </label>
      )}
      <select
        value={value}
        onChange={onChange}
        disabled={disabled}
        className={clsx(
          'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-colors',
          'text-gray-800 bg-white',
          disabled && 'bg-gray-100 cursor-not-allowed'
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
