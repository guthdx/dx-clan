# DX Clan Genealogy Database

A searchable genealogy database for the Ducheneaux family history, built with FastAPI, PostgreSQL, and React.

## Database Statistics

- **8,988 persons** in the database
- **2,760 marriages** linked
- **11,396 parent-child relationships**

## Production Deployment

**URL**: https://dxclan.iyeska.net

**Server**: 192.168.11.20 (IyeskaLLC Ubuntu server)

**Location**: `/opt/apps/dxclan/`

**Ports**:
- Frontend: 19080 (nginx)
- Backend: 19000 (FastAPI)
- Database: internal Docker network

**Cloudflare Tunnel**: Requires public hostname added via Zero Trust dashboard

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for frontend development without Docker)
- Python 3.12+ (for backend development without Docker)

### Running with Docker

```bash
# Start all services
docker compose up -d

# Import genealogy data (first time only)
docker compose cp DX_Clan_ocr_clean.txt backend:/app/DX_Clan_ocr_clean.txt
docker compose exec backend python scripts/parse_genealogy.py DX_Clan_ocr_clean.txt --clear

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

Once running:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Production Deployment (Ubuntu Server)

```bash
# SSH to server
ssh guthdx@192.168.11.20

# Navigate to deployment
cd /opt/apps/dxclan

# Start services
docker compose -f docker-compose.production.yml up -d

# Check status
docker compose -f docker-compose.production.yml ps

# View logs
docker compose -f docker-compose.production.yml logs -f

# Reimport data (if OCR was updated)
docker compose -f docker-compose.production.yml exec backend python scripts/import_genealogy.py --clear
```

Production URLs (once Cloudflare tunnel hostname is configured):
- **Frontend**: https://dxclan.iyeska.net
- **Backend API**: https://dxclan.iyeska.net/api/
- **Local Frontend**: http://localhost:19080
- **Local API**: http://localhost:19000

### Development Setup

**Backend (without Docker):**

```bash
cd backend

# Create virtual environment (use Python 3.12+)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations (requires PostgreSQL running)
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000
```

**Frontend (without Docker):**

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

## Project Structure

```
dx_clan/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API routes
│   │   ├── core/            # Configuration
│   │   ├── db/              # Database session
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── scripts/             # Parser and utilities
│   └── alembic/             # Database migrations
├── frontend/
│   └── src/
│       ├── pages/           # Route components
│       ├── components/      # Reusable UI
│       └── lib/             # API client
├── highres_pages/           # 300 DPI PNG images from PDF
├── ocr_output/              # Individual page OCR text
├── ocr_vision.py            # Single-page Apple Vision OCR
├── ocr_all_pages.py         # Batch OCR script
├── DX_Clan_ocr_clean.txt    # Combined clean OCR output
├── docker-compose.yml
└── Dx_clan_genealogy_only.pdf  # Source PDF (cropped)
```

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy (async) + Alembic
- **Frontend**: React + Vite + React Router
- **Database**: PostgreSQL 16
- **OCR**: Apple Vision framework (macOS)
- **Deployment**: Docker Compose

## Data Source

The genealogy data comes from a 274-page PDF document that was:
1. Cropped to remove scanning artifacts
2. Converted to 300 DPI PNG images using `pdftoppm`
3. OCR'd using Apple Vision framework (superior accuracy for this document type)
4. Parsed into structured database records

**Format:**
- Dots with generation numbers indicate depth (e.g., `....3 Name`)
- `+` prefix indicates spouse
- `*` prefix indicates remarriage

## API Endpoints

### Persons
- `GET /api/v1/persons/search?q=` - Search by name
- `GET /api/v1/persons/{id}` - Get person details
- `GET /api/v1/persons` - List all persons
- `POST /api/v1/persons` - Create person
- `PUT /api/v1/persons/{id}` - Update person
- `DELETE /api/v1/persons/{id}` - Delete person

### Families
- `GET /api/v1/families/{id}/ancestors` - Get ancestor tree
- `GET /api/v1/families/{id}/descendants` - Get descendant tree
- `GET /api/v1/families/{id}/tree` - Get full family tree

### Relationships
- `POST /api/v1/relationships/marriages` - Create marriage
- `DELETE /api/v1/relationships/marriages/{id}` - Delete marriage
- `POST /api/v1/relationships/parent-child` - Create parent-child link
- `DELETE /api/v1/relationships/parent-child/{id}` - Delete parent-child link

## OCR Re-processing (if needed)

If you need to re-OCR the source PDF:

```bash
# Extract high-resolution PNGs (300 DPI)
pdftoppm -png -r 300 Dx_clan_genealogy_only.pdf highres_pages/page

# Activate OCR virtual environment
source .ocr_venv/bin/activate

# Run Apple Vision OCR on all pages
python ocr_all_pages.py

# Output saved to DX_Clan_ocr_clean.txt
deactivate
```

Requires macOS with pyobjc packages installed in `.ocr_venv`.

## License

Private - Ducheneaux Family
