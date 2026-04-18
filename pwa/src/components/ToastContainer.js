import React from 'react';
import { CheckCircle, Warning, XCircle } from '@phosphor-icons/react';
import { useApp } from '../context/AppContext';

const icons = {
  success: CheckCircle,
  warning: Warning,
  error: XCircle,
};
const colors = {
  success: 'var(--success)',
  warning: 'var(--warning)',
  error: 'var(--danger)',
};

export default function ToastContainer() {
  const { toasts } = useApp();

  if (!toasts.length) return null;

  return (
    <div className="toast-container">
      {toasts.map(toast => {
        const Icon = icons[toast.type] || icons.success;
        return (
          <div key={toast.id} className="toast" style={{ marginBottom: 8 }}>
            <Icon size={20} color={colors[toast.type] || colors.success} weight="fill" />
            <span>{toast.message}</span>
          </div>
        );
      })}
    </div>
  );
}
