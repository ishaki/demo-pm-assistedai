import React, { Fragment } from 'react';
import { Dialog as HeadlessDialog, Transition } from '@headlessui/react';
import clsx from 'clsx';

export const Dialog = ({ open, onClose, title, children, maxWidth = 'sm' }) => {
  const maxWidthClasses = {
    sm: 'max-w-md',
    md: 'max-w-2xl',
    lg: 'max-w-4xl',
  };

  return (
    <Transition appear show={open} as={Fragment}>
      <HeadlessDialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <HeadlessDialog.Panel
                className={clsx(
                  'w-full transform overflow-hidden rounded-lg bg-white shadow-xl transition-all',
                  maxWidthClasses[maxWidth]
                )}
              >
                {title && (
                  <HeadlessDialog.Title className="px-6 py-4 border-b border-gray-200 text-lg font-semibold text-gray-800">
                    {title}
                  </HeadlessDialog.Title>
                )}
                {children}
              </HeadlessDialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </HeadlessDialog>
    </Transition>
  );
};

export const DialogContent = ({ children, className = '' }) => {
  return <div className={clsx('px-6 py-4', className)}>{children}</div>;
};

export const DialogActions = ({ children, className = '' }) => {
  return (
    <div className={clsx('px-6 py-4 bg-gray-50 flex justify-end gap-3', className)}>
      {children}
    </div>
  );
};
