create extension if not exists pgcrypto;

create table public.suppliers (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  contact_name text not null default '',
  email text not null default '',
  region text not null default '',
  lead_time_days integer not null default 30 check (lead_time_days >= 0),
  minimum_order_value numeric(10,2) not null default 0 check (minimum_order_value >= 0),
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.products (
  id uuid primary key default gen_random_uuid(),
  supplier_id uuid references public.suppliers(id) on delete set null,
  sku text not null unique,
  slug text not null unique,
  name text not null,
  category text not null,
  brush_type text not null,
  bristle_material text not null default '',
  handle_material text not null default '',
  price numeric(10,2) not null check (price >= 0),
  inventory_count integer not null default 0 check (inventory_count >= 0),
  reorder_point integer not null default 0 check (reorder_point >= 0),
  image_url text not null default '',
  description text not null default '',
  ideal_for text not null default '',
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.customers (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  first_name text not null default '',
  last_name text not null default '',
  phone text not null default '',
  preferred_medium text not null default 'email',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint customers_email_format check (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$')
);

create table public.orders (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid references public.customers(id) on delete set null,
  status text not null default 'pending_payment'
    check (status in ('pending_payment', 'paid', 'fulfilled', 'cancelled', 'refunded')),
  subtotal numeric(10,2) not null default 0 check (subtotal >= 0),
  shipping numeric(10,2) not null default 0 check (shipping >= 0),
  total numeric(10,2) not null default 0 check (total >= 0),
  currency char(3) not null default 'USD',
  channel text not null default 'site',
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.orders(id) on delete cascade,
  product_id uuid references public.products(id) on delete set null,
  sku text not null,
  product_name text not null,
  quantity integer not null check (quantity > 0),
  unit_price numeric(10,2) not null check (unit_price >= 0),
  created_at timestamptz not null default now()
);

create table public.customer_messages (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid references public.customers(id) on delete set null,
  email text not null,
  subject text not null,
  body text not null,
  channel text not null default 'site',
  status text not null default 'open' check (status in ('open', 'queued', 'sent', 'closed')),
  sequence_key text,
  created_at timestamptz not null default now()
);

create table public.email_sequences (
  id uuid primary key default gen_random_uuid(),
  key text not null unique,
  name text not null,
  "trigger" text not null,
  active boolean not null default true,
  cadence_days integer[] not null default '{}',
  touch_count integer not null default 0 check (touch_count >= 0),
  template_subject text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.inventory_movements (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references public.products(id) on delete cascade,
  quantity_delta integer not null,
  reason text not null,
  note text not null default '',
  created_at timestamptz not null default now()
);

create index products_active_category_idx on public.products (active, category, name);
create index products_supplier_idx on public.products (supplier_id);
create index orders_created_at_idx on public.orders (created_at desc);
create index orders_customer_idx on public.orders (customer_id);
create index order_items_order_idx on public.order_items (order_id);
create index customer_messages_created_at_idx on public.customer_messages (created_at desc);
create index customer_messages_status_idx on public.customer_messages (status);
create index inventory_movements_product_idx on public.inventory_movements (product_id, created_at desc);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger suppliers_set_updated_at
before update on public.suppliers
for each row execute function public.set_updated_at();

create trigger products_set_updated_at
before update on public.products
for each row execute function public.set_updated_at();

create trigger customers_set_updated_at
before update on public.customers
for each row execute function public.set_updated_at();

create trigger orders_set_updated_at
before update on public.orders
for each row execute function public.set_updated_at();

create trigger email_sequences_set_updated_at
before update on public.email_sequences
for each row execute function public.set_updated_at();

revoke execute on function public.set_updated_at() from public, anon, authenticated;

alter table public.suppliers enable row level security;
alter table public.products enable row level security;
alter table public.customers enable row level security;
alter table public.orders enable row level security;
alter table public.order_items enable row level security;
alter table public.customer_messages enable row level security;
alter table public.email_sequences enable row level security;
alter table public.inventory_movements enable row level security;

revoke all on table
  public.suppliers,
  public.products,
  public.customers,
  public.orders,
  public.order_items,
  public.customer_messages,
  public.email_sequences,
  public.inventory_movements
from anon, authenticated;

grant select on table public.products to anon, authenticated;

grant select, insert, update, delete on table
  public.suppliers,
  public.products,
  public.customers,
  public.orders,
  public.order_items,
  public.customer_messages,
  public.email_sequences,
  public.inventory_movements
to service_role;

grant usage, select on all sequences in schema public to service_role;

create policy "products are publicly readable when active"
on public.products
for select
to anon, authenticated
using (active = true);

create policy "service role can manage suppliers"
on public.suppliers
for all
to service_role
using (true)
with check (true);

create policy "service role can manage products"
on public.products
for all
to service_role
using (true)
with check (true);

create policy "service role can manage customers"
on public.customers
for all
to service_role
using (true)
with check (true);

create policy "service role can manage orders"
on public.orders
for all
to service_role
using (true)
with check (true);

create policy "service role can manage order items"
on public.order_items
for all
to service_role
using (true)
with check (true);

create policy "service role can manage customer messages"
on public.customer_messages
for all
to service_role
using (true)
with check (true);

create policy "service role can manage email sequences"
on public.email_sequences
for all
to service_role
using (true)
with check (true);

create policy "service role can manage inventory movements"
on public.inventory_movements
for all
to service_role
using (true)
with check (true);

insert into public.suppliers (
  id,
  name,
  contact_name,
  email,
  region,
  lead_time_days,
  minimum_order_value,
  notes
) values
  (
    '11111111-1111-4111-8111-111111111111',
    'Kumano Atelier Works',
    'Mika Sato',
    'studio@kumano.example',
    'Hiroshima, JP',
    42,
    2500,
    'Hand-shaped detail and watercolor brushes.'
  ),
  (
    '22222222-2222-4222-8222-222222222222',
    'Florentine Ferrules',
    'Luca Bianchi',
    'orders@florentine.example',
    'Florence, IT',
    35,
    1800,
    'Nickel-plated brass ferrules and lacquered handles.'
  ),
  (
    '33333333-3333-4333-8333-333333333333',
    'Yorkshire Bristle Co.',
    'Amelia Hart',
    'supply@yorkshirebristle.example',
    'Leeds, UK',
    28,
    1400,
    'Natural hog bristle and oil-painting flats.'
  )
on conflict (id) do update set
  name = excluded.name,
  contact_name = excluded.contact_name,
  email = excluded.email,
  region = excluded.region,
  lead_time_days = excluded.lead_time_days,
  minimum_order_value = excluded.minimum_order_value,
  notes = excluded.notes;

insert into public.products (
  id,
  supplier_id,
  sku,
  slug,
  name,
  category,
  brush_type,
  bristle_material,
  handle_material,
  price,
  inventory_count,
  reorder_point,
  image_url,
  description,
  ideal_for,
  active
) values
  (
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1',
    '11111111-1111-4111-8111-111111111111',
    'AB-RND-06',
    'reserve-round-06',
    'Reserve Round 06',
    'Watercolor',
    'Pointed round',
    'Kolinsky-style sable blend',
    'Balanced lacquered birch',
    88,
    18,
    8,
    '/static/generated/product-round.png',
    'A responsive belly with a needle point for washes, lettering and controlled edges.',
    'Watercolor layers, gouache detail, ink linework',
    true
  ),
  (
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2',
    '33333333-3333-4333-8333-333333333333',
    'AB-FLT-12',
    'heritage-flat-12',
    'Heritage Flat 12',
    'Oil',
    'Long flat',
    'Interlocked hog bristle',
    'Walnut-stained beech',
    112,
    7,
    10,
    '/static/generated/product-flat.png',
    'Built for confident oil strokes, crisp planes and heavy-body paint control.',
    'Oil blocking, impasto edges, acrylic grounds',
    true
  ),
  (
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa3',
    '22222222-2222-4222-8222-222222222222',
    'AB-FAN-04',
    'velatura-fan-04',
    'Velatura Fan 04',
    'Blending',
    'Fan blender',
    'Soft synthetic squirrel',
    'Lacquered cedar',
    76,
    26,
    9,
    '/static/generated/product-fan.png',
    'Feathered shape for veils, clouds, glazing transitions and dry blending.',
    'Soft edges, glazes, portrait transitions',
    true
  ),
  (
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa4',
    '11111111-1111-4111-8111-111111111111',
    'AB-LNR-02',
    'linea-liner-02',
    'Linea Liner 02',
    'Detail',
    'Fine liner',
    'Elastic synthetic sable',
    'Short polished maple',
    64,
    11,
    8,
    '/static/generated/product-liner.png',
    'A precise liner for signatures, botanical marks and final highlights.',
    'Miniature work, botanical detail, signatures',
    true
  )
on conflict (sku) do update set
  supplier_id = excluded.supplier_id,
  slug = excluded.slug,
  name = excluded.name,
  category = excluded.category,
  brush_type = excluded.brush_type,
  bristle_material = excluded.bristle_material,
  handle_material = excluded.handle_material,
  price = excluded.price,
  inventory_count = excluded.inventory_count,
  reorder_point = excluded.reorder_point,
  image_url = excluded.image_url,
  description = excluded.description,
  ideal_for = excluded.ideal_for,
  active = excluded.active;

insert into public.email_sequences (
  key,
  name,
  "trigger",
  active,
  cadence_days,
  touch_count,
  template_subject
) values
  (
    'artist_welcome',
    'Artist welcome',
    'newsletter_signup',
    true,
    array[0, 3, 10],
    3,
    'Choosing a brush that keeps its point'
  ),
  (
    'post_purchase_care',
    'Post-purchase care',
    'order_created',
    true,
    array[0, 7, 30],
    3,
    'Care notes for your new brush'
  ),
  (
    'low_stock_private_offer',
    'Low-stock private offer',
    'inventory_below_reorder',
    false,
    array[0, 2],
    2,
    'A small batch is nearly gone'
  )
on conflict (key) do update set
  name = excluded.name,
  "trigger" = excluded."trigger",
  active = excluded.active,
  cadence_days = excluded.cadence_days,
  touch_count = excluded.touch_count,
  template_subject = excluded.template_subject;
