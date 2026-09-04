import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../api';

const STORAGE_KEY = 'laptop_intelligence_source';
const ACTIVE_SOURCES = new Set(['kaggle', 'amazon']);
const SourceContext = createContext(null);

function normalizeActiveSource(value) {
  const key = String(value || 'kaggle').toLowerCase();
  return ACTIVE_SOURCES.has(key) ? key : 'kaggle';
}

export function SourceProvider({ children }) {
  const [source, setSourceState] = useState(() => {
    try {
      return normalizeActiveSource(localStorage.getItem(STORAGE_KEY));
    } catch {
      return 'kaggle';
    }
  });
  const [meta, setMeta] = useState({ label: 'Kaggle', records: 0 });
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);

  const refreshMeta = async (nextSource = source) => {
    const key = normalizeActiveSource(nextSource);
    try {
      const stats = await api.getStats(key);
      setMeta({
        label: stats.label || key,
        records: stats.count || 0,
        message: stats.message,
      });
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setReady(true);
    }
  };

  const setSource = async (nextSource) => {
    const key = normalizeActiveSource(nextSource);
    if (!ACTIVE_SOURCES.has(String(nextSource || '').toLowerCase()) && nextSource) {
      setError(`${String(nextSource)} is Coming Soon. Currently available: Kaggle and Amazon.`);
    }
    setSourceState(key);
    try {
      localStorage.setItem(STORAGE_KEY, key);
    } catch {
      /* ignore */
    }
    try {
      const selected = await api.selectDataset(key);
      if (selected.coming_soon) {
        setError(selected.message || 'This source is Coming Soon.');
        await refreshMeta('kaggle');
        setSourceState('kaggle');
        localStorage.setItem(STORAGE_KEY, 'kaggle');
        return;
      }
      setMeta({
        label: selected.label || key,
        records: selected.records || 0,
        message: selected.message,
        trained: selected.trained,
        train_message: selected.train_message,
        reliable: selected.reliable,
      });
      setError(selected.records ? '' : (selected.message || ''));
    } catch (err) {
      setError(err.message);
      await refreshMeta(key);
    }
  };

  useEffect(() => {
    setSource(source);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = useMemo(
    () => ({ source, setSource, meta, error, ready, refreshMeta }),
    [source, meta, error, ready],
  );

  return <SourceContext.Provider value={value}>{children}</SourceContext.Provider>;
}

export function useSource() {
  const ctx = useContext(SourceContext);
  if (!ctx) throw new Error('useSource must be used within SourceProvider');
  return ctx;
}
