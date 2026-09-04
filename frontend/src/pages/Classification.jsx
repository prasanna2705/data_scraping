import { useState } from 'react';
import { api } from '../api';
import { useSource } from '../context/SourceContext';
import SpecForm from '../components/SpecForm';

export default function Classification() {
  const { source, meta } = useSource();
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (values) => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      setResult(await api.classify({ ...values, source }));
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
          <h2>Classification</h2>
          <p>
            Current Source: <b>{meta.label || source}</b>
            {meta.records != null ? ` · ${meta.records} records` : ''}
            {' · '}Categories derived from this dataset&apos;s price distribution.
          </p>
        </div>
      </header>
      {empty && (
        <div className="banner error">
          No laptop data is currently available for this source. Load the Kaggle dataset or scrape Amazon first.
        </div>
      )}
      {!empty && (
        <SpecForm onSubmit={submit} submitText={loading ? 'Classifying…' : 'Classify Laptop'} />
      )}
      {error && <div className="banner error">{error}</div>}
      {result && (
        <div className="classify-result">
          <p className="eyebrow">Predicted Category</p>
          <h3>{result.category}</h3>
          {result.probability != null && (
            <p>Confidence: {Math.round(result.probability * 100)}%</p>
          )}
          {result.probabilities && (
            <ul>
              {Object.entries(result.probabilities).map(([label, score]) => (
                <li key={label}>{label}: {Math.round(score * 100)}%</li>
              ))}
            </ul>
          )}
          {result.thresholds && (
            <p className="muted">
              Budget &lt; {result.thresholds.budget_max?.toLocaleString?.('en-IN') ?? result.thresholds.budget_max}
              {' · '}Mid Range &lt; {result.thresholds.mid_max?.toLocaleString?.('en-IN') ?? result.thresholds.mid_max}
            </p>
          )}
          {!result.metrics && (
            <p className="banner">
              Classification uses the real {meta.label || source} model. Accuracy metrics are hidden until
              more records are available for a reliable evaluation.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
