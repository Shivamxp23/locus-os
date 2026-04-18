import React, { useState } from 'react';
import { X } from '@phosphor-icons/react';
import { useApp } from '../context/AppContext';
import { api } from '../utils/api';
import './QuickCapture.css';

export default function QuickCapture({ isOpen, onClose }) {
  const { addToast } = useApp();
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);

  if (!isOpen) return null;

  const handleCapture = async () => {
    if (!text.trim()) return;
    setSending(true);
    const result = await api.createCapture({ text: text.trim(), source: 'pwa' });
    setSending(false);
    if (result) {
      addToast('Captured → Vault / 00-Inbox', 'success');
      setText('');
      onClose();
    } else {
      addToast('Failed to capture. Try again.', 'error');
    }
  };

  return (
    <>
      <div className="backdrop" onClick={onClose} />
      <div className="bottom-sheet quick-capture-sheet">
        <div className="drag-handle" />
        <div className="quick-capture-header">
          <h2 className="heading-1">Capture</h2>
          <button className="btn-icon" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>
        <div className="quick-capture-body">
          <textarea
            className="quick-capture-textarea"
            placeholder="What's on your mind..."
            value={text}
            onChange={e => setText(e.target.value)}
            autoFocus
            rows={4}
          />
          <div className="quick-capture-footer">
            <div className="quick-capture-tags">
              <span className="tag tag-health">PWA</span>
            </div>
            <button
              className="btn-primary"
              onClick={handleCapture}
              disabled={!text.trim() || sending}
            >
              {sending ? 'Capturing...' : 'Capture →'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
