import { useEffect, useState } from 'react';
import { api, money } from '../api';
import { useSource } from '../context/SourceContext';

function MetricValue({ value, moneyFormat = false }) {
  if (value == null || value === '') return '—';
  return moneyFormat ? money(value) : value;
}

export default function MLAnalysis() {
  const { source, meta } = useSource();
  const [metrics, setMetrics] = useState(null);
  const [importance, setImportance] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      setError('');
      setMetrics(null);
      setImportance([]);
      try {
        if (!meta.records && source) {
          // Still attempt API — it returns a clear empty/error message
        }
        const [analysis, features] = await Promise.all([
          api.mlAnalysis(source),
          api.importance(source).catch(() => ({ items: [] })),
        ]);
        if (!alive) return;
        if (analysis.error) {
          setError(analysis.error);
          setMetrics(null);
        } else {
          setMetrics(analysis);
        }
        setImportance(features.items || []);
      } catch (err) {
        if (alive) setError(err.message);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [source, meta.records]);

  const reliable = metrics?.reliable !== false && metrics?.linear_regression != null;

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <h2>ML Analysis</h2>
          <p>
            Current Source: <b>{meta.label || source}</b>
            {meta.records != null ? ` · ${meta.records} records` : ''}
            {' · '}Models trained only on this source.
          </p>
        </div>
      </header>

      {loading && <p className="status">Loading ML analysis…</p>}
      {error && <div className="banner error">{error}</div>}

      {metrics && (
        <>
          <div className="table wrap">
            <table>
              <thead>
                <tr><th>Algorithm</th><th>Purpose</th></tr>
              </thead>
              <tbody>
                {(metrics.algorithms || []).map((row) => (
                  <tr key={row.name}><td>{row.name}</td><td>{row.purpose}</td></tr>
                ))}
              </tbody>
            </table>
          </div>

          {metrics.reliability_note && (
            <div className="banner">{metrics.reliability_note}</div>
          )}

          <div className="ml-results">
            <article>
              <h3>Linear Regression</h3>
              {reliable ? (
                <ul>
                  <li>MAE: <MetricValue value={metrics.linear_regression?.mae} moneyFormat /></li>
                  <li>RMSE: <MetricValue value={metrics.linear_regression?.rmse} moneyFormat /></li>
                  <li>R²: <MetricValue value={metrics.linear_regression?.r2} /></li>
                </ul>
              ) : (
                <p className="muted">Metrics unavailable — not enough records for a reliable evaluation.</p>
              )}
            </article>
            <article>
              <h3>Random Forest Regressor</h3>
              {reliable ? (
                <ul>
                  <li>MAE: <MetricValue value={metrics.random_forest?.mae} moneyFormat /></li>
                  <li>RMSE: <MetricValue value={metrics.random_forest?.rmse} moneyFormat /></li>
                  <li>R²: <MetricValue value={metrics.random_forest?.r2} /></li>
                </ul>
              ) : (
                <p className="muted">Metrics unavailable — not enough records for a reliable evaluation.</p>
              )}
            </article>
            <article>
              <h3>Random Forest Classifier</h3>
              {reliable && metrics.classification ? (
                <ul>
                  <li>Accuracy: <MetricValue value={metrics.classification?.accuracy} /></li>
                  <li>Precision: <MetricValue value={metrics.classification?.precision} /></li>
                  <li>Recall: <MetricValue value={metrics.classification?.recall} /></li>
                  <li>F1-score: <MetricValue value={metrics.classification?.f1} /></li>
                </ul>
              ) : (
                <p className="muted">Metrics unavailable — not enough records for a reliable evaluation.</p>
              )}
            </article>
            <article>
              <h3>KNN Recommendation</h3>
              <p>{metrics.recommendation?.note}</p>
              <ul>
                <li>Neighbors: {metrics.recommendation?.neighbors}</li>
                <li>Features: {(metrics.recommendation?.features || []).join(', ')}</li>
              </ul>
            </article>
          </div>

          <p className={`banner ${metrics.best_model ? 'ok' : ''}`}>
            Dataset: {metrics.dataset_source} · Training rows: {metrics.training_rows} · Test rows: {metrics.testing_rows}
            {metrics.best_model ? <> · Best regressor: <b>{metrics.best_model}</b></> : null}
          </p>

          {reliable && !!importance.length && (
            <article className="importance">
              <h3>Random Forest feature importance</h3>
              {importance.slice(0, 12).map((item) => (
                <div className="bar" key={item.feature}>
                  <span>{String(item.feature).replaceAll('_', ' ')}</span>
                  <i style={{ width: `${Math.max(4, item.importance * 100)}%` }} />
                  <b>{(item.importance * 100).toFixed(1)}%</b>
                </div>
              ))}
            </article>
          )}

          {reliable && !!metrics.actual_vs_predicted?.length && (
            <article className="importance">
              <h3>Actual vs predicted (held-out test sample)</h3>
              {metrics.actual_vs_predicted.slice(0, 12).map((row, index) => {
                const max = Math.max(...metrics.actual_vs_predicted.slice(0, 12).flatMap((x) => [x.actual, x.predicted]));
                return (
                  <div className="prediction-row" key={index}>
                    <span>#{index + 1}</span>
                    <i style={{ width: `${(row.actual / max) * 100}%` }} title={`Actual ${money(row.actual)}`} />
                    <em style={{ width: `${(row.predicted / max) * 100}%` }} title={`Predicted ${money(row.predicted)}`} />
                    <b>{money(row.actual)} / {money(row.predicted)}</b>
                  </div>
                );
              })}
            </article>
          )}
        </>
      )}
    </section>
  );
}
