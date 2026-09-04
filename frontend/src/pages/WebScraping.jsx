import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useSource } from '../context/SourceContext';

const EXAMPLES = ['Amazon laptops', 'https://www.amazon.in/'];
const COMING_SOON = ['Flipkart laptops', 'Croma'];

export default function WebScraping() {
  const { setSource, refreshMeta } = useSource();
  const navigate = useNavigate();
  const [query, setQuery] = useState('Amazon laptops');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [soonNote, setSoonNote] = useState('');

  const start = async () => {
    setRunning(true);
    setError('');
    setSoonNote('');
    setResult(null);
    try {
      const response = await api.scrape({ query });
      setResult(response);
      if (response.success && response.source_key) {
        await setSource(response.source_key);
        await refreshMeta(response.source_key);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Option 2</p>
          <h2>Web Scraping</h2>
          <p>Enter an Amazon laptop search phrase or Amazon URL. Flipkart and OnePlus are Coming Soon.</p>
        </div>
      </header>

      <div className="scrape-box">
        <label>
          Enter website, company name, laptop search or URL
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Amazon laptops"
          />
        </label>
        <div className="example-row">
          {EXAMPLES.map((item) => (
            <button
              type="button"
              className="chip"
              key={item}
              onClick={() => {
                setQuery(item);
                setSoonNote('');
              }}
            >
              {item}
            </button>
          ))}
          {COMING_SOON.map((item) => (
            <button
              type="button"
              className="chip disabled"
              key={item}
              onClick={() => {
                setSoonNote(`${item.split(' ')[0]} scraping is Coming Soon. Currently supported: Amazon.`);
                setResult(null);
                setError('');
              }}
            >
              {item} — Coming Soon
            </button>
          ))}
        </div>
        <button type="button" disabled={running || !query.trim()} onClick={start}>
          {running ? 'Scraping…' : 'Start Scraping'}
        </button>
      </div>

      {soonNote && <div className="banner">{soonNote}</div>}
      {error && <div className="banner error">{error}</div>}

      {result && (
        <div className={`results-panel ${result.success ? 'ok' : 'fail'}`}>
          <h3>Scraping Results</h3>
          {result.source && <p>Source: <b>{result.source}</b></p>}
          <ul className="result-stats">
            <li>Products discovered: {result.products_discovered ?? result.records_found ?? 0}</li>
            <li>Valid products: {result.valid_products ?? 0}</li>
            <li>Duplicates removed: {result.duplicates_removed ?? result.duplicates ?? 0}</li>
            <li>Invalid records: {result.invalid_records ?? 0}</li>
            <li>Failed records: {result.failed_records ?? 0}</li>
          </ul>
          <p>{result.message}</p>
          {result.success ? (
            <div className="actions">
              <button type="button" onClick={() => navigate('/catalog')}>View Dataset</button>
              <Link className="ghost" to="/catalog">Continue to Catalog</Link>
              <Link className="ghost" to="/prediction">Continue to Prediction</Link>
            </div>
          ) : (
            <p className="muted">{result.message || 'No valid laptop products were found.'}</p>
          )}
        </div>
      )}
    </section>
  );
}
