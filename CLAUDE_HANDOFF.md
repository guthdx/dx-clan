# DX Clan Genealogy Database - Project Complete

## Project Status: All Phases Complete

### What's Built

**Backend (FastAPI + SQLAlchemy + PostgreSQL)**
- `backend/app/models/` - Person, PersonAlias, Marriage, ParentChild, Source
- `backend/app/services/person_service.py` - Search, CRUD, alias management
- `backend/app/services/family_service.py` - Ancestor/descendant tree traversal
- `backend/app/services/relationship_service.py` - Marriage and parent-child CRUD
- `backend/app/api/v1/persons.py` - Full CRUD endpoints
- `backend/app/api/v1/families.py` - Tree endpoints
- `backend/app/api/v1/relationships.py` - Relationship management endpoints
- `backend/app/schemas/genealogy.py` - Pydantic schemas with camelCase aliases
- `backend/alembic/versions/001_initial_schema.py` - Database migration

**Parser**
- `backend/scripts/parse_genealogy.py` - Parses genealogy text files
- Handles OCR artifacts, dot-notation genealogy format with explicit generation numbers
- Extracts **13,356 persons**, **3,331 marriages**, **7,229 parent-child links**

**OCR Pipeline (Apple Vision)**
- `ocr_vision.py` - Single-page OCR using Apple Vision framework
- `ocr_all_pages.py` - Batch OCR for all pages
- `.ocr_venv/` - Python virtual environment with pyobjc dependencies
- `highres_pages/` - 300 DPI PNG images extracted from PDF
- `ocr_output/` - Individual page OCR text files
- `DX_Clan_ocr_clean.txt` - Combined clean OCR output (24,058 lines)

**Frontend (React + Vite)**
- `frontend/src/App.jsx` - Routes: `/`, `/person/:id`, `/person/:id/tree`
- `frontend/src/pages/Home.jsx` - Search with debounce, browse list
- `frontend/src/pages/PersonDetail.jsx` - Person view with relationships
- `frontend/src/pages/TreeView.jsx` - Family tree visualization page
- `frontend/src/components/FamilyTree.jsx` - Expandable tree component
- `frontend/src/components/ErrorBoundary.jsx` - Error handling
- `frontend/src/components/Loading.jsx` - Loading spinners
- `frontend/src/lib/api.js` - API client

**Docker**
- `docker-compose.yml` - PostgreSQL 16, backend, frontend services

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/persons/search?q=` | Search persons |
| GET | `/api/v1/persons/{id}` | Get person details |
| GET | `/api/v1/persons` | List persons |
| POST | `/api/v1/persons` | Create person |
| PUT | `/api/v1/persons/{id}` | Update person |
| DELETE | `/api/v1/persons/{id}` | Delete person |
| POST | `/api/v1/persons/{id}/aliases` | Add alias |
| DELETE | `/api/v1/persons/{id}/aliases/{alias_id}` | Remove alias |
| GET | `/api/v1/families/{id}/ancestors` | Get ancestor tree |
| GET | `/api/v1/families/{id}/descendants` | Get descendant tree |
| GET | `/api/v1/families/{id}/tree` | Get full tree |
| POST | `/api/v1/relationships/marriages` | Create marriage |
| DELETE | `/api/v1/relationships/marriages/{id}` | Delete marriage |
| POST | `/api/v1/relationships/parent-child` | Create parent-child |
| DELETE | `/api/v1/relationships/parent-child/{id}` | Delete parent-child |

### How to Run

```bash
cd /Users/guthdx/terminal_projects/dx_clan
docker compose up -d
docker compose cp DX_Clan_ocr_clean.txt backend:/app/DX_Clan_ocr_clean.txt
docker compose exec backend python scripts/parse_genealogy.py DX_Clan_ocr_clean.txt --clear
# Frontend: http://localhost:5173
# API: http://localhost:8000/docs
```

### OCR Workflow (if re-processing PDF)

```bash
# 1. Extract high-resolution PNGs from PDF (300 DPI)
pdftoppm -png -r 300 Dx_clan_genealogy_only.pdf highres_pages/page

# 2. Activate OCR virtual environment
source .ocr_venv/bin/activate

# 3. Run Apple Vision OCR on all pages
python ocr_all_pages.py

# 4. Output saved to DX_Clan_ocr_clean.txt
deactivate
```

### Features

- **Search**: Type-ahead search by name or alias
- **Person Detail**: View person info, aliases, spouses, parents, children
- **Family Tree**: Visual expandable tree with ancestors and descendants
- **Generation Controls**: Adjust how many generations to display
- **Mobile Responsive**: Works on phones and tablets
- **Error Handling**: Error boundaries catch and display errors gracefully
- **Loading States**: Spinner animations during data fetching

### Key Technical Decisions

1. **Database**: PostgreSQL with UUID primary keys
2. **API**: FastAPI with async SQLAlchemy, camelCase JSON responses
3. **OCR**: Apple Vision framework (macOS) - far superior to Tesseract for this document
4. **Parser**: Line-by-line with regex, handles explicit generation numbers (e.g., `....3 Name`)
5. **Frontend**: React with React Router, vanilla CSS
6. **Tree Display**: Recursive component with expand/collapse state

### Data Source

**Original**: `Dx_clan_genealogy_only.pdf` (274 pages, cropped to remove scan artifacts)

**Processed**: `DX_Clan_ocr_clean.txt` (24,058 lines)
- OCR'd using Apple Vision framework at 300 DPI
- Uses dot notation with explicit generation numbers (e.g., `....3 Sophia LeCompte`)
- `+` prefix = spouse, `*` prefix = remarriage
- Clean names, proper dates, minimal OCR artifacts

### Database Statistics

- **13,356 persons** imported
- **3,331 marriages** linked
- **7,229 parent-child relationships** established
- **564 aliases** (nicknames, alternate names)
- **4,319 persons** with birth/death dates

### Future Enhancements (if needed)

- Authentication (admin key like cyoa-honky-tonk)
- Edit forms in frontend (API is ready)
- Export to GEDCOM format
- Photo attachments
- Source citations UI
- Deduplication of repeated names (some persons appear multiple times in source)

### Current State (as of Dec 25, 2024)

**Local Development:**
- **Docker**: Services running (`docker compose up -d`)
- **Database**: Populated with genealogy data
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000/docs
- **Git**: Initialized, pushed to GitHub

**Production Deployment (Ubuntu Server 192.168.11.20):**
- **Location**: `/opt/apps/dxclan/`
- **Docker Compose**: `docker-compose.production.yml`
- **Frontend**: http://localhost:19080
- **Backend API**: http://localhost:19000
- **Database**: PostgreSQL 16 (Docker container)
- **Data**: 8,988 persons, 11,396 parent-child, 2,760 marriages

**Cloudflare Tunnel:**
- DNS route added: `dxclan.iyeska.net` → tunnel
- **TODO**: Add public hostname via Cloudflare Zero Trust dashboard
  - Subdomain: `dxclan`
  - Domain: `iyeska.net`
  - Service: `http://localhost:19080`

### Recent Changes (Dec 25, 2024)

1. **OCR Date Fixes**:
   - Fixed semicolons in dates (`Jan 22; 1978` → `Jan 22, 1978`)
   - Added multi-line date joining for 3-line patterns
   - Fixed Marie Elizabeth Kougl (1978) and Jewel Daleen Kougl (1988) dates

2. **Production Deployment**:
   - Deployed to `/opt/apps/dxclan/` following established process
   - Created `docker-compose.production.yml` with localhost ports
   - Configured nginx to proxy API requests to backend
   - Imported data via `import_genealogy.py`

3. **Cloudflare Integration**:
   - Added DNS route via `cloudflared tunnel route dns`
   - Local cloudflared config updated (but uses remote config)
   - Pending: Add public hostname via Zero Trust dashboard

### Key Files

| File | Purpose |
|------|---------|
| `scripts/clean_ocr_punctuation.py` | Cleans OCR artifacts before parsing |
| `backend/scripts/smart_parser.py` | Main parser for genealogy text |
| `backend/scripts/import_genealogy.py` | Imports JSON to PostgreSQL |
| `backend/scripts/qa_check.py` | Data quality checks |
| `docker-compose.production.yml` | Production deployment config |

### Management Commands

**Local:**
```bash
docker compose up -d
docker compose logs -f
```

**Production (SSH to 192.168.11.20):**
```bash
cd /opt/apps/dxclan
docker compose -f docker-compose.production.yml up -d
docker compose -f docker-compose.production.yml logs -f
docker compose -f docker-compose.production.yml exec backend python scripts/import_genealogy.py --clear
```

### GitHub

Repository: https://github.com/guthdx/dx_clan
