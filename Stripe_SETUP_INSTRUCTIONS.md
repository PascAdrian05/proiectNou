# Configurare Stripe pentru plăți

Pentru a activa plățile cu Stripe, adaugă următoarele în fișierul `backend/.env`:

## 1. Stripe API Key
- Mergi la https://dashboard.stripe.com/test/apikeys
- Copie `Secret key` (începe cu `sk_test_...`)

## 2. Stripe Webhook Secret
- Mergi la https://dashboard.stripe.com/test/webhooks
- Adaugă endpoint: `http://localhost:8000/api/v1/billing/stripe/webhook`
- După salvare, copie `Signing secret` (începe cu `whsec_...`)

## 3. Stripe Price IDs (produse)
- Mergi la https://dashboard.stripe.com/test/products
- Creează 2 produse abonament lunar:
  - "Basic" -> copie `price_xxx`
  - "Pro" -> copie `price_xxx`

## Adaugă în `backend/.env`:
```
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_BASIC_ID=price_xxx_basic
STRIPE_PRICE_PRO_ID=price_xxx_pro
```

După ce adaugi datele, spune-mi să repornesc backend-ul!