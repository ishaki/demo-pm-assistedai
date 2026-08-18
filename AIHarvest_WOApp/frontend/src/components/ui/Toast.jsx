import React, { createContext, useContext, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';

const ToastContext = createContext(null);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
};

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info', duration = 5000) => {
    const id = Date.now() + Math.random();
    const toast = { id, message, type, duration };

    setToasts((prev) => [...prev, toast]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const success = useCallback((message, duration) => addToast(message, 'success', duration), [addToast]);
  const error = useCallback((message, duration) => addToast(message, 'error', duration), [addToast]);
  const warning = useCallback((message, duration) => addToast(message, 'warning', duration), [addToast]);
  const info = useCallback((message, duration) => addToast(message, 'info', duration), [addToast]);

  return (
    <ToastContext.Provider value={{ success, error, warning, info, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
};

const ToastContainer = ({ toasts, onRemove }) => {
  if (toasts.length === 0) return null;

  return createPortal(
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>,
    document.body
  );
};

const Toast = ({ toast, onRemove }) => {
  const { id, message, type } = toast;

  const typeConfig = {
    success: {
      bg: 'bg-success',
      icon: 'check_circle',
      border: 'border-green-600',
    },
    error: {
      bg: 'bg-error',
      icon: 'error',
      border: 'border-red-600',
    },
    warning: {
      bg: 'bg-warning',
      icon: 'warning',
      border: 'border-amber-600',
    },
    info: {
      bg: 'bg-primary',
      icon: 'info',
      border: 'border-blue-600',
    },
  };

  const config = typeConfig[type] || typeConfig.info;

  return (
    <div
      className={`${config.bg} text-white rounded-lg shadow-lg border-l-4 ${config.border} p-4 min-w-[320px] max-w-md pointer-events-auto animate-slide-in-right`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <span className="material-icons-round text-white flex-shrink-0">{config.icon}</span>
        <div className="flex-1 pt-0.5">
          <p className="text-sm font-medium leading-relaxed">{message}</p>
        </div>
        <button
          onClick={() => onRemove(id)}
          className="text-white hover:text-gray-200 transition-colors flex-shrink-0 -mt-1 -mr-1"
          aria-label="Close notification"
        >
          <span className="material-icons-round text-lg">close</span>
        </button>
      </div>
    </div>
  );
};

export default Toast;
