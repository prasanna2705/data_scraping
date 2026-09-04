import { useState } from 'react';
import { api, money } from '../api';
import { useSource } from '../context/SourceContext';
import SpecForm from '../components/SpecForm';

function MetricBlock({ metrics, reliable }) {
  if (!reliable || !metrics) {
    return <p className="muted">Evaluation metrics are not shown until enough records are available.</p>;
  }
  return (
    <ul>
      <li>MAE: {money(metrics.mae)}</li>
      <li>RMSE: {money(metrics.rmse)}</li>
      <li>R²: {metrics.r2 ?? '—'}</li>
    </ul>
  );
}

export default function Prediction() {
  const { source, meta } = useSource();
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (values) => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await api.predictPrice({ ...values, source });
      setResult(response);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const empty = !meta.records;

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <h2>Prediction</h2>
          <p>Current Dataset: <b>{meta.label || source}</b>{meta.records != null ? ` · ${meta.records} records` : ''}</p>
        </div>
      </header>
      {empty && (
        <div className="banner error">
          No laptop data is currently available for this source. Load the Kaggle dataset or scrape Amazon first.
        </div>
      )}
      {!empty && (
        <SpecForm onSubmit={submit} submitText={loading ? 'Predicting…' : 'Predict Price'} />
      )}
      {error && <div className="banner error">{error}</div>}
      {result && (
        <div className="ml-results">
          {result.linear_regression?.metrics == null && result.random_forest?.metrics == null && (
            <p className="banner">
              Predictions use the real {meta.label || source} model. Hold-out metrics are hidden until more
              products are available for a reliable evaluation.
            </p>
          )}
          <article>
            <h3>Linear Regression</h3>
            <p className="price">{money(result.linear_regression?.predicted_price)}</p>
            <MetricBlock
              metrics={result.linear_regression?.metrics}
              reliable={result.linear_regression?.metrics != null}
            />
          </article>
          <article>
            <h3>Random Forest</h3>
            <p className="price">{money(result.random_forest?.predicted_price)}</p>
            <MetricBlock
              metrics={result.random_forest?.metrics}
              reliable={result.random_forest?.metrics != null}
            />
          </article>
          {result.best_model ? (
            <p className="banner ok">Better-performing model: <b>{result.best_model}</b></p>
          ) : (
            <p className="banner">Model comparison metrics will appear once the dataset is large enough.</p>
          )}
        </div>
      )}
    </section>
  );
}
