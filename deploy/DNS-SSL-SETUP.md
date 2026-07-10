# Domain & SSL Setup

Production URL: https://kistie-store-production.up.railway.app
Domain: kistie-store-production.up.railway.app
Framework: react

## SSL
SSL/TLS is automatic on Vercel, Railway, and Fly.io custom domains.

## Stripe Webhook (production)
Update webhook URL to: `https://kistie-store-production.up.railway.app/api/stripe/webhook`

## Verification
```bash
curl https://kistie-store-production.up.railway.app/api/health
```
Run readiness from Stripe Installer after deploy.
