import { useState } from 'react';
import { api, money } from '../api';
import { useSource } from '../context/SourceContext';
import SpecForm from '../components/SpecForm';

export default function Recommendation() {
  const { source, meta } = useSource();
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (values) => {
    setLoading(true);
    setError('');
    setNote('');
    setItems([]);
    try {
      const response = await api.recommend({ ...values, source, limit: 5 });
      const list = response.recommendations || response.items || (Array.isArray(response) ? response : []);
      setItems(list);
      setNote(list.length ? '' : (response.message || 'No current catalog listings meet those requirements.'));
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
          <h2>Recommendation</h2>
          <p>
            Current Source: <b>{meta.label || source}</b>
            {meta.records != null ? ` · ${meta.records} records` : ''}
            {' · '}Returns real laptops from the active dataset via KNN.
          </p>
        </div>
      </header>
      {empty && (
        <div className="banner error">
          No laptop data is currently available for this source. Load the Kaggle dataset or scrape Amazon first.
        </div>
      )}
      {!empty && (
        <SpecForm budget onSubmit={submit} submitText={loading ? 'Searching…' : 'Find Similar Laptops'} />
      )}
      {error && <div className="banner error">{error}</div>}
      {note && <div className="banner">{note}</div>}
      <div className="recommend-list">
        {items.map((item, index) => (
          <article key={item.id || item.title || index}>
            <span className="rank">{index + 1}</span>
            <div>
              <h3>{item.title}</h3>
              <p>{money(item.price)} · {item.ram_gb} GB RAM · {item.storage_gb} GB · {item.brand}</p>
              {item.similarity != null && (
                <small>Similarity score: {Math.round(Number(item.similarity) * 100)} / 100</small>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
