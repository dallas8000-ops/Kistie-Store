// Simple API utility for the React frontend.
// Relative `/api/inventory`: Vite proxies to Django in dev (vite.config.js) — same-origin, fewer CORS/session issues.
const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.trim() || '/api/inventory';

export async function fetchProducts() {
  const res = await fetch(`${API_BASE}/products/`);
  if (!res.ok) throw new Error('Failed to fetch products');
  return res.json();
}

export async function fetchCategories() {
  const res = await fetch(`${API_BASE}/categories/`);
  if (!res.ok) throw new Error('Failed to fetch categories');
  return res.json();
}

export async function fetchFitRecommendation(productId, payload) {
  const res = await fetch(`${API_BASE}/fit-recommend/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_id: productId, ...payload }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.error || 'Failed to fetch fit recommendation');
  }
  return res.json();
}
