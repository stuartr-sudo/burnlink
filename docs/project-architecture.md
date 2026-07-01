# Atelier Bristle Architecture

```mermaid
flowchart LR
  visitor["Customer browser"] --> storefront["FastAPI storefront /"]
  visitor --> api["FastAPI JSON APIs"]
  admin["Operator browser"] --> dashboard["FastAPI dashboard /dashboard"]

  storefront --> jinja["Jinja templates"]
  dashboard --> jinja
  jinja --> static_assets["Static assets"]
  fal["Fal image generation"] --> static_assets

  api --> repo["CommerceRepository"]
  dashboard --> repo
  repo --> supabase["Supabase REST API"]

  supabase --> products["products"]
  supabase --> customers["customers"]
  supabase --> orders["orders"]
  supabase --> order_items["order_items"]
  supabase --> suppliers["suppliers"]
  supabase --> messages["customer_messages"]
  supabase --> sequences["email_sequences"]
  supabase --> inventory["inventory_movements"]

  vercel["Vercel Python runtime"] --> app_py["app.py"]
  app_py --> fastapi["main.py FastAPI app"]
  fastapi --> storefront
  fastapi --> dashboard
  fastapi --> api
```

```mermaid
erDiagram
  SUPPLIERS ||--o{ PRODUCTS : supplies
  PRODUCTS ||--o{ ORDER_ITEMS : purchased_as
  PRODUCTS ||--o{ INVENTORY_MOVEMENTS : records
  CUSTOMERS ||--o{ ORDERS : places
  CUSTOMERS ||--o{ CUSTOMER_MESSAGES : receives
  ORDERS ||--o{ ORDER_ITEMS : contains
  EMAIL_SEQUENCES ||--o{ CUSTOMER_MESSAGES : queues

  SUPPLIERS {
    uuid id PK
    text name
    text contact_name
    text email
    text region
    int lead_time_days
  }

  PRODUCTS {
    uuid id PK
    uuid supplier_id FK
    text sku
    text slug
    numeric price
    int inventory_count
    int reorder_point
  }

  CUSTOMERS {
    uuid id PK
    text email
    text first_name
    text last_name
    text preferred_medium
  }

  ORDERS {
    uuid id PK
    uuid customer_id FK
    text status
    numeric total
    text channel
  }

  ORDER_ITEMS {
    uuid id PK
    uuid order_id FK
    uuid product_id FK
    int quantity
    numeric unit_price
  }

  CUSTOMER_MESSAGES {
    uuid id PK
    uuid customer_id FK
    text email
    text subject
    text status
    text sequence_key
  }

  EMAIL_SEQUENCES {
    uuid id PK
    text key
    text trigger
    boolean active
    int touch_count
  }
```

## Runtime Flow

1. Customers browse `/`, add products to the browser cart and submit a reservation through `/api/orders`.
2. FastAPI validates the cart, reads current inventory and writes customer, order, order item and queued communication records to Supabase.
3. The dashboard reads aggregate order, product, supplier, message and sequence data through the same server-side repository.
4. Vercel serves `app.py`, which imports the FastAPI app from `main.py`.
5. Fal-generated imagery is stored locally in `static/generated/` and served by FastAPI static files.
