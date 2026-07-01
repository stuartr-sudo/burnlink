import hmac
import json
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request


app = FastAPI(title="Atelier Bristle", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
security = HTTPBasic(auto_error=False)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "atelier")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def money(value: Any) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0
    return f"${amount:,.2f}"


templates.env.filters["money"] = money


SUPPLIERS = [
    {
        "id": "11111111-1111-4111-8111-111111111111",
        "name": "Kumano Atelier Works",
        "contact_name": "Mika Sato",
        "email": "studio@kumano.example",
        "region": "Hiroshima, JP",
        "lead_time_days": 42,
        "minimum_order_value": 2500,
        "notes": "Hand-shaped detail and watercolor brushes.",
    },
    {
        "id": "22222222-2222-4222-8222-222222222222",
        "name": "Florentine Ferrules",
        "contact_name": "Luca Bianchi",
        "email": "orders@florentine.example",
        "region": "Florence, IT",
        "lead_time_days": 35,
        "minimum_order_value": 1800,
        "notes": "Nickel-plated brass ferrules and lacquered handles.",
    },
    {
        "id": "33333333-3333-4333-8333-333333333333",
        "name": "Yorkshire Bristle Co.",
        "contact_name": "Amelia Hart",
        "email": "supply@yorkshirebristle.example",
        "region": "Leeds, UK",
        "lead_time_days": 28,
        "minimum_order_value": 1400,
        "notes": "Natural hog bristle and oil-painting flats.",
    },
]

PRODUCTS = [
    {
        "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1",
        "sku": "AB-RND-06",
        "slug": "reserve-round-06",
        "name": "Reserve Round 06",
        "category": "Watercolor",
        "brush_type": "Pointed round",
        "bristle_material": "Kolinsky-style sable blend",
        "handle_material": "Balanced lacquered birch",
        "price": 88,
        "inventory_count": 18,
        "reorder_point": 8,
        "supplier_id": SUPPLIERS[0]["id"],
        "supplier_name": SUPPLIERS[0]["name"],
        "lead_time_days": SUPPLIERS[0]["lead_time_days"],
        "image_url": "/static/generated/product-round.png",
        "description": "A responsive belly with a needle point for washes, lettering and controlled edges.",
        "ideal_for": "Watercolor layers, gouache detail, ink linework",
        "active": True,
    },
    {
        "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2",
        "sku": "AB-FLT-12",
        "slug": "heritage-flat-12",
        "name": "Heritage Flat 12",
        "category": "Oil",
        "brush_type": "Long flat",
        "bristle_material": "Interlocked hog bristle",
        "handle_material": "Walnut-stained beech",
        "price": 112,
        "inventory_count": 7,
        "reorder_point": 10,
        "supplier_id": SUPPLIERS[2]["id"],
        "supplier_name": SUPPLIERS[2]["name"],
        "lead_time_days": SUPPLIERS[2]["lead_time_days"],
        "image_url": "/static/generated/product-flat.png",
        "description": "Built for confident oil strokes, crisp planes and heavy-body paint control.",
        "ideal_for": "Oil blocking, impasto edges, acrylic grounds",
        "active": True,
    },
    {
        "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa3",
        "sku": "AB-FAN-04",
        "slug": "velatura-fan-04",
        "name": "Velatura Fan 04",
        "category": "Blending",
        "brush_type": "Fan blender",
        "bristle_material": "Soft synthetic squirrel",
        "handle_material": "Lacquered cedar",
        "price": 76,
        "inventory_count": 26,
        "reorder_point": 9,
        "supplier_id": SUPPLIERS[1]["id"],
        "supplier_name": SUPPLIERS[1]["name"],
        "lead_time_days": SUPPLIERS[1]["lead_time_days"],
        "image_url": "/static/generated/product-fan.png",
        "description": "Feathered shape for veils, clouds, glazing transitions and dry blending.",
        "ideal_for": "Soft edges, glazes, portrait transitions",
        "active": True,
    },
    {
        "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa4",
        "sku": "AB-LNR-02",
        "slug": "linea-liner-02",
        "name": "Linea Liner 02",
        "category": "Detail",
        "brush_type": "Fine liner",
        "bristle_material": "Elastic synthetic sable",
        "handle_material": "Short polished maple",
        "price": 64,
        "inventory_count": 11,
        "reorder_point": 8,
        "supplier_id": SUPPLIERS[0]["id"],
        "supplier_name": SUPPLIERS[0]["name"],
        "lead_time_days": SUPPLIERS[0]["lead_time_days"],
        "image_url": "/static/generated/product-liner.png",
        "description": "A precise liner for signatures, botanical marks and final highlights.",
        "ideal_for": "Miniature work, botanical detail, signatures",
        "active": True,
    },
]

EMAIL_SEQUENCES = [
    {
        "key": "artist_welcome",
        "name": "Artist welcome",
        "trigger": "newsletter_signup",
        "active": True,
        "cadence_days": [0, 3, 10],
        "touch_count": 3,
        "template_subject": "Choosing a brush that keeps its point",
    },
    {
        "key": "post_purchase_care",
        "name": "Post-purchase care",
        "trigger": "order_created",
        "active": True,
        "cadence_days": [0, 7, 30],
        "touch_count": 3,
        "template_subject": "Care notes for your new brush",
    },
    {
        "key": "low_stock_private_offer",
        "name": "Low-stock private offer",
        "trigger": "inventory_below_reorder",
        "active": False,
        "cadence_days": [0, 2],
        "touch_count": 2,
        "template_subject": "A small batch is nearly gone",
    },
]

DEMO_ORDERS = [
    {
        "id": "BL-1048",
        "created_at": "2026-06-28T10:12:00+00:00",
        "status": "paid",
        "customer_email": "mara@example.com",
        "subtotal": 264,
        "shipping": 12,
        "total": 276,
        "currency": "USD",
        "order_items": [
            {"sku": "AB-RND-06", "product_name": "Reserve Round 06", "quantity": 2, "unit_price": 88},
            {"sku": "AB-LNR-02", "product_name": "Linea Liner 02", "quantity": 1, "unit_price": 64},
        ],
    },
    {
        "id": "BL-1047",
        "created_at": "2026-06-27T15:31:00+00:00",
        "status": "pending_payment",
        "customer_email": "jules@example.com",
        "subtotal": 188,
        "shipping": 12,
        "total": 200,
        "currency": "USD",
        "order_items": [
            {"sku": "AB-FLT-12", "product_name": "Heritage Flat 12", "quantity": 1, "unit_price": 112},
            {"sku": "AB-FAN-04", "product_name": "Velatura Fan 04", "quantity": 1, "unit_price": 76},
        ],
    },
]

DEMO_MESSAGES = [
    {
        "id": "msg-demo-1",
        "created_at": "2026-06-29T09:20:00+00:00",
        "email": "studio@northlight.example",
        "subject": "Restock request",
        "body": "Please alert me when Heritage Flat 12 returns above ten units.",
        "channel": "site",
        "status": "open",
        "sequence_key": "low_stock_private_offer",
    },
    {
        "id": "msg-demo-2",
        "created_at": "2026-06-28T18:05:00+00:00",
        "email": "mara@example.com",
        "subject": "Care note queued",
        "body": "Post-purchase care sequence queued.",
        "channel": "email_sequence",
        "status": "queued",
        "sequence_key": "post_purchase_care",
    },
]


class CartItem(BaseModel):
    slug: str
    quantity: int = Field(default=1, ge=1, le=20)


class CustomerInput(BaseModel):
    email: str
    first_name: str = ""
    last_name: str = ""
    phone: str = ""


class OrderRequest(BaseModel):
    customer: CustomerInput
    items: list[CartItem]
    notes: str = ""


class NewsletterRequest(BaseModel):
    email: str
    first_name: str = ""


class CustomerMessageRequest(BaseModel):
    email: str
    subject: str = Field(min_length=2, max_length=160)
    body: str = Field(min_length=2, max_length=2000)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if not EMAIL_RE.match(cleaned):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    return cleaned


def inventory_status(product: dict[str, Any]) -> str:
    count = int(product.get("inventory_count") or 0)
    reorder = int(product.get("reorder_point") or 0)
    if count <= 0:
        return "Out"
    if count <= reorder:
        return "Low"
    if count <= reorder * 2:
        return "Limited"
    return "In stock"


def public_product(product: dict[str, Any]) -> dict[str, Any]:
    item = dict(product)
    item["price"] = float(item.get("price") or 0)
    item["inventory_count"] = int(item.get("inventory_count") or 0)
    item["reorder_point"] = int(item.get("reorder_point") or 0)
    item["status"] = inventory_status(item)
    return item


class CommerceRepository:
    def __init__(self) -> None:
        self.supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        self.supabase_key = (
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_SECRET_KEY")
            or ""
        )
        self.last_error = ""

    @property
    def configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def source_label(self) -> str:
        return "Supabase" if self.configured and not self.last_error else "Demo seed data"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        body: Any = None,
        prefer: str = "return=representation",
    ) -> Any:
        if not self.configured:
            raise RuntimeError("Supabase is not configured")

        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{self.supabase_url}/rest/v1/{path}{query}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Prefer": prefer,
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise HTTPException(
                status_code=502,
                detail=f"Supabase request failed: {detail or exc.reason}",
            ) from exc
        except urllib.error.URLError as exc:
            raise HTTPException(status_code=502, detail="Supabase is unavailable.") from exc

        if not payload:
            return None
        return json.loads(payload)

    def products(self) -> list[dict[str, Any]]:
        if not self.configured:
            return [public_product(product) for product in PRODUCTS]

        rows = self.request(
            "GET",
            "products",
            params={
                "select": "*,suppliers(name,lead_time_days)",
                "active": "eq.true",
                "order": "category.asc,name.asc",
            },
        )
        products: list[dict[str, Any]] = []
        for row in rows or []:
            supplier = row.get("suppliers") or {}
            row["supplier_name"] = supplier.get("name", "")
            row["lead_time_days"] = supplier.get("lead_time_days", "")
            products.append(public_product(row))
        return products

    def suppliers(self) -> list[dict[str, Any]]:
        if not self.configured:
            return SUPPLIERS
        return self.request("GET", "suppliers", params={"select": "*", "order": "name.asc"}) or []

    def email_sequences(self) -> list[dict[str, Any]]:
        if not self.configured:
            return EMAIL_SEQUENCES
        return self.request("GET", "email_sequences", params={"select": "*", "order": "name.asc"}) or []

    def orders(self) -> list[dict[str, Any]]:
        if not self.configured:
            return DEMO_ORDERS
        rows = self.request(
            "GET",
            "orders",
            params={
                "select": "*,customers(email),order_items(*)",
                "order": "created_at.desc",
                "limit": "25",
            },
        )
        orders: list[dict[str, Any]] = []
        for row in rows or []:
            customer = row.get("customers") or {}
            row["customer_email"] = customer.get("email", "")
            orders.append(row)
        return orders

    def messages(self) -> list[dict[str, Any]]:
        if not self.configured:
            return DEMO_MESSAGES
        return self.request(
            "GET",
            "customer_messages",
            params={"select": "*", "order": "created_at.desc", "limit": "25"},
        ) or []

    def upsert_customer(self, customer: CustomerInput) -> dict[str, Any]:
        email = normalize_email(customer.email)
        body = {
            "email": email,
            "first_name": customer.first_name.strip(),
            "last_name": customer.last_name.strip(),
            "phone": customer.phone.strip(),
            "preferred_medium": "email",
        }
        rows = self.request(
            "POST",
            "customers",
            params={"on_conflict": "email"},
            body=body,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return rows[0] if isinstance(rows, list) and rows else {"email": email}

    def create_order(self, payload: OrderRequest) -> dict[str, Any]:
        email = normalize_email(payload.customer.email)
        if not payload.items:
            raise HTTPException(status_code=422, detail="Add at least one brush to the cart.")

        products_by_slug = {product["slug"]: product for product in self.products()}
        order_lines = []
        subtotal = 0.0

        for item in payload.items:
            product = products_by_slug.get(item.slug)
            if not product:
                raise HTTPException(status_code=404, detail=f"Unknown product: {item.slug}")
            if int(product.get("inventory_count") or 0) < item.quantity:
                raise HTTPException(status_code=409, detail=f"{product['name']} is low on inventory.")
            unit_price = float(product["price"])
            subtotal += unit_price * item.quantity
            order_lines.append(
                {
                    "product": product,
                    "quantity": item.quantity,
                    "unit_price": unit_price,
                }
            )

        shipping = 0 if subtotal >= 250 else 12
        total = subtotal + shipping

        if not self.configured:
            return {
                "id": f"DEMO-{secrets.token_hex(3).upper()}",
                "customer_email": email,
                "status": "pending_payment",
                "subtotal": subtotal,
                "shipping": shipping,
                "total": total,
                "currency": "USD",
                "source": "demo",
            }

        customer = self.upsert_customer(payload.customer)
        order_rows = self.request(
            "POST",
            "orders",
            body={
                "customer_id": customer.get("id"),
                "status": "pending_payment",
                "subtotal": subtotal,
                "shipping": shipping,
                "total": total,
                "currency": "USD",
                "channel": "site",
                "notes": payload.notes.strip(),
            },
        )
        order = order_rows[0]

        items_body = []
        for line in order_lines:
            product = line["product"]
            items_body.append(
                {
                    "order_id": order["id"],
                    "product_id": product.get("id"),
                    "sku": product["sku"],
                    "product_name": product["name"],
                    "quantity": line["quantity"],
                    "unit_price": line["unit_price"],
                }
            )
            next_count = max(0, int(product.get("inventory_count") or 0) - line["quantity"])
            self.request(
                "PATCH",
                "products",
                params={"id": f"eq.{product.get('id')}"},
                body={"inventory_count": next_count},
                prefer="return=minimal",
            )

        self.request("POST", "order_items", body=items_body)
        self.request(
            "POST",
            "customer_messages",
            body={
                "customer_id": customer.get("id"),
                "email": email,
                "subject": "Order confirmation queued",
                "body": f"Post-purchase care sequence queued for order {order['id']}.",
                "channel": "email_sequence",
                "status": "queued",
                "sequence_key": "post_purchase_care",
            },
        )

        return {
            "id": order["id"],
            "customer_email": email,
            "status": order["status"],
            "subtotal": subtotal,
            "shipping": shipping,
            "total": total,
            "currency": "USD",
            "source": "supabase",
        }

    def create_newsletter_signup(self, payload: NewsletterRequest) -> dict[str, Any]:
        email = normalize_email(payload.email)
        if not self.configured:
            return {"email": email, "sequence_key": "artist_welcome", "source": "demo"}

        customer = self.upsert_customer(
            CustomerInput(email=email, first_name=payload.first_name, last_name="", phone="")
        )
        self.request(
            "POST",
            "customer_messages",
            body={
                "customer_id": customer.get("id"),
                "email": email,
                "subject": "Newsletter signup",
                "body": "Artist welcome sequence queued.",
                "channel": "email_sequence",
                "status": "queued",
                "sequence_key": "artist_welcome",
            },
        )
        return {"email": email, "sequence_key": "artist_welcome", "source": "supabase"}

    def create_customer_message(self, payload: CustomerMessageRequest) -> dict[str, Any]:
        email = normalize_email(payload.email)
        if not self.configured:
            return {"email": email, "status": "open", "source": "demo"}

        customer = self.upsert_customer(CustomerInput(email=email))
        rows = self.request(
            "POST",
            "customer_messages",
            body={
                "customer_id": customer.get("id"),
                "email": email,
                "subject": payload.subject.strip(),
                "body": payload.body.strip(),
                "channel": "site",
                "status": "open",
            },
        )
        return rows[0] if isinstance(rows, list) and rows else {"email": email, "status": "open"}

    def dashboard(self) -> dict[str, Any]:
        products = self.products()
        orders = self.orders()
        suppliers = self.suppliers()
        messages = self.messages()
        sequences = self.email_sequences()

        revenue = sum(float(order.get("total") or 0) for order in orders)
        item_count = 0
        for order in orders:
            for item in order.get("order_items") or []:
                item_count += int(item.get("quantity") or 0)

        low_stock = [product for product in products if inventory_status(product) in {"Low", "Out"}]
        open_messages = [message for message in messages if message.get("status") in {"open", "queued"}]

        return {
            "source": self.source_label,
            "generated_at": now_iso(),
            "metrics": {
                "revenue": revenue,
                "orders": len(orders),
                "average_order": revenue / len(orders) if orders else 0,
                "items_sold": item_count,
                "low_stock": len(low_stock),
                "open_messages": len(open_messages),
            },
            "products": products,
            "orders": orders,
            "suppliers": suppliers,
            "messages": messages,
            "sequences": sequences,
            "low_stock": low_stock,
        }


repo = CommerceRepository()


def require_admin(credentials: HTTPBasicCredentials | None = Depends(security)) -> bool:
    if not ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin password is not configured.",
        )
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required.",
            headers={"WWW-Authenticate": 'Basic realm="Atelier Bristle Admin"'},
        )
    username_ok = hmac.compare_digest(credentials.username, ADMIN_USERNAME)
    password_ok = hmac.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
            headers={"WWW-Authenticate": 'Basic realm="Atelier Bristle Admin"'},
        )
    return True


@app.get("/", response_class=HTMLResponse)
async def storefront(request: Request):
    products = repo.products()
    return templates.TemplateResponse(
        request,
        "storefront.html",
        {
            "brand": "Atelier Bristle",
            "products": products,
            "source": repo.source_label,
        },
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, _: bool = Depends(require_admin)):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "brand": "Atelier Bristle",
            "dashboard": repo.dashboard(),
            "admin_protected": bool(ADMIN_PASSWORD),
        },
    )


@app.get("/api/catalog")
async def catalog():
    return {"products": repo.products(), "source": repo.source_label}


@app.post("/api/newsletter")
async def newsletter(payload: NewsletterRequest):
    return repo.create_newsletter_signup(payload)


@app.post("/api/messages")
async def customer_message(payload: CustomerMessageRequest):
    return repo.create_customer_message(payload)


@app.post("/api/orders")
async def create_order(payload: OrderRequest):
    return repo.create_order(payload)


@app.get("/api/dashboard")
async def dashboard_data(_: bool = Depends(require_admin)):
    return repo.dashboard()


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "supabase_configured": repo.configured,
        "source": repo.source_label,
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)
