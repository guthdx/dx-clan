# CLAUDE.md - DX Clan Genealogy Database

This file provides guidance to Claude Code when working with this repository.

## Overview

A searchable genealogy database for the Ducheneaux family history built with FastAPI, PostgreSQL, and React. The data comes from a 274-page PDF that was OCR'd using Apple Vision framework.

## Architecture

```
dx_clan/
├── backend/           # FastAPI + SQLAlchemy async
│   ├── app/
│   │   ├── api/v1/   # REST endpoints
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   └── services/ # Business logic
│   └── scripts/      # Parser and import tools
├── frontend/          # React + Vite
│   └── src/
│       ├── pages/    # Route components
│       ├── components/
│       └── lib/      # API client
├── ocr_output/        # Per-page OCR text files
├── scripts/           # OCR cleaning utilities
└── docker-compose.yml # Local development
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/scripts/smart_parser.py` | Parses genealogy text format |
| `backend/scripts/import_genealogy.py` | Imports parsed JSON to PostgreSQL |
| `backend/scripts/qa_check.py` | Data quality validation |
| `scripts/clean_ocr_punctuation.py` | Pre-processing OCR artifacts |
| `backend/data/parsed_genealogy.json` | Intermediate parsed data |
| `DX_Clan_ocr_clean.txt` | Combined OCR output |

## Genealogy Text Format

```
....3 Sophia LeCompte Jan 1, 1900 - Dec 31, 1980
.....+John Smith 1898 - 1970
......4 Mary LeCompte Smith Feb 14, 1925
```

- Dots indicate generation depth
- Number after dots is explicit generation
- `+` prefix = spouse
- `*` prefix = remarriage
- Dates: `Month Day, Year` or just `Year`

## Common Tasks

### Re-parse OCR Data

```bash
# 1. Clean OCR artifacts
python scripts/clean_ocr_punctuation.py

# 2. Regenerate combined file
cat ocr_output/page-*.txt > DX_Clan_ocr_clean.txt

# 3. Parse to JSON
python backend/scripts/smart_parser.py

# 4. Run QA checks
python backend/scripts/qa_check.py

# 5. Import to database (local)
docker compose exec backend python scripts/import_genealogy.py --clear
```

### Local Development

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f

# Frontend: http://localhost:5173
# API Docs: http://localhost:8000/docs
```

### Production Deployment

Production runs on Ubuntu server at 192.168.11.20.

```bash
# SSH to server
ssh guthdx@192.168.11.20

# Navigate to deployment
cd /opt/apps/dxclan

# Manage services
docker compose -f docker-compose.production.yml up -d
docker compose -f docker-compose.production.yml logs -f
docker compose -f docker-compose.production.yml ps

# Reimport data
docker compose -f docker-compose.production.yml exec backend python scripts/import_genealogy.py --clear
```

**Production URLs:**
- Public: https://dxclan.iyeska.net (via Cloudflare Tunnel)
- Local: http://localhost:19080 (frontend), http://localhost:19000 (API)

## Database Schema

- `persons` - Main person records (UUID PK)
- `person_aliases` - Nicknames and alternate names
- `marriages` - Spouse relationships (spouse1_id, spouse2_id)
- `parent_child` - Parent-child relationships

## OCR Pipeline

If re-OCR is needed (macOS only):

```bash
# Extract PNGs from PDF
pdftoppm -png -r 300 Dx_clan_genealogy_only.pdf highres_pages/page

# Activate OCR environment
source .ocr_venv/bin/activate

# Run Apple Vision OCR
python ocr_all_pages.py

deactivate
```

## Known Issues

1. **OCR artifacts**: Some names have garbage characters; use `qa_check.py` to identify
2. **Duplicate persons**: Same person may appear multiple times in source
3. **Date fragments**: Multi-line dates sometimes split incorrectly

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/persons/search?q=` | Search by name |
| `GET /api/v1/persons/{id}` | Person details |
| `GET /api/v1/families/{id}/tree` | Family tree |
| `GET /api/v1/families/{id}/ancestors` | Ancestor tree |
| `GET /api/v1/families/{id}/descendants` | Descendant tree |

## Environment

**Local Docker Compose:**
- PostgreSQL 16 on internal network
- Backend on port 8000
- Frontend on port 5173

**Production (192.168.11.20):**
- Frontend: port 19080 (nginx)
- Backend: port 19000 (FastAPI)
- Cloudflare Tunnel for public access

## Cloudflare Tunnel

The production server uses Cloudflare Tunnel with **remote configuration** (managed via Zero Trust dashboard). To add/modify public hostnames:

1. Go to https://one.dash.cloudflare.com/
2. Networks > Tunnels > select tunnel > Configure
3. Public Hostname tab > Add hostname
4. Subdomain: `dxclan`, Domain: `iyeska.net`, Service: `http://localhost:19080`

Local cloudflared config at `~/.cloudflared/config.yml` is for reference only.
