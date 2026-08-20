const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000/api';
async function request(path, options = {}) {
  let response;
  try { response = await fetch(`${API_URL}${path}`, options); } catch { throw new Error('Cannot reach the backend. Start Flask on http://127.0.0.1:5000.'); }
  const body = (response.headers.get('content-type') || '').includes('application/json') ? await response.json() : {};
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status}).`);
  return body;
}
export const api = { getLaptops: () => request('/laptops'), getStats: () => request('/stats'), scrape: () => request('/scrape', { method: 'POST' }), predictPrice: data => request('/predict-price', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }), classify: data => request('/classify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }), recommend: data => request('/recommend', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }) };
