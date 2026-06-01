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

  if (loading) return <div className="bg-dark text-light p-4 rounded-3">Loading products...<br /><small style={{color: '#fff', opacity: 0.85}}>Tukutegeerera ebyatundibwa...</small></div>;
  if (error) return <div className="alert alert-danger">{error}</div>;

  return (
    <div className="bg-dark text-light p-4 rounded-3">
      <h2 className="mb-1">Inventory</h2>
      <small className="d-block mb-4" style={{color: '#fff', opacity: 0.85}}>Ebyatundibwa</small>
      <div className="row">
        {products.map(product => (
          <div className="col-md-4 mb-4" key={product.id}>
            <div className="card h-100 shadow-sm bg-secondary text-light">
              {product.images && product.images.length > 0 ? (
                <img src={product.images[0].image} className="card-img-top" alt={product.name} style={{height: '250px', objectFit: 'cover'}} />
              ) : (
                <div className="card-img-top bg-dark d-flex align-items-center justify-content-center" style={{height: '250px'}}>
                  <span style={{color: '#fff', opacity: 0.85}}>No Image<br /><small>Tewali Kifaananyi</small></span>
                </div>
              )}
              <div className="card-body d-flex flex-column">
                <h5 className="card-title">{product.name}</h5>
                <p className="card-text">${product.price}</p>
                <button className="btn btn-primary mt-auto">
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
