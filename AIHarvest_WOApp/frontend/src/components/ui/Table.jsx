import React from 'react';
import clsx from 'clsx';

export const Table = ({ children, className = '' }) => {
  return (
    <div className="overflow-x-auto">
      <table className={clsx('min-w-full divide-y divide-line', className)}>
        {children}
      </table>
    </div>
  );
};

export const TableHead = ({ children, className = '' }) => {
  return <thead className={clsx('bg-sunken', className)}>{children}</thead>;
};

export const TableBody = ({ children, className = '' }) => {
  return <tbody className={clsx('bg-surface divide-y divide-line', className)}>{children}</tbody>;
};

export const TableRow = ({ children, hover = false, onClick, className = '' }) => {
  return (
    <tr
      onClick={onClick}
      className={clsx(
        hover && 'hover:bg-sunken cursor-pointer transition-colors',
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
        'px-3',
        header
          ? 'py-3 text-xs font-semibold text-content-muted uppercase tracking-[0.03em] whitespace-nowrap'
          : 'py-3.5 text-sm text-content tabular-nums',
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
      className="group inline-flex items-center gap-1 hover:text-content focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
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
    <div className="px-4 py-3 flex items-center justify-between border-t border-line bg-surface">
      <div className="flex items-center gap-4">
        <span className="text-sm text-content-muted">Rows per page:</span>
        <select
          value={rowsPerPage}
          onChange={(e) => onRowsPerPageChange({ target: { value: parseInt(e.target.value) } })}
          className="border border-line-strong bg-surface text-content rounded px-2 py-1 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          {rowsPerPageOptions.map(option => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-sm text-content-muted">
          {startIndex}-{endIndex} of {count}
        </span>
        <div className="flex gap-1">
          <button
            onClick={() => onPageChange(null, page - 1)}
            disabled={page === 0}
            aria-label="Previous page"
            className="p-1 rounded text-content-muted hover:bg-sunken hover:text-content disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <span className="material-icons-round text-xl">chevron_left</span>
          </button>
          <button
            onClick={() => onPageChange(null, page + 1)}
            disabled={page >= totalPages - 1}
            aria-label="Next page"
            className="p-1 rounded text-content-muted hover:bg-sunken hover:text-content disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <span className="material-icons-round text-xl">chevron_right</span>
          </button>
        </div>
      </div>
    </div>
  );
};
