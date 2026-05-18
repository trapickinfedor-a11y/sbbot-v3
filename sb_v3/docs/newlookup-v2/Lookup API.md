# Lookup API

[[MOC]] > Lookup API

**3 файла** | FastAPI + SQLite | Порт :8001 | Автономный

---

## lookup_api/app.py
**Строк:** 903

**Классы:**
- `CreateTokenRequest(BaseModel)`
- `SearchRequest(BaseModel)`
- `DLRequest(BaseModel)`
- `CRRequest(BaseModel)`
- `AddBalanceRequest(BaseModel)`

**Функции (25):**
- `_conn() -> sqlite3.Connection`
- `init_db() -> None`
- `async lifespan(application: FastAPI)`
- `_hash_pw(password: str) -> str`
- `_get_key_by_apikey(conn: sqlite3.Connection, api_key: str)`
- `_get_key_by_credentials(...)`
- `_require_api_key(x_api_key: Optional[str] = Header(default=None))`
- `_require_admin(x_admin_token: Optional[str] = Header(default=None))`
- `_bill(...)`
- `_norm_name(s: str) -> str`
- `_norm_dob(dob: Optional[str]) -> Optional[str]`
- `_row_to_dict(row: sqlite3.Row) -> dict`
- `create_token(body: CreateTokenRequest)`
- `get_balance(api_key: str = Depends(_require_api_key))`
- `search_ssn(body: SearchRequest, api_key: str = Depends(...))`
- `search_dl(body: DLRequest, api_key: str = Depends(...))`
- `search_cr(body: CRRequest, api_key: str = Depends(...))`
- `download_cr_pdf(record_id: int, api_key: str = Depends(...))`
- `async upload_cr_pdf(...)`
- `admin_add_balance(...)`
- `admin_list_users(_: None = Depends(_require_admin))`
- `admin_stats(_: None = Depends(_require_admin))`
- `async admin_import_csv(...)`
- `_batched(iterable, n)`
- `health()`

**Роуты (12):**
- `@app.post("/api/create_token/")`
- `@app.get("/api/get_balance/")`
- `@app.post("/api/search/")`
- `@app.post("/api/dl/")`
- `@app.post("/api/cr/")`
- `@app.get("/api/cr/download/{record_id}")`
- `@app.post("/api/cr/upload_pdf")`
- `@app.post("/api/admin/add_balance")`
- `@app.get("/api/admin/users")`
- `@app.get("/api/admin/stats")`
- `@app.post("/api/admin/import_csv")`
- `@app.get("/health")`

**API-вызовы:**
- `from fastapi.middleware.cors import CORSMiddleware`
- `from fastapi.responses import FileResponse`

**TODO/заглушки:** 1 (`pass`)

---

## lookup_api/importer.py
**Строк:** 362

**Функции (9):**
- `_norm_dob(dob: str | None) -> str | None`
- `_pick(row: dict, *keys: str, default: str = "") -> str`
- `_normalise_header(row: dict) -> dict`
- `import_persons(conn: sqlite3.Connection, path: Path, sep...)`
- `import_licenses(conn: sqlite3.Connection, path: Path, se...)`
- `rebuild_fts(conn: sqlite3.Connection) -> None`
- `import_cr_records(conn: sqlite3.Connection, path: Path, ...)`
- `link_pdfs(conn: sqlite3.Connection, pdf_dir: Path, patte...)`
- `main() -> None`

**TODO/заглушки:** 1 (`pass`)

---

## lookup_api/manage_keys.py
**Строк:** 257

**Функции (6):**
- `create_key(username: str, password: str, initial_balance...)`
- `list_keys() -> list`
- `get_balance(username: str) -> dict`
- `add_balance(username: str, amount: float) -> dict`
- `set_active(username: str, active: bool) -> dict`
- `main()`

---

## Авторизация

- API-ключ: `X-Api-Key` header → `_require_api_key()`
- Admin-токен: `X-Admin-Token` header → `_require_admin()`
- Биллинг за каждый запрос через `_bill()`

## Изоляция

Полностью автономный сервис. Не зависит от [[Shared Services]], [[Seller Bot]] или [[Web Panel]]. Собственная SQLite БД.
