# Team10LeapRUNAnalytics
Warehouse-backed trading analytics service for the Spring Boot trading application.

## Security boundary

**This Python service does not validate JWTs or employee roles.** Spring Boot must
authenticate and authorize every call. Deploy Python on a private network and allow
access only from Spring Boot. Do not expose these URLs directly to the frontend.
CORS is not authentication. The existing wildcard CORS configuration does not protect data.

For client account routes, Spring Boot must derive `client_id` from the signed-in
principal, never trust a browser-supplied ID. Only REPORTER and ADMIN should access
employee reports. This applies to existing routes as well as new ones. No employee
ID/role query parameter grants authorization.

Frontend flow: browser → authenticated Spring Boot endpoint → private Python URL.
Spring Boot should stream PNG responses with `Content-Type: image/png`. For bearer
authentication use authenticated frontend fetch and a blob URL rather than placing
tokens in image URLs. All responses have `Cache-Control: no-store`.

## Endpoint reference

All routes below use **GET**. Local development base URL is `http://localhost:5000`;
interactive OpenAPI docs are at `/docs`. Restart the existing API process after code
changes; no automatic reload is enabled by the current startup scripts.

### Signed-in client account

`{client_id}` must be supplied by Spring Boot using the authenticated account.

| Python route | Result | Status |
| --- | --- | --- |
| `/api/analytics/clients/{client_id}/holdings/top-gainers` | Top five priced holdings ranked by absolute unrealized profit, plus excluded tickers | New JSON |
| `/api/analytics/clients/{client_id}/allocation` | Current market values and allocation percentages | New JSON |
| `/api/analytics/clients/{client_id}/allocation/graph` | Allocation pie chart showing percentages | New PNG |
| `/api/analytics/clients/{client_id}/order-status/graph?days=30` | Counts of cancelled, pending, fulfilled orders | New PNG |
| `/api/analytics/order-status?client_id={client_id}&days=30` | The same status counts for frontend-rendered charts | Existing JSON |
| `/analytics/transactions/{client_id}` | Account transactions | Existing JSON; `data` is a JSON-encoded string |

JSON responses wrap the payload in `status` and `data`. New account responses also
include `client_id`. Status JSON uses an array with one client record. Unknown
clients return 404 for the status chart; empty holdings produce an empty top-five
list, zero allocation, and a PNG labelled “No priced holdings”. Holdings routes
do not distinguish unknown clients from clients with no holdings.

#### Holdings definitions

- Profit is **unrealized moving weighted-average cost gain**, not today's price
	movement or realized profit. Replay fulfilled BUY/SELL orders chronologically;
	a sell removes cost at the current average cost. Fees, dividends and FX are excluded.
- Top-five ranking is by absolute gain, not percentage. Negative gains remain
	eligible if fewer than five profitable positions exist.
- Cost history must reconcile to current holdings. Unsupported order types,
	sells preceding purchases or quantity mismatches produce unknown cost basis;
	those positions are excluded from the ranking and listed in `excluded_tickers`.
	Imported holdings without full acquisition history need an authoritative cost
	basis source before their profit can be reported.
- Current holdings use the latest available bid, falling back to ask. The quote
	timestamp is returned; historical/stale quotes are not presented as live prices.
- Allocation uses **market value**, not share count: stock, other crypto, Bitcoin,
	and other assets. Bitcoin is not double-counted as crypto. Cash is excluded.
	Missing quotes are disclosed in `unpriced_tickers` and omitted from percentages.
	All values must share the same quote currency; no FX conversion is implemented.
- ETL must maintain accurate net holdings. These endpoints do not repair holdings
	or create historical acquisition records.

### Employee reports — REPORTER / ADMIN only

| Python route | Purpose | Status |
| --- | --- | --- |
| `/api/analytics/orders` | Filtered, paginated order list and total matching count | New JSON |
| `/api/analytics/trends` | Order counts, volume, active clients and other metrics over time | Extended existing JSON |
| `/api/analytics/trends/graph?metric=trade_count` | Total orders over time chart | Extended existing PNG |
| `/api/analytics/trading-volume` | Total turnover, quantity, buy and sell volumes | New JSON |
| `/api/analytics/by-instrument?sort_by=trade_count&limit=1` | Most active instrument by number of orders | Extended existing JSON |
| `/api/analytics/by-instrument?sort_by=total_volume&limit=5` | Top instruments by turnover | Extended existing JSON |
| `/api/analytics/client-activity` | Per-client activity trend by period | New JSON |
| `/api/analytics/` | Existing KPI overview and top five clients by volume | Existing JSON |
| `/api/analytics/by-client` | Client segment summary and detailed activity | Existing JSON |
| `/api/analytics/order-status` | Status breakdown for all clients; optional client filter | Existing JSON |
| `/api/analytics/instrument/{ticker}` | Instrument metrics, top traders and daily trend | Existing JSON |

The following routes share these filters: `orders`, `trends`, `trends/graph`,
`trading-volume`, `by-instrument`, and `client-activity`:

| Query parameter | Meaning |
| --- | --- |
| `days=30` | Lookback from current date, 1–3650 days |
| `start_date=2026-10-01` | Inclusive date; overrides `days` lower bound |
| `end_date=2026-10-23` | Inclusive whole day; default includes today |
| `ticker=AAPL` | Exact instrument ticker |
| `client_id=3` | One client |
| `order_status=FULFILLED` | Optional FULFILLED/PENDING/CANCELLED/CANCELED; both cancelled spellings match |

Date boundaries use the database session timezone. Start must not be after end.
`trends`, `trends/graph`, and `client-activity` accept
`granularity=daily|weekly|monthly`. Empty periods are omitted, not filled with zeros.

Additional parameters:
- `orders`: `limit=50` (1–500), `offset=0`. `data` contains `total_orders`, `orders`,
	`limit`, `offset`; total remains available beyond the last page.
- `by-instrument`: `sort_by=total_volume|trade_count|total_quantity`, optional
	`limit` (1–1000). Instruments without matching orders may appear with zero metrics.
- `trends/graph`: `metric=trade_count|total_volume|avg_trade_value|active_clients|instruments_traded`.
- Existing overview, client segments, instrument details and order-status JSON
	accept `days`; they do not share the other report filters.

**Volume semantics:** `/trading-volume` defaults to FULFILLED orders (executed
notional turnover, sum of quantity × price). Other reports include all order
statuses unless explicitly filtered. For matching executed-volume trends use
`/trends?order_status=FULFILLED` or the graph equivalent. The legacy overview
totals count all historical orders; its `days` parameter limits client activity
fields rather than all totals. Quantities across assets are not a currency value.

Example private service requests:
- `/api/analytics/orders?ticker=AAPL&client_id=3&start_date=2026-10-01&end_date=2026-10-23&limit=50`
- `/api/analytics/trends?granularity=weekly&order_status=FULFILLED&client_id=3`
- `/api/analytics/trading-volume?ticker=AAPL&days=7`
- `/api/analytics/client-activity?granularity=daily&days=30`

### Market/reference data — authorize in Spring Boot as appropriate

| Route | Result |
| --- | --- |
| `/analytics/instruments/` | Instrument catalogue; legacy `data` is a JSON-encoded string |
| `/stock_statistics/{ticker}` | Current-day open, previous calendar-day close, bid/ask and day range |

Stock statistics return 404 when there are no quotes today. The previous calendar
day may not be a trading day, so previous close may be null. Instrument details
contain client names in top traders and therefore belong to employee reports,
not the public/client market-data proxy.

## Validation

Runtime dependencies are in [requirements.txt](requirements.txt); test dependencies
are in [requirements-dev.txt](requirements-dev.txt).

Dashboard tests: `python -m unittest discover -s tests -p test_dashboard_api.py -v`.
Set `RUN_DASHBOARD_INTEGRATION=1` to include the read-only warehouse smoke test.
Tests use FastAPI's in-process HTTP client, including real PNG rendering. Existing
legacy analytics tests have outdated imports/mocks and are not part of this
focused suite. Live service availability still depends on starting/restarting
Uvicorn and an accessible warehouse.
