# Pocket CFO Parser

Pocket CFO Parser is a comprehensive financial data parsing service. It extracts structured transaction mappings seamlessly from unformatted text sources like Indian Bank SMS notifications and bank statement PDFs.

Parsed transaction data is automatically categorized, mapped to a unified internal schema, and securely stored into a MongoDB database with native deduplication. 

## 🌟 Key Features

- **Robust SMS Parsing**: Intelligent text-scraping to intercept, parse, and identify relevant UPI, Credit, and Debit SMS records. Built to recognize dynamic formats spanning major Indian banks (SBI, HDFC, ICICI, Axis, Kotak).
- **Tabular PDF Extractions**: Deep structural mapping of tabular structures inside Bank Statement PDFs (Customized for HDFC & SBI variants).
- **Universal Transaction Model**: Aggregates multi-source data (SMS/PDF) into a single, unified `Transaction` dataclass ensuring normalized analytics downstream.
- **Advanced Deduplication**: Auto-generates unique SHA256 string signatures based on intrinsic transaction traits (amount, date, party combination) to eliminate identical duplicate entries dynamically during database upsert operations.
- **Unified MongoDB Infrastructure**: Ships ready to ingest user-specific streams into pre-configured MongoDB databases using `pymongo`.

## 🛠️ Technology Stack

- **Python 3.10+**
- **pdfplumber:** Handling tabular data extraction from PDFs without visual degradation.
- **python-dateutil:** For robust string parsing into precise datetimes formats.
- **pymongo & python-dotenv:** Cloud and local MongoDB integrations.
- **pytest:** Bulletproof test infrastructures.

## 🚀 Setup Instructions

1. **Clone the repository** inside your development workspace.
2. **Setup virtual environment:**
   ```bash
   python -m venv venv
   
   # For Windows
   venv\Scripts\activate
   
   # For Linux/MacOS
   source venv/bin/activate 
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Environment Variables Configs:**
   Replace the `.env` attributes at the root directory of the project with your working MongoDB active connection attributes:
   ```env
   MONGODB_URI=mongodb://localhost:27017
   DB_NAME=pocket_cfo
   ```

## ▶️ Running the Project

> All commands below must be run from the **`hackfest/` root directory** (one level above `pocket-cfo-parser/`).

### Start the Backend (FastAPI)

```bash
cd pocket-cfo-parser && source .venv/Scripts/activate && uvicorn api.main:app --reload --port 8000
```

API will be available at → **http://localhost:8000**  
Swagger docs at → **http://localhost:8000/docs**

### Start the Frontend (Testing Dashboard)

Open a **second terminal** from the `hackfest/` root:

```bash
python -m http.server 5500 --directory frontend
```

Dashboard will be available at → **http://localhost:5500**

### Quick Start (Windows — double-click)

```bash
start.bat
```

Launches both servers and opens Chrome automatically.



```text
pocket-cfo-parser/
├── pocket_cfo_parser/
│   ├── models/            # Core data definitions (Transaction dataclass)
│   ├── parsers/           # Sub-extractor logical routing (sms_parser, pdf_parser)
│   ├── db/                # Database clients, schemas, and query logic (mongo.py)
│   └── ingestion.py       # Main unified data intake interface endpoint
├── tests/
│   ├── test_data/         # Reference text constraints and PDF sample generations
│   ├── test_sms_parser.py # Isolated tests covering SMS parsing variants
│   └── test_pdf_parser.py # Isolated tests validating matrix mapping in PDFs
├── requirements.txt       # Dependencies registry
└── .env                   # Environmental variable footprints
```

## 🧪 Testing

To validate the extractors, execute the pytest suite from the project's root:

```bash
pytest tests/
```

> **Note:** To prevent testing constraints, ensure you first generate the dummy PDF files locally. By running the pre-configured script: `python tests/test_data/create_sample_pdfs.py`
