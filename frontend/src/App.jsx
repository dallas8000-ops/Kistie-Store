import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import './theme.css';

import Home from './Home';
import About from './About';
import Inventory from './Inventory';
import Cart from './Cart';

function App() {
  return (
    <Router>
      <nav className="navbar navbar-expand-lg navbar-dark react-app-nav mb-4">
        <div className="container-fluid">
          <Link className="navbar-brand" to="/">Kistie Store</Link>
          <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
            <span className="navbar-toggler-icon"></span>
          </button>
          <div className="collapse navbar-collapse" id="navbarNav">
            <ul className="navbar-nav ms-auto">
              <li className="nav-item">
                <Link className="nav-link lh-1" to="/">Home<br /><small className="react-subtle" style={{fontSize: '0.65rem'}}>Eka</small></Link>
              </li>
              <li className="nav-item">
                <Link className="nav-link lh-1" to="/about">About<br /><small className="react-subtle" style={{fontSize: '0.65rem'}}>Ku Ffe</small></Link>
              </li>
              <li className="nav-item">
                <Link className="nav-link lh-1" to="/inventory">Inventory<br /><small className="react-subtle" style={{fontSize: '0.65rem'}}>Ebyatundibwa</small></Link>
              </li>
              <li className="nav-item">
                <Link className="nav-link lh-1" to="/cart">Cart<br /><small className="react-subtle" style={{fontSize: '0.65rem'}}>Ekikapu</small></Link>
              </li>
            </ul>
          </div>
        </div>
      </nav>
      <div className="container react-app-panel py-4">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/cart" element={<Cart />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
