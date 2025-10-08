# PDF Purchase Order Parser 📄

A full-stack application that extracts structured data from PDF purchase orders using AI and provides a modern dashboard for viewing and filtering orders.

## 🚀 Quick Start

###  Docker (Recommended)

```bash
cd llm_games

# put your gemini api key in docker-compose.prod.yml (search for your_api_key and replace)
docker-compose -f docker-compose.prod.yml up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```


## 🔮 Area of  Improvements

### **Dynamic Schema Architecture**

Instead of fixing the current SQL schema, I would prefer to add another layer which actively decides the schema for any uploaded PDFs and sees if it fits the existing format. If not, use an agent to come up with a new format. 

Rather than using SQL, I'd prefer MongoDB since our schema can't always be predictable - different orders can have different formats. A document database can help tackle this problem and store data in flexible format from different PDFs.

The approach would also change how we handle the frontend - not fetching data in standard format but in document format, using components wisely for showing nested dynamic JSON on the UI. Since our data format is dynamic, the frontend logic should also be fluid.

One idea is to have a UI engine where as we generate a structured format for a new PDF which is new, we also generate a UI blueprint like a tree structure of components. When any data is fetched, this tree structure is also fetched and components are dynamically generated on the UI.

The flow would be: PDF gets uploaded, schema analysis happens, format detection occurs, then document storage. Simultaneously, UI blueprint generation happens, and when data is fetched, the blueprint comes with it to dynamically create the component tree and render the UI.

This approach would handle any purchase order format dynamically, making the system truly universal rather than limited to the current fixed schema.






### Local Development

```bash
# 1. Start PostgreSQL
docker run --name postgres-parser \
  -e POSTGRES_USER=parser \
  -e POSTGRES_PASSWORD=parser123 \
  -e POSTGRES_DB=parser \
  -p 4000:5432 -d postgres

# 2. Create database schema
docker exec -i postgres-parser psql -U parser -d parser < parser/database_schema.sql


# 3. Setup and start backend
cd parser
python3 -m venv parser
source parser/bin/activate
pip install -r requirements.txt
# put your gemini api key in .env (search for your_api_key and replace)
python server.py



# 4. Setup and start frontend (new terminal)
cd frontend
npm install
npm start
```

## 📋 Features

### PDF Processing
- **AI-powered extraction** using Google Gemini
- **Structured data parsing** from purchase order PDFs
- **Automatic data validation** and normalization
- **Duplicate detection** with data override capability

### Dashboard
- **Orders overview** with key metrics
- **Advanced filtering** by model ID, color, size
- **Full-text search** across PO ID, buyer, supplier
- **Sorting** by date, amount, item count
- **Pagination** for both orders and line items

### Data Management
- **PostgreSQL storage** with optimized schema
- **UUID-based primary keys** for scalability
- **Foreign key relationships** with cascade deletes
- **Indexed columns** for fast queries

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React App     │    │   FastAPI       │    │   PostgreSQL    │
│   (Frontend)    │───▶│   (Backend)     │───▶│   (Database)    │
│   Port 3000     │    │   Port 8000     │    │   Port 5432     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Google        │
                       │   Gemini AI     │
                       └─────────────────┘
```

## 📁 Project Structure

```
llm_games/
├── parser/                     # Backend (FastAPI)
│   ├── server.py              # Main API server
│   ├── gemini.py              # AI PDF parsing
│   ├── database.py            # Database operations
│   ├── database_schema.sql    # PostgreSQL schema
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile            # Backend container
├── frontend/                   # Frontend (React)
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── App.js            # Main app
│   │   └── App.css           # Styles
│   ├── package.json          # Node dependencies
│   └── Dockerfile            # Frontend container
├── sample_pdfs/               # Test PDF files
├── docker-compose.yml         # Development setup
├── docker-compose.prod.yml    # Production setup
└── README.md                  # This file
```

## 🔧 API Endpoints

### Upload
- `POST /upload-pdf` - Upload and parse PDF

### Orders
- `GET /orders` - List orders with filtering/pagination
- `GET /orders/{id}` - Get order details with line items

### Utilities
- `GET /filters` - Get available filter options
- `GET /stats` - Get dashboard statistics

### API Documentation
Interactive docs available at: http://localhost:8000/docs

## 🗄️ Database Schema

### Orders Table
- Purchase order information (ID, date, buyer, supplier, totals)
- UUID primary keys for scalability

### Line Items Table
- Individual items with model, color, size, quantity, pricing
- Foreign key relationship to orders with cascade delete

## 🎯 Sample Data

The `sample_pdfs/` directory contains test purchase order PDFs for development and demonstration.



## 🐳 Docker Deployment

### Development
```bash
docker-compose up --build
```

### Production Docker totallay independent
first 
```bash
docker-compose -f docker-compose.prod.yml up -d
```
 
### Docker Hub Images
- Backend: `rajneesh2311/pdf-parser-backend:latest`
- Frontend: `rajneesh2311/pdf-parser-frontend:latest`


### API Test
```bash
# Health check
curl http://localhost:8000/stats

# Upload PDF
curl -X POST "http://localhost:8000/upload-pdf" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample_pdfs/purchase-order.pdf"
```


## ⚠️ Known Limitations

1. **PDF Format Dependency**: Works best with structured purchase order PDFs. Complex layouts or non-standard formats may require prompt adjustments.

2. **AI Parsing Accuracy**: Depends on Google Gemini's interpretation. Very complex tables or poor scan quality may result in parsing errors.

3. **Single File Processing**: Currently processes one PDF at a time. Batch processing would require additional implementation.

4. **No User Authentication**: Currently open access. Production deployment should add authentication/authorization.

## 📄 License

MIT License - See LICENSE file for details

## 👨‍💻 Author

Built with using FastAPI, React, PostgreSQL, and Google Gemini AI.