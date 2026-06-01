import { useEffect, useState } from 'react';
import { fetchFitRecommendation, fetchProducts } from './api';

function Inventory() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [fitForm, setFitForm] = useState({
    bust: '',
    waist: '',
    hips: '',
    height: '',
    usual_size: '',
    fit_preference: 'regular',
    occasion: 'casual',
  });
  const [fitResult, setFitResult] = useState(null);
  const [fitLoading, setFitLoading] = useState(false);
  const [fitError, setFitError] = useState('');

  useEffect(() => {
    fetchProducts()
      .then(data => {
        setProducts(data);
        setLoading(false);
      })
      .catch(() => {
        setError('Failed to load products');
        setLoading(false);
      });
  }, []);

  const openFitChecker = (product) => {
    setSelectedProduct(product);
    setFitResult(null);
    setFitError('');
  };

  const handleFitSubmit = async (event) => {
    event.preventDefault();
    if (!selectedProduct) return;
    setFitLoading(true);
    setFitError('');
    try {
      const response = await fetchFitRecommendation(selectedProduct.id, fitForm);
      setFitResult(response);
    } catch (err) {
      setFitError(err.message || 'Fit check failed');
    } finally {
      setFitLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-2">
        Loading products...
        <br />
        <small className="react-muted">Tukutegeerera ebyatundibwa...</small>
      </div>
    );
  }
  if (error) return <div className="alert alert-danger">{error}</div>;

  return (
    <div className="p-2">
      <div className="d-flex flex-wrap align-items-end justify-content-between gap-3 mb-4">
        <div>
          <h2 className="mb-1">Inventory</h2>
          <small className="d-block react-muted">Ebyatundibwa</small>
        </div>
        <div className="badge text-bg-dark px-3 py-2" style={{background: 'var(--secondary)', color: 'var(--primary)'}}>
          AI fit guidance enabled
        </div>
      </div>

      <div className="card mb-4 shadow-sm" style={{background: 'var(--surface-soft)', color: 'var(--text)'}}>
        <div className="card-body">
          <div className="d-flex flex-wrap align-items-start justify-content-between gap-3">
            <div>
              <h5 className="card-title mb-1">Fit and return-risk checker</h5>
              <p className="card-text react-muted mb-0">Pick a product, add measurements, and get a size suggestion plus a risk label before checkout.</p>
            </div>
            {selectedProduct ? (
              <div className="text-end">
                <div className="fw-semibold">Selected</div>
                <div>{selectedProduct.name}</div>
              </div>
            ) : null}
          </div>

          <form className="row g-3 mt-2" onSubmit={handleFitSubmit}>
            <div className="col-md-2">
              <label className="form-label" htmlFor="fit-bust">Bust (cm)</label>
              <input id="fit-bust" className="form-control" value={fitForm.bust} onChange={(e) => setFitForm({ ...fitForm, bust: e.target.value })} />
            </div>
            <div className="col-md-2">
              <label className="form-label" htmlFor="fit-waist">Waist (cm)</label>
              <input id="fit-waist" className="form-control" value={fitForm.waist} onChange={(e) => setFitForm({ ...fitForm, waist: e.target.value })} />
            </div>
            <div className="col-md-2">
              <label className="form-label" htmlFor="fit-hips">Hips (cm)</label>
              <input id="fit-hips" className="form-control" value={fitForm.hips} onChange={(e) => setFitForm({ ...fitForm, hips: e.target.value })} />
            </div>
            <div className="col-md-2">
              <label className="form-label" htmlFor="fit-height">Height (cm)</label>
              <input id="fit-height" className="form-control" value={fitForm.height} onChange={(e) => setFitForm({ ...fitForm, height: e.target.value })} />
            </div>
            <div className="col-md-2">
              <label className="form-label" htmlFor="fit-usual-size">Usual size</label>
              <input id="fit-usual-size" className="form-control" placeholder="38" value={fitForm.usual_size} onChange={(e) => setFitForm({ ...fitForm, usual_size: e.target.value })} />
            </div>
            <div className="col-md-2">
              <label className="form-label" htmlFor="fit-preference">Fit</label>
              <select id="fit-preference" className="form-select" value={fitForm.fit_preference} onChange={(e) => setFitForm({ ...fitForm, fit_preference: e.target.value })}>
                <option value="snug">Snug</option>
                <option value="regular">Regular</option>
                <option value="relaxed">Relaxed</option>
              </select>
            </div>
            <div className="col-md-3">
              <label className="form-label" htmlFor="fit-occasion">Occasion</label>
              <select id="fit-occasion" className="form-select" value={fitForm.occasion} onChange={(e) => setFitForm({ ...fitForm, occasion: e.target.value })}>
                <option value="casual">Casual</option>
                <option value="office">Office</option>
                <option value="party">Party</option>
                <option value="wedding">Wedding</option>
                <option value="travel">Travel</option>
              </select>
            </div>
            <div className="col-md-9 d-flex align-items-end justify-content-start gap-2">
              <button type="submit" className="btn btn-primary" style={{background: 'var(--secondary)', borderColor: 'var(--secondary)', color: 'var(--primary)'}} disabled={!selectedProduct || fitLoading}>
                {fitLoading ? 'Checking...' : 'Check fit'}
              </button>
              {selectedProduct ? <span className="react-muted">Using {selectedProduct.name}</span> : <span className="react-muted">Choose a product below first.</span>}
            </div>
          </form>

          {fitError ? <div className="alert alert-danger mt-3 mb-0">{fitError}</div> : null}

          {fitResult ? (
            <div className="mt-4 p-3 rounded" style={{background: 'var(--surface)', border: '1px solid rgba(255,255,255,0.08)'}}>
              <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-2">
                <div>
                  <h5 className="mb-1">Recommended size: EU {fitResult.recommended_size}</h5>
                  <small className="react-muted">Fallback size: EU {fitResult.fallback_size}</small>
                </div>
                <div className="d-flex gap-2">
                  <span className="badge bg-success">{fitResult.return_risk} risk</span>
                  <span className="badge bg-secondary">{fitResult.fit_confidence}% confidence</span>
                </div>
              </div>
              <p className="mb-3">{fitResult.why}</p>
              {Array.isArray(fitResult.bundle_suggestions) && fitResult.bundle_suggestions.length > 0 ? (
                <div>
                  <div className="fw-semibold mb-2">Bundle suggestions</div>
                  <div className="row g-2">
                    {fitResult.bundle_suggestions.map((item) => (
                      <div className="col-md-6" key={item.id}>
                        <div className="border rounded p-2 h-100" style={{borderColor: 'rgba(255,255,255,0.08)'}}>
                          <div className="fw-semibold">{item.name}</div>
                          <small className="react-muted">{item.reason}</small>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      <div className="row">
        {products.map(product => (
          <div className="col-md-4 mb-4" key={product.id}>
            <div className="card h-100 shadow-sm" style={{background: 'var(--surface-soft)', color: 'var(--text)'}}>
              {product.images && product.images.length > 0 ? (
                <img src={product.images[0].image} className="card-img-top" alt={product.name} style={{height: '250px', objectFit: 'cover'}} />
              ) : (
                <div className="card-img-top d-flex align-items-center justify-content-center react-muted" style={{height: '250px', background: 'var(--surface)'}}>
                  <span>No Image<br /><small>Tewali Kifaananyi</small></span>
                </div>
              )}
              <div className="card-body d-flex flex-column">
                <h5 className="card-title">{product.name}</h5>
                <p className="card-text">${product.price}</p>
                {product.sizes ? <small className="react-muted d-block mb-2">Sizes: {product.sizes}</small> : null}
                <button type="button" className="btn btn-primary mt-auto" style={{background: 'var(--secondary)', borderColor: 'var(--secondary)', color: 'var(--primary)'}}>
                  Add to Cart<br />
                  <small style={{fontWeight: 'normal', opacity: 0.85}}>Gattako mu Kikapu</small>
                </button>
                <button type="button" className="btn btn-outline-light mt-2" onClick={() => openFitChecker(product)}>
                  Check fit with AI<br />
                  <small style={{fontWeight: 'normal', opacity: 0.85}}>Laba obupimo</small>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Inventory;
