import { NavLink, Route, Routes } from 'react-router-dom';
import { SourceProvider, useSource } from './context/SourceContext';
import Home from './pages/Home';
import Dataset from './pages/Dataset';
import WebScraping from './pages/WebScraping';
import Catalog from './pages/Catalog';
import Prediction from './pages/Prediction';
import Classification from './pages/Classification';
import Recommendation from './pages/Recommendation';
import MLAnalysis from './pages/MLAnalysis';

const NAV = [
  ['/', 'Home'],
  ['/dataset', 'Dataset'],
  ['/scraping', 'Web Scraping'],
  ['/catalog', 'Catalog'],
  ['/prediction', 'Prediction'],
  ['/classification', 'Classification'],
  ['/recommendation', 'Recommendation'],
  ['/ml-analysis', 'ML Analysis'],
];

function Shell() {
  const { source, meta, error, setSource } = useSource();
  return (
    <>
      <aside>
        <div className="brand">
          <h1>Laptop<span>IQ</span></h1>
          <p>Intelligence platform</p>
        </div>
        <nav>
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="source-switch">
          <label>
            Active source
            <select value={source} onChange={(event) => setSource(event.target.value)}>
              <option value="kaggle">Kaggle</option>
              <option value="amazon">Amazon</option>
              <option value="flipkart" disabled>
                Flipkart — Coming Soon
              </option>
              <option value="oneplus" disabled>
                Croma — Coming Soon
              </option>
            </select>
          </label>
          <small>{meta.records ?? 0} records</small>
        </div>
      </aside>
      <main>
        {error && <div className="banner error top">{error}</div>}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dataset" element={<Dataset />} />
          <Route path="/scraping" element={<WebScraping />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/prediction" element={<Prediction />} />
          <Route path="/classification" element={<Classification />} />
          <Route path="/recommendation" element={<Recommendation />} />
          <Route path="/ml-analysis" element={<MLAnalysis />} />
        </Routes>
      </main>
    </>
  );
}

export default function App() {
  return (
    <SourceProvider>
      <Shell />
    </SourceProvider>
  );
}
