# Mango Orchard Website

A single-page static website for a mango retail/wholesale business in Pakistan. Plain HTML/CSS/JS — no build step, no dependencies.

## Structure

```
mango-orchard-website/
├── index.html       # All page content/sections
├── css/style.css     # Styling
├── js/main.js         # Mobile nav + WhatsApp order form
├── assets/favicon.svg
└── README.md
```

## Before you launch

Update these placeholders with real business details:

- **WhatsApp number** — `js/main.js`, the `WHATSAPP_NUMBER` constant, and the WhatsApp link in `index.html` (`#contact` section)
- **Phone number** — `tel:` link and displayed number in `index.html`
- **Email** — `mailto:` link in `index.html`
- **Address** — the "Orchard & Dispatch" card in `index.html`
- Pricing, crate sizes, and delivery cities can be added to the "Order" section once finalized

## Running locally

Any static file server works, e.g.:

```bash
cd mango-orchard-website
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Deploying

This is a static site, so it can be hosted for free on GitHub Pages, Netlify, Vercel, or Cloudflare Pages — just point the host at this folder.
