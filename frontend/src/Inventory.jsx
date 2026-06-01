import { useEffect, useState } from 'react';
import { fetchProducts } from './api';

function Inventory() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
      <h2 className="mb-1">Inventory</h2>
      <small className="d-block mb-4 react-muted">Ebyatundibwa</small>
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
                <button type="button" className="btn btn-primary mt-auto" style={{background: 'var(--secondary)', borderColor: 'var(--secondary)', color: 'var(--primary)'}}>
                  Add to Cart<br />
                  <small style={{fontWeight: 'normal', opacity: 0.85}}>Gattako mu Kikapu</small>
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
