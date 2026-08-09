// Node.js Express server for payment integrations
const path = require('node:path');
require('dotenv').config({ path: path.join(__dirname, '.env') });
const express = require('express');
const cors = require('cors');
const axios = require('axios');

const app = express();
app.disable('x-powered-by');

const allowedOrigins = new Set(
  (process.env.PAYMENTS_ALLOWED_ORIGINS || 'http://127.0.0.1:8000,http://localhost:8000')
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean),
);

app.use(cors({
  origin(origin, callback) {
    if (!origin || allowedOrigins.has(origin)) {
      return callback(null, true);
    }
    return callback(new Error('CORS blocked: origin is not allowed'));
  },
  credentials: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Internal-Key'],
}));
app.use(express.json());

// ── Pesapal v3 configuration ──────────────────────────────────────────────────
const PESAPAL_BASE =
  process.env.PESAPAL_ENV === 'production'
    ? 'https://pay.pesapal.com/v3'
    : 'https://cybqa.pesapal.com/pesapalv3';

const CONSUMER_KEY    = process.env.PESAPAL_CONSUMER_KEY;
const CONSUMER_SECRET = process.env.PESAPAL_CONSUMER_SECRET;
const DJANGO_BASE     = process.env.DJANGO_BASE || 'http://127.0.0.1:8000';
const IPN_URL         = process.env.IPN_URL || 'http://localhost:5000/api/pay/ipn';
const INTERNAL_KEY    = process.env.INTERNAL_WEBHOOK_KEY;

if (!INTERNAL_KEY) {
  throw new Error('INTERNAL_WEBHOOK_KEY must be set before starting payments service.');
}

// ── Pesapal helpers ───────────────────────────────────────────────────────────
async function getPesapalToken() {
  const res = await axios.post(
    `${PESAPAL_BASE}/api/Auth/RequestToken`,
    { consumer_key: CONSUMER_KEY, consumer_secret: CONSUMER_SECRET },
    { headers: { 'Content-Type': 'application/json', Accept: 'application/json' } },
  );
  return res.data.token;
}

async function registerIPN(token) {
  const res = await axios.post(
    `${PESAPAL_BASE}/api/URLSetup/RegisterIPN`,
    { url: IPN_URL, ipn_notification_type: 'POST' },
    {
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        Authorization: `Bearer ${token}`,
      },
    },
  );
  return res.data.ipn_id;
}

// ── Pesapal sandbox payment endpoint ─────────────────────────────────────────
app.post('/api/pay/pesapal', async (req, res) => {
  if (!CONSUMER_KEY || !CONSUMER_SECRET) {
    return res.status(503).json({
      error: 'Pesapal credentials not configured. Copy payments/.env.example to .env and add your sandbox keys.',
    });
  }

  const { order_ref, amount, currency, customer } = req.body;
  if (!order_ref || !amount) {
    return res.status(400).json({ error: 'order_ref and amount are required.' });
  }

  try {
    const token  = await getPesapalToken();
    const ipn_id = await registerIPN(token);

    const nameParts = (customer?.name || 'Customer').split(' ');
    const orderRes = await axios.post(
      `${PESAPAL_BASE}/api/Transactions/SubmitOrderRequest`,
      {
        id: order_ref,
        currency: currency || 'USD',
        amount: Number(Number(amount).toFixed(2)),
        description: `Kistie Store — order ${order_ref}`,
        callback_url: `${DJANGO_BASE}/order/pesapal/callback/?order_ref=${order_ref}`,
        notification_id: ipn_id,
        billing_address: {
          email_address: customer?.email || 'customer@kistiestore.com',
          phone_number:  customer?.phone || '',
          country_code:  'UG',
          first_name:    nameParts[0] || 'Customer',
          last_name:     nameParts.slice(1).join(' ') || 'Customer',
        },
      },
      {
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          Authorization: `Bearer ${token}`,
        },
      },
    );

    const { redirect_url, order_tracking_id } = orderRes.data;
    return res.json({ redirect_url, order_tracking_id });
  } catch (err) {
    const detail = err.response?.data || err.message;
    console.error('[Pesapal] submit order failed:', detail);
    return res.status(502).json({ error: 'Pesapal request failed.', detail });
  }
});

// ── Pesapal IPN (webhook) ─────────────────────────────────────────────────────
// Pesapal POSTs here after a payment is completed/failed.
app.post('/api/pay/ipn', async (req, res) => {
  const { OrderTrackingId, OrderMerchantReference, OrderNotificationType } = req.body;
  if (!OrderTrackingId) {
    return res.status(400).json({ error: 'Missing OrderTrackingId' });
  }

  try {
    const token = await getPesapalToken();
    const statusRes = await axios.get(
      `${PESAPAL_BASE}/api/Transactions/GetTransactionStatus?orderTrackingId=${OrderTrackingId}`,
      { headers: { Accept: 'application/json', Authorization: `Bearer ${token}` } },
    );

    const { payment_status_description } = statusRes.data;
    const djangoStatus =
      payment_status_description === 'Completed' ? 'payment_confirmed' : 'payment_failed';

    // Tell Django to update the order status
    await axios.post(
      `${DJANGO_BASE}/api/internal/order-status/`,
      { order_ref: OrderMerchantReference, status: djangoStatus, tracking_id: OrderTrackingId },
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Internal-Key': INTERNAL_KEY,
        },
      },
    );

    // Pesapal requires this exact JSON shape in the IPN response
    return res.json({
      orderNotificationType: OrderNotificationType,
      orderTrackingId: OrderTrackingId,
      orderMerchantReference: OrderMerchantReference,
      status: '200',
    });
  } catch (err) {
    console.error('[IPN] processing failed:', err.response?.data || err.message);
    return res.status(500).json({ error: 'IPN processing failed.' });
  }
});

// ── Generic checkout endpoint (optional frontend client can call this) ───────
app.post('/api/pay/checkout', (req, res) => {
  res.json({
    message:
      'Use /api/pay/pesapal for live gateway redirect. Other payment rails remain method-specific and can be enabled as separate integrations.',
  });
});

// ── Additional provider endpoints (reserved for future integrations) ─────────
app.post('/api/pay/mtn',    (_req, res) => res.json({ message: 'MTN Mobile Money integration coming soon.' }));
app.post('/api/pay/airtel', (_req, res) => res.json({ message: 'Airtel Money integration coming soon.' }));
app.post('/api/pay/daraja', (_req, res) => res.json({ message: 'Daraja (M-Pesa) integration coming soon.' }));
app.post('/api/pay/klasha', (_req, res) => res.json({ message: 'Klasha integration coming soon.' }));

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Payments server running on port ${PORT}`);
  console.log(`Pesapal env: ${process.env.PESAPAL_ENV || 'sandbox (default)'}`);
});
