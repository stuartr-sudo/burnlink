# Atelier Bristle

High-end artist paint brush ecommerce site with a compact FastAPI storefront, generated Fal imagery, Supabase-backed commerce data and an internal operator dashboard.

## What Is Included

- Storefront at `/` with product catalogue, cart, order reservation, newsletter signup and customer message capture.
- Dashboard at `/dashboard` for sales, inventory, suppliers, customer communications and email sequences.
- Supabase migration at `supabase/migrations/20260630001241_brush_house_schema.sql`.
- Local Fal-generated image assets under `static/generated/`.
- Vercel Python entrypoint through `app.py`.

## Local Run

```bash
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 9999
```

Open `http://localhost:9999`.

## Environment

The app runs with demo seed data when Supabase is not configured. Set these for production:

```bash
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-server-only-service-role-key
ADMIN_USERNAME=atelier
ADMIN_PASSWORD=choose-a-long-password
```

Keep `SUPABASE_SERVICE_ROLE_KEY` server-side only. Do not expose it with a `NEXT_PUBLIC_` style variable or in browser JavaScript.

## Supabase

Apply the migration after linking a Supabase project:

```bash
supabase link --project-ref your-project-ref
supabase db push
```

The migration enables RLS on every public table, grants public read access only to active products and keeps customers, orders, suppliers, inventory movements and communications limited to the service role.

## Vercel

This repo already has `app.py` exporting the FastAPI `app`, which Vercel's Python runtime can load from the project root. Add the environment variables above to Vercel before promoting a production deployment.

## Architecture

See `docs/project-architecture.md` for the visual system map and table relationships.
