import { useEffect, useMemo, useState } from 'react';

const BASE_CURRENCY = 'USD';
const SUPPORTED_CURRENCIES = ['USD', 'EUR', 'KES', 'UGX'];
const PAYMENT_METHODS = [
  { value: 'mtn', label: 'MTN Mobile Money' },
  { value: 'airtel', label: 'Airtel Money' },
  { value: 'worldremit', label: 'WorldRemit' },
];
const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.trim() || '/api/inventory';
const CART_STORAGE_KEY = 'eaf_cart_items';

const FALLBACK_RATES = {
  USD: 1,
  EUR: 0.92,
  KES: 129.5,
  UGX: 3820,
};

function formatAmount(amount, currency) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: currency === 'UGX' ? 0 : 2,
  }).format(amount);
}

function normalizeCartPayload(rawItems) {
  if (!Array.isArray(rawItems)) {
    return [];
  }

  return rawItems
    .map((item) => ({
      id: item.id ?? `${item.product_id ?? 'item'}-${item.size ?? ''}-${item.color ?? ''}`,
      name: item.name ?? item.product_name ?? item.product?.name ?? 'Item',
      price: Number(item.price ?? item.price_usd ?? item.unit_price ?? 0),
      quantity: Math.max(1, Number(item.quantity ?? 1)),
      size: item.size ?? '',
      color: item.color ?? '',
    }))
    .filter((item) => Number.isFinite(item.price) && Number.isFinite(item.quantity));
}

function readCartFromStorage() {
  try {
    const raw = localStorage.getItem(CART_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return normalizeCartPayload(parsed);
  } catch {
    return [];
  }
}

async function loadExchangeRates() {
  try {
    const response = await fetch('https://api.frankfurter.app/latest?from=USD&to=EUR,KES,UGX');
    if (!response.ok) throw new Error('Failed to fetch rates');
    const data = await response.json();
    return {
      rates: {
        USD: 1,
        EUR: data.rates?.EUR ?? FALLBACK_RATES.EUR,
        KES: data.rates?.KES ?? FALLBACK_RATES.KES,
        UGX: data.rates?.UGX ?? FALLBACK_RATES.UGX,
      },
      source: 'live',
      updatedAt: data.date || new Date().toISOString().slice(0, 10),
    };
  } catch {
    return {
      rates: FALLBACK_RATES,
      source: 'fallback',
      updatedAt: new Date().toISOString().slice(0, 10),
    };
  }
}

async function loadCartItems() {
  try {
    const response = await fetch(`${API_BASE}/cart/`, { credentials: 'include' });
    if (!response.ok) throw new Error('Cart endpoint unavailable');
    const data = await response.json();
    return { items: normalizeCartPayload(data?.items), source: 'api', error: '' };
  } catch {
    const storedItems = readCartFromStorage();
    return {
      items: storedItems,
      source: 'local',
      error: storedItems.length === 0 ? 'No synced cart API yet. Showing local cart if available.' : '',
    };
  }
}

function Cart() {
  const [currency, setCurrency] = useState('KES');
  const [paymentMethod, setPaymentMethod] = useState('mtn');
  const [rates, setRates] = useState(FALLBACK_RATES);
  const [ratesSource, setRatesSource] = useState('fallback');
  const [ratesUpdatedAt, setRatesUpdatedAt] = useState(null);
  const [cartItems, setCartItems] = useState([]);
  const [cartSource, setCartSource] = useState('loading');
  const [cartError, setCartError] = useState('');
  const [loadingCart, setLoadingCart] = useState(true);
  const [paying, setPaying] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    let cancelled = false;
    loadExchangeRates().then((data) => {
      if (!cancelled) {
        setRates(data.rates);
        setRatesSource(data.source);
        setRatesUpdatedAt(data.updatedAt);
      }
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoadingCart(true);
    setCartError('');
    loadCartItems().then((data) => {
      if (!cancelled) {
        setCartItems(data.items);
        setCartSource(data.source);
        setCartError(data.error);
        setLoadingCart(false);
      }
    });
    return () => { cancelled = true; };
  }, []);

  const cartTotal = useMemo(
    () => cartItems.reduce((sum, item) => sum + (item.price * item.quantity), 0),
    [cartItems],
  );

  const convertedItems = useMemo(() => {
    const rate = rates[currency] || 1;
    return cartItems.map((item) => ({
      ...item,
      convertedUnitPrice: item.price * rate,
      convertedLineTotal: item.price * item.quantity * rate,
    }));
  }, [cartItems, currency, rates]);

  const convertedTotal = useMemo(() => {
    const rate = rates[currency] || 1;
    return cartTotal * rate;
  }, [cartTotal, currency, rates]);

  const selectedMethodLabel = PAYMENT_METHODS.find((method) => method.value === paymentMethod)?.label || paymentMethod;

  const handlePay = async () => {
    if (cartItems.length === 0) {
      setResult({ error: 'Your cart is empty.' });
      return;
    }

    setPaying(true);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/pay/checkout/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          amount: Number(convertedTotal.toFixed(2)),
          currency,
          exchange_rate: rates[currency] || 1,
          base_currency: BASE_CURRENCY,
          payment_method: paymentMethod,
          customer: { email: 'customer@example.com', name: 'Store Customer' },
          items: convertedItems,
          order_summary: {
            item_count: cartItems.length,
            total_quantity: cartItems.reduce((sum, item) => sum + item.quantity, 0),
          },
        }),
      });
      if (!res.ok) {
        throw new Error('Payment request failed');
      }
      const data = await res.json();
      setResult({
        ...data,
        uiSummary: `${selectedMethodLabel} selected. ${formatAmount(convertedTotal, currency)} ready for checkout.`,
      });
    } catch {
      setResult({ error: 'Payment failed. Try again.' });
    }
    setPaying(false);
  };

  let cartContent;
  if (loadingCart) {
    cartContent = <p className="p-3">Loading your cart...<br /><small className="react-muted">Tukutegeerera ekikapu kyo...</small></p>;
  } else if (cartItems.length === 0) {
    cartContent = <p className="p-3">Your cart is empty. Start shopping!<br /><small className="react-muted">Ekikapu kyo kirina wangu. Tangira okugula!</small></p>;
  } else {
    cartContent = (
      <>
        <div className="card p-3 mb-3 text-start shadow-sm" style={{background: 'var(--surface-soft)', color: 'var(--text)'}}>
          <h5 className="mb-1">Order Information</h5>
          <small className="d-block mb-3">Ebirowoozo by'Omutendera</small>
          <div className="row g-3 align-items-end">
            <div className="col-md-4">
              <label className="form-label mb-1" htmlFor="currencySelect">Currency <small>(Ssente)</small></label>
              <select id="currencySelect" className="form-select" value={currency} onChange={(event) => setCurrency(event.target.value)}>
                {SUPPORTED_CURRENCIES.map((code) => (
                  <option key={code} value={code}>{code}</option>
                ))}
              </select>
            </div>
            <div className="col-md-4">
              <label className="form-label mb-1" htmlFor="paymentMethodSelect">Payment Method <small>(Enkola y'Okuliipira)</small></label>
              <select id="paymentMethodSelect" className="form-select" value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)}>
                {PAYMENT_METHODS.map((method) => (
                  <option key={method.value} value={method.value}>{method.label}</option>
                ))}
              </select>
            </div>
            <div className="col-md-4">
              <small className="d-block">Rate Source: {ratesSource === 'live' ? 'Live API' : 'Fallback'}</small>
              <small className="d-block">Updated: {ratesUpdatedAt || 'loading...'}</small>
              <small className="d-block">1 USD = {rates[currency]?.toFixed(currency === 'UGX' ? 0 : 4)} {currency}</small>
              <small className="d-block">Cart Source: {cartSource === 'api' ? 'API' : 'Local Storage'}</small>
            </div>
          </div>
        </div>

        <ul className="list-group mb-3">
          {convertedItems.map(item => (
            <li className="list-group-item d-flex justify-content-between align-items-center" style={{background: 'var(--surface-soft)', color: 'var(--text)'}} key={item.id}>
              <span>{item.name} <span>x{item.quantity}</span></span>
              <span>{formatAmount(item.convertedLineTotal, currency)}</span>
            </li>
          ))}
        </ul>

        <div className="card p-3 mb-3 text-start shadow-sm" style={{background: 'var(--surface-soft)', color: 'var(--text)'}}>
          <h5 className="mb-1">Order Summary</h5>
          <small className="d-block mb-2">Ekifuufu ky'Omutendera</small>
          <div className="d-flex justify-content-between"><span>Items <small>(Ebintu)</small></span><span>{cartItems.length}</span></div>
          <div className="d-flex justify-content-between"><span>Quantity <small>(Omuwendo)</small></span><span>{cartItems.reduce((sum, item) => sum + item.quantity, 0)}</span></div>
          <div className="d-flex justify-content-between"><span>Method <small>(Enkola)</small></span><span>{selectedMethodLabel}</span></div>
          <hr className="my-2" />
          <h4 className="mb-0">Total: {formatAmount(convertedTotal, currency)}<br /><small className="fw-normal react-subtle" style={{fontSize: '0.65rem'}}>Enteeresa Yonna</small></h4>
        </div>

        <button className="btn btn-success mt-3" onClick={handlePay} disabled={paying}>
          {paying ? <>Processing...<br /><small style={{fontWeight: 'normal', opacity: 0.85}}>Tukola...</small></> : <>{`Pay (${selectedMethodLabel})`}<br /><small style={{fontWeight: 'normal', opacity: 0.85}}>Liipira</small></>}
        </button>
        {result && (
          <div className="mt-3 alert alert-info">
            {result.error ? result.error : (result.uiSummary || result.message)}
          </div>
        )}
      </>
    );
  }

  return (
    <div className="text-center p-2">
      <h2>Your Cart</h2>
      <small className="d-block mb-2 react-muted">Ekikapu Kyo</small>
      {cartContent}
      {!loadingCart && cartError && (
        <div className="mt-3 alert alert-warning">
          {cartError}
        </div>
      )}
    </div>
  );
}

export default Cart;
