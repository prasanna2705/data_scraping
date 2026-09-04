import { Link } from 'react-router-dom';
import { useSource } from '../context/SourceContext';

export default function Home() {
  const { meta, source } = useSource();
  return (
    <div className="home">
      <section className="hero">
        <p className="eyebrow">Data · ML · Scraping · Recommendations</p>
        <h1>LAPTOP INTELLIGENCE</h1>
        <p className="tagline">Analyze · Scrape · Predict · Classify · Recommend</p>
        <p className="lede">
          Analyze real laptop datasets and web sources. Both paths feed the same catalog,
          prediction, classification, recommendation, and ML analysis pipeline.
        </p>
        <div className="hero-actions">
          <Link className="choice-card" to="/dataset">
            <span className="choice-kicker">Option 1</span>
            <strong>Dataset Analysis</strong>
            <p>Kaggle Laptop Price Prediction — ~1,300 labelled records.</p>
            <span className="choice-cta">Explore</span>
          </Link>
          <Link className="choice-card scrape" to="/scraping">
            <span className="choice-kicker">Option 2</span>
            <strong>Web Scraping</strong>
            <p>Amazon laptop listings (live scrape).</p>
            <span className="choice-cta">Scrape</span>
          </Link>
        </div>
        <div className="coming-soon-row">
          <span className="chip disabled">Flipkart — Coming Soon</span>
          <span className="chip disabled">Croma — Coming Soon</span>
        </div>
        <p className="active-pill">
          Active source: <b>{meta.label || source}</b>
          {meta.records != null ? ` · ${meta.records} records` : ''}
        </p>
      </section>

      <section className="features-panel">
        <h2>Features</h2>
        <ul>
          <li>Real Dataset Analysis</li>
          <li>Website Scraping</li>
          <li>Price Prediction</li>
          <li>Classification</li>
          <li>Recommendation</li>
          <li>ML Model Comparison</li>
        </ul>
      </section>
    </div>
  );
}
