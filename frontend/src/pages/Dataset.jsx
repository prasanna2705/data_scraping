import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, money } from '../api';
import { useSource } from '../context/SourceContext';

export default function Dataset() {
  const { setSource, meta } = useSource();
  const navigate = useNavigate();
  const [info, setInfo] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      try {
        const data = await api.kaggleDataset();
        if (!alive) return;
        setInfo(data);
        await setSource('kaggle');
      } catch (err) {
        if (alive) setError(err.message);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Option 1</p>
          <h2>Dataset Analysis</h2>
          <p>Loads the real Kaggle Laptop Price Prediction dataset and sets it as the active source.</p>
        </div>
      </header>

      {loading && <p className="status">Loading Kaggle dataset…</p>}
      {error && <div className="banner error">{error}</div>}

      {info && (
        <div className="dataset-panel">
          <div className="stat-grid">
            <article><small>Source</small><strong>{info.label}</strong></article>
            <article><small>Records</small><strong>{info.records}</strong></article>
            <article><small>Active catalog</small><strong>{meta.records}</strong></article>
          </div>
          <p className="muted">
            Source:{' '}
            <a href="https://www.kaggle.com/datasets/eslamelsolya/laptop-price-prediction" target="_blank" rel="noreferrer">
              kaggle.com/datasets/eslamelsolya/laptop-price-prediction
            </a>
          </p>
          <div className="table wrap">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Brand</th>
                  <th>Price</th>
                  <th>RAM</th>
                  <th>Storage</th>
                </tr>
              </thead>
              <tbody>
                {(info.sample || []).map((row, index) => (
                  <tr key={index}>
                    <td>{row.title}</td>
                    <td>{row.brand}</td>
                    <td>{money(row.price)}</td>
                    <td>{row.ram_gb != null ? `${row.ram_gb} GB` : '—'}</td>
                    <td>{row.storage_gb != null ? `${row.storage_gb} GB` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="actions">
            <button type="button" onClick={() => navigate('/catalog')}>Continue to Catalog</button>
            <Link className="ghost" to="/prediction">Continue to Prediction</Link>
          </div>
        </div>
      )}
    </section>
  );
}
