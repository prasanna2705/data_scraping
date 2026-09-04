import { useEffect, useState } from 'react';
import { api, money } from '../api';
import { useSource } from '../context/SourceContext';

const emptyFilters = {
  page: 1,
  per_page: 12,
  sort: 'price_asc',
  search: '',
  brand: '',
  ram_gb: '',
  storage_gb: '',
  processor: '',
  max_price: '',
  min_price: '',
};

export default function Catalog() {
  const { source, meta } = useSource();
  const [filters, setFilters] = useState(emptyFilters);
  const [data, setData] = useState({ records: [], brands: [], processors: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      try {
        const response = await api.getCatalog(filters, source);
        if (!alive) return;
        setData(response);
        setError(response.message && !response.records?.length ? response.message : '');
      } catch (err) {
        if (alive) {
          setError(err.message);
          setData({ records: [], brands: [], processors: [], total: 0 });
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [filters, source]);

  const change = (key, value) => setFilters((prev) => ({ ...prev, [key]: value, page: key === 'page' ? value : 1 }));

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <h2>Catalog</h2>
          <p>
            Current Source: <b>{meta.label || source}</b> · Records: <b>{meta.records ?? data.total}</b>
          </p>
        </div>
      </header>

      <div className="filters">
        <input placeholder="Search" value={filters.search} onChange={(e) => change('search', e.target.value)} />
        <select value={filters.brand} onChange={(e) => change('brand', e.target.value)}>
          <option value="">All brands</option>
          {(data.brands || []).map((brand) => (
            <option key={brand} value={brand}>{brand}</option>
          ))}
        </select>
        <select value={filters.ram_gb} onChange={(e) => change('ram_gb', e.target.value)}>
          <option value="">Any RAM</option>
          {[4, 8, 16, 32, 64].map((v) => <option key={v} value={v}>{v} GB</option>)}
        </select>
        <select value={filters.storage_gb} onChange={(e) => change('storage_gb', e.target.value)}>
          <option value="">Any storage</option>
          {[128, 256, 512, 1024, 2048].map((v) => <option key={v} value={v}>{v} GB</option>)}
        </select>
        <input placeholder="Processor filter" value={filters.processor} onChange={(e) => change('processor', e.target.value)} />
        <input type="number" placeholder="Min price" value={filters.min_price} onChange={(e) => change('min_price', e.target.value)} />
        <input type="number" placeholder="Max price" value={filters.max_price} onChange={(e) => change('max_price', e.target.value)} />
        <select value={filters.sort} onChange={(e) => change('sort', e.target.value)}>
          <option value="price_asc">Price: low to high</option>
          <option value="price_desc">Price: high to low</option>
          <option value="rating_desc">Rating</option>
        </select>
      </div>

      {loading && <p className="status">Loading catalog…</p>}
      {error && !loading && <div className="banner error">{error || 'No laptop data is currently available for this source.'}</div>}

      {!loading && !error && !data.records?.length && (
        <div className="empty">No laptop data is currently available for this source.</div>
      )}

      {!loading && !!data.records?.length && (
        <>
          <div className="catalog-grid">
            {data.records.map((item) => (
              <article key={item.id} className="product-card">
                <div className="thumb">
                  {item.image_url ? (
                    <img src={item.image_url} alt="" loading="lazy" />
                  ) : (
                    <div className="thumb-fallback" aria-hidden="true">
                      <span>{(item.brand || 'Laptop').slice(0, 1)}</span>
                    </div>
                  )}
                </div>
                <div className="product-body">
                  <h3>{item.title}</h3>
                  <p className="price">{money(item.price)}</p>
                  <ul>
                    <li>{item.brand || '—'}</li>
                    <li>{item.ram_gb != null ? `${item.ram_gb} GB RAM` : 'RAM n/a'}</li>
                    <li>{item.storage_gb != null ? `${item.storage_gb} GB storage` : 'Storage n/a'}</li>
                    <li>{item.processor || item.cpu || 'Processor n/a'}</li>
                    <li>{item.screen_size != null ? `${item.screen_size}"` : 'Screen n/a'}</li>
                    <li>{item.rating != null ? `${item.rating} ★` : 'Rating n/a'}</li>
                  </ul>
                  <small>{item.source || meta.label}</small>
                </div>
              </article>
            ))}
          </div>
          <div className="pager">
            <button type="button" disabled={filters.page <= 1} onClick={() => change('page', filters.page - 1)}>Previous</button>
            <span>Page {data.page} · {data.total} records</span>
            <button
              type="button"
              disabled={filters.page * filters.per_page >= data.total}
              onClick={() => change('page', filters.page + 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </section>
  );
}
