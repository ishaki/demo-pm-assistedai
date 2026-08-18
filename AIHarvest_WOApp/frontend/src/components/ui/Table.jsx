import React from 'react';
import clsx from 'clsx';

export const Table = ({ children, className = '' }) => {
  return (
    <div className="overflow-x-auto">
      <table className={clsx('min-w-full divide-y divide-gray-200', className)}>
        {children}
      </table>
    </div>
  );
};

export const TableHead = ({ children, className = '' }) => {
  return <thead className={clsx('bg-gray-50', className)}>{children}</thead>;
};

export const TableBody = ({ children, className = '' }) => {
  return <tbody className={clsx('bg-white divide-y divide-gray-200', className)}>{children}</tbody>;
};

export const TableRow = ({ children, hover = false, onClick, className = '' }) => {
  return (
    <tr
      onClick={onClick}
      className={clsx(
        hover && 'hover:bg-gray-50 cursor-pointer transition-colors',
        className
      )}
    >
      {children}
    </tr>
  );
};

export const TableCell = ({ children, header = false, align = 'left', className = '' }) => {
  const Component = header ? 'th' : 'td';
  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  };

  return (
    <Component
      className={clsx(
        'px-6 py-4',
        header ? 'text-xs font-semibold text-gray-700 uppercase tracking-wider' : 'text-sm text-gray-800',
        alignClasses[align],
        className
      )}
    >
      {children}
    </Component>
  );
};

export const TableSortLabel = ({ children, active, direction, onClick }) => {
  return (
    <button
      onClick={onClick}
      className="group inline-flex items-center gap-1 hover:text-gray-900 focus:outline-none"
    >
      {children}
      <span className={clsx(
        'material-icons-round text-base transition-opacity',
        active ? 'opacity-100' : 'opacity-0 group-hover:opacity-50'
      )}>
        {direction === 'asc' ? 'arrow_upward' : 'arrow_downward'}
      </span>
    </button>
  );
};

export const TablePagination = ({
  count,
  page,
  rowsPerPage,
  onPageChange,
  onRowsPerPageChange,
  rowsPerPageOptions = [5, 10, 25, 50]
}) => {
  const totalPages = Math.ceil(count / rowsPerPage);
  const startIndex = page * rowsPerPage + 1;
  const endIndex = Math.min((page + 1) * rowsPerPage, count);

  return (
    <div className="px-6 py-4 flex items-center justify-between border-t border-gray-200 bg-white">
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-600">Rows per page:</span>
        <select
          value={rowsPerPage}
          onChange={(e) => onRowsPerPageChange({ target: { value: parseInt(e.target.value) } })}
          className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        >
          {rowsPerPageOptions.map(option => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-600">
          {startIndex}-{endIndex} of {count}
        </span>
        <div className="flex gap-1">
          <button
            onClick={() => onPageChange(null, page - 1)}
            disabled={page === 0}
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="material-icons-round text-xl">chevron_left</span>
          </button>
          <button
            onClick={() => onPageChange(null, page + 1)}
            disabled={page >= totalPages - 1}
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="material-icons-round text-xl">chevron_right</span>
          </button>
        </div>
      </div>
    </div>
  );
};
