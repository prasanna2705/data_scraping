const API_URL = import.meta.env.VITE_API_URL ;

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, options);
  } catch {
    throw new Error(
      'Unable to connect to the backend server. Please make sure the Flask server is running.',
    );
  }
  const contentType = response.headers.get('content-type') || '';
  const body = contentType.includes('application/json') ? await response.json() : {};
  if (!response.ok) {
    throw new Error(body.error || `Request failed (${response.status}).`);
  }
  return body;
}

const withSource = (params = {}, source) => {
  const query = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, value);
  });
  if (source) query.set('source', source);
  const text = query.toString();
  return text ? `?${text}` : '';
};

const post = (path, data) =>
  request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

export const api = {
  health: () => request('/health'),
  sources: () => request('/sources'),
  kaggleDataset: () => request('/datasets/kaggle'),
  selectDataset: (source) => post('/datasets/select', { source }),
  getCatalog: (params, source) => request(`/catalog${withSource(params, source)}`),
  getLaptops: (params, source) => request(`/laptops${withSource(params, source)}`),
  getLaptop: (id, source) => request(`/laptops/${id}${withSource({}, source)}`),
  getStats: (source) => request(`/stats${withSource({}, source)}`),
  scrape: (data) => post('/scrape', data),
  validate: (data) => post('/sources/validate', data),
  predictPrice: (data) => post('/predict-price', data),
  classify: (data) => post('/classify', data),
  recommend: (data) => post('/recommend', data),
  mlAnalysis: (source) => request(`/ml-analysis${withSource({}, source)}`),
  performance: (source) => request(`/model-performance${withSource({}, source)}`),
  quality: (source) => request(`/data-quality${withSource({}, source)}`),
  importance: (source) => request(`/feature-importance${withSource({}, source)}`),
  analytics: (source) => request(`/analytics${withSource({}, source)}`),
  train: (source) => post('/train', { source }),
};

export const money = (value) =>
  value == null || value === ''
    ? '—'
    : `₹${Number(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
