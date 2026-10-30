# EcoCycle AI — Backend Engine (2.0 MVP)

> Large-Scale Waste Intelligence, Reverse Logistics, and Circular Recovery Platform Backend.

---

## 1. Project Overview & Scope

**EcoCycle AI** is an enterprise-grade circular economy and reverse logistics platform designed to optimize municipal and doorstep waste management, construction & demolition (C&D) material estimation, circular resource recovery, and fleet logistics.

**Scope of this repository:**
- **Backend Only**: Implemented as a high-performance modular monolith using **Python and FastAPI**.
- **Mobile Client**: The mobile application is developed independently using **Flutter** and communicates exclusively with this backend via versioned REST APIs (`/api/v1`).
- No frontend dashboard or mobile screens are included in this repository.

---

## 2. Five Pillars Implemented Workflows (2.0 MVP)

All five pillars are operational through real, testable, and persistent backend workflows:

### 1. Four-Stream Waste Management & EcoPass
- **Statutory Four Streams**: `wet_organic`, `dry_recyclable`, `sanitary`, and `hazardous` (special-care / domestic hazardous).
- **Citizen Reports**: Doorstep reports with GPS coordinates, address, municipal ward, stream classification, description, and optional photo URLs.
- **EcoPass Digital Household Identity**: Generates unique identifiers (e.g. `ECOPASS-W101-A79B12`) tracking household diversion and credit balances.

### 2. Pickup Dispatch & EcoProof Verification
- **Operational Dispatch**: Pickups scheduled from logged reports, assigned to sanitation workers and vehicles.
- **EcoProof Cryptographic Verification**: Upon physical collection, records confirmed stream, weighed mass, collector signature ID, and issues a **SHA-256 integrity hash digest**.
- **Automated EcoCredits**: Awards 10 EcoCredits per kg of verified segregated waste diverted to the household's immutable ledger.

### 3. Construction & Demolition (C&D) Waste Management
- **Geometric Formula Estimation**: Computes volume ($m^3$) and tonnage using dimensional inputs ($L \times W \times H$) or direct cubic meters with bulk material densities (concrete rubble ~1500 kg/m³, brick masonry ~1800 kg/m³, mixed C&D ~1300 kg/m³, tiles ~1600 kg/m³).
- **Salvage Marketplace**: Persistent CRUD for reusable materials (bricks, tiles, concrete blocks, aggregate, timber, steel scrap) with condition grading and pricing.

### 4. Circular Recovery & Community Donations
- **Reuse & Resale Listings**: Secondhand marketplace for furniture, electronics, clothing, books, and appliances.
- **Community NGO Donations**: Free donation listings for community diversion.
- **Diversion Incentives**: When an item is claimed or completed, 50 EcoCredits are awarded to the donor's household EcoPass.

### 5. Fleet Logistics, Municipal Dashboard & Multilingual Voice Guidance
- **Deterministic Priority Queue**: Ranks active collections using transparent multi-factor scoring: Stream Biohazard Risk (`hazardous`=100, `sanitary`=50, `wet_organic`=40, `dry_recyclable`=20) + Aging Hours ($\times 2.0$) + Estimated Mass ($\times 0.5$).
- **Live Municipal Governance Dashboard**: Real-time aggregated statistics calculated directly from stored database rows (stream distributions, verified tonnage, circulating EcoCredits, ward coverage).
- **Regional Language Rules**: Official segregation guidelines localized in **English**, **Hindi (हिंदी)**, **Kannada (ಕನ್ನಡ)**, **Tamil (தமிழ்)**, **Telugu (తెలుగు)**, and **Marathi (मराठी)**.
- **MeitY Bhashini Interface**: Transparent diagnostic probe reporting connection readiness.

---

## 3. Technology Stack

- **Framework**: Python 3.12+, FastAPI (ASGI)
- **Database**:
  - **Local Prototyping (Active)**: Persistent SQLite (`data/ecocycle_dev.db`) with zero external setup required.
  - **Production Ready**: Fully compatible with PostgreSQL + PostGIS via SQLAlchemy 2.x and Alembic.
- **ORM & Validation**: SQLAlchemy 2.x (Universal `sa.Uuid`), Pydantic v2, Pydantic-Settings
- **Server**: Uvicorn with ASGI
- **Testing**: Pytest, Pytest-Asyncio, Starlette TestClient (30 automated tests passing in <0.5s)
- **Security & Cryptography**: SHA-256 HMAC integrity digests, input bounds validation

---

## 4. Local Setup & Execution Guide (Windows)

### Prerequisites
- Python 3.12+ installed on Windows.
- Windows PowerShell.

### Step 1: Open Terminal in Project Directory
```powershell
cd "D:\EcoCycle AI"
```

### Step 2: (Optional / Recommended) Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Verify Environment Settings
The prototype comes pre-configured to use the persistent SQLite database out-of-the-box:
- Database location: `D:\EcoCycle AI\data\ecocycle_dev.db`
- If you wish to customize ports or CORS origins, edit [.env](file:///d:/EcoCycle%20AI/.env).

### Step 5: Start the Development Server
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 5. API Documentation & Interactive Exploration

Once running, access the interactive docs in your browser:
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI Schema**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 6. Complete API Catalog (29 Endpoints)

| Pillar / Group | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **System** | `GET` | `/` | API root summary and directory |
| **System** | `GET` | `/health` | High-level application health overview |
| **System** | `GET` | `/api/v1/health` | Versioned health diagnostics |
| **System** | `GET` | `/api/v1/health/db` | Database connectivity & PostGIS probe |
| **System** | `GET` | `/api/v1/health/live` | Container liveness check |
| **System** | `GET` | `/api/v1/health/ready` | Readiness check |
| **Pillar 1: Waste** | `POST` | `/api/v1/waste-reports` | Log waste report across 4 streams |
| **Pillar 1: Waste** | `GET` | `/api/v1/waste-reports` | List reports with category/status/ward filters |
| **Pillar 1: Waste** | `GET` | `/api/v1/waste-reports/{id}` | Get report by ID |
| **Pillar 1: Waste** | `PATCH`| `/api/v1/waste-reports/{id}` | Update report status or weight |
| **Pillar 1: EcoPass**| `POST` | `/api/v1/ecopass` | Provision household EcoPass identity |
| **Pillar 1: EcoPass**| `GET` | `/api/v1/ecopass/{id}` | View EcoPass balance and profile |
| **Pillar 1: EcoPass**| `GET` | `/api/v1/ecopass/{id}/transactions`| Immutable ledger transaction history |
| **Pillar 2: Pickups**| `POST` | `/api/v1/pickups` | Schedule pickup for a waste report |
| **Pillar 2: Pickups**| `GET` | `/api/v1/pickups` | List collection pickups |
| **Pillar 2: Pickups**| `GET` | `/api/v1/pickups/{id}` | Get pickup details with verification |
| **Pillar 2: Pickups**| `PATCH`| `/api/v1/pickups/{id}/status` | Progress pickup status |
| **Pillar 2: EcoProof**| `POST` | `/api/v1/pickups/{id}/verify` | Verify collection, issue SHA-256 hash & EcoCredits |
| **Pillar 3: C&D** | `POST` | `/api/v1/cd-waste/estimates` | Formula-based volume & tonnage estimate |
| **Pillar 3: C&D** | `GET` | `/api/v1/cd-waste/estimates` | List historical C&D volume estimates |
| **Pillar 3: C&D** | `POST` | `/api/v1/cd-waste/materials` | List salvageable building materials |
| **Pillar 3: C&D** | `GET` | `/api/v1/cd-waste/materials` | Browse salvageable materials with filters |
| **Pillar 3: C&D** | `GET` | `/api/v1/cd-waste/materials/{id}`| Get material listing details |
| **Pillar 3: C&D** | `PATCH`| `/api/v1/cd-waste/materials/{id}/status`| Update material status (reserved/collected) |
| **Pillar 4: Circular**| `POST` | `/api/v1/circular/listings` | Publish reuse resale or community donation |
| **Pillar 4: Circular**| `GET` | `/api/v1/circular/listings` | Browse circular items |
| **Pillar 4: Circular**| `GET` | `/api/v1/circular/listings/{id}` | Get circular item details |
| **Pillar 4: Circular**| `POST` | `/api/v1/circular/listings/{id}/claim` | Claim item & award 50 EcoCredits to donor |
| **Pillar 5: Fleet** | `GET` | `/api/v1/fleet/priority-queue` | Multi-factor risk-scored collection queue |
| **Pillar 5: Municipal**| `GET` | `/api/v1/municipal/dashboard` | Live dashboard metrics computed from DB |
| **Pillar 5: Voice** | `GET` | `/api/v1/voice/instructions` | Localized rules (en, hi, kn, ta, te, mr) |
| **Pillar 5: Voice** | `GET` | `/api/v1/voice/bhashini/status` | MeitY Bhashini integration interface status |

---

## 7. Step-by-Step Demo Workflow

You can demonstrate the entire circular flow via Swagger UI or PowerShell `curl`/`Invoke-RestMethod`:

### Step A: Register an EcoPass Identity
```bash
POST /api/v1/ecopass
{
  "household_name": "Narayanan Household",
  "ward_number": "104",
  "address": "Flat 302, Palm Meadows, Ward 104"
}
```
*Response returns:* `ecopass_id: "ECOPASS-W104-..."`, `balance_ecocredits: 0`.

### Step B: Log a Segregated Waste Report
```bash
POST /api/v1/waste-reports
{
  "category": "wet_organic",
  "description": "Daily vegetable peels and meal leftovers",
  "latitude": 12.9716,
  "longitude": 77.5946,
  "ward_number": "104",
  "ecopass_id": "<YOUR_ECOPASS_ID>",
  "estimated_weight_kg": 4.5
}
```

### Step C: Schedule & Verify Pickup (EcoProof)
1. **Schedule Pickup**: `POST /api/v1/pickups` with `report_id`.
2. **Verify Handover**:
```bash
POST /api/v1/pickups/{pickup_id}/verify
{
  "actual_weight_kg": 4.8,
  "stream_confirmed": "wet_organic",
  "collector_signature_id": "STAFF-8842",
  "notes": "Clean source segregation in compostable bin liner"
}
```
*Result:* Returns a 64-character SHA-256 `integrity_hash`, records status `completed`, and awards 48 EcoCredits to the household.

### Step D: Check EcoCredits Balance & Ledger
```bash
GET /api/v1/ecopass/{ecopass_id}
GET /api/v1/ecopass/{ecopass_id}/transactions
```
*Result:* Balance reflects 48 EcoCredits with an audit record tagged `pickup_reward`.

### Step E: Calculate Construction & Demolition Debris Volume
```bash
POST /api/v1/cd-waste/estimates
{
  "project_name": "Basement Excavation & Wall Demolition",
  "location": "Site 12, Indiranagar",
  "material_type": "concrete_rubble",
  "length_m": 8.0,
  "width_m": 3.0,
  "height_m": 1.5
}
```
*Result:* Automatically computes 36.0 $m^3$, 54,000.0 kg (54.0 metric tons) with standard concrete bulk density (1500 kg/m³).

### Step F: Circular Item Donation & Diversion
1. **List item**: `POST /api/v1/circular/listings` with `listing_type: "donation"` and your `ecopass_id`.
2. **Claim item**: `POST /api/v1/circular/listings/{id}/claim` with `claimer_name: "Community Center"`.
*Result:* Awards 50 diversion EcoCredits to your EcoPass ledger.

### Step G: Inspect Fleet Priority Queue & Municipal Dashboard
1. `GET /api/v1/fleet/priority-queue`: Shows hazardous waste automatically sorted to the top tier (`URGENT`).
2. `GET /api/v1/municipal/dashboard`: Displays live aggregate counts for waste streams, total kilograms verified, and circulating credits.

---

## 8. Running Automated Tests

All tests run in complete isolation with an in-memory SQLite fixture (leaving prototype data untouched):

```powershell
python -m pytest -v
```

**Results:**
```
============================= 30 passed in 0.43s ==============================
```

---

## 9. Known Limitations & Integrity Boundaries

In accordance with good engineering ethics and project guidelines:
1. **Image Classification**: No AI vision model (YOLOv8-Seg or MobileNet) is integrated yet. Image URLs are stored as metadata.
2. **EcoProof Cryptographic Hash**: The SHA-256 digest guarantees **record immutability and tamper-detection**. It proves that the digital record has not been altered after creation; it does not constitute physical proof that a collection occurred in the physical world.
3. **C&D Volumetric Estimation**: Calculations use **geometric formula bounding boxes** ($L \times W \times H \times \text{bulk density}$). They are not 3D point cloud or AI depth camera scans.
4. **NGO Partnerships**: Community recipient fields in circular donations are prototype placeholders, not verified statutory government NGO partners.
5. **Fleet Routing**: Prioritization is performed using a **deterministic multi-factor heuristic** based on stream risk, aging duration, and mass density. It does not use Google OR-Tools or active GPS telemetry in this prototype.
6. **Voice Accessibility**: Multilingual instructions are stored regional guidelines. The MeitY Bhashini integration interface reports `unconfigured` until valid API credentials are supplied in `.env`.
