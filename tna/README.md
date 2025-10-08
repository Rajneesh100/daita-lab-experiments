# TNA Plan Mapper - Backend API

FastAPI backend for processing TNA (Time and Action) plan Excel sheets and creating structured dashboards.

## Features

- **Excel Upload & Storage**: Upload and store Excel files
- **Column Mapping**: Save and retrieve column-to-field mappings
- **Data Extraction**: Process Excel data using saved mappings
- **Merged Cell Handling**: Automatically handles merged cells in Excel
- **Dashboard Creation**: Creates structured TNA dashboards in MongoDB
- **CORS Enabled**: Frontend-ready with CORS middleware

## Tech Stack

- FastAPI
- MongoDB (PyMongo)
- Pandas (Excel processing)
- Python 3.8+

## Installation

### Prerequisites

- Python 3.8+
- MongoDB running on `localhost:27017`
- Virtual environment (recommended)

### Setup

```bash
cd parser/tna
pip install fastapi uvicorn pymongo pandas openpyxl python-multipart
```

### MongoDB Setup

```bash
# Start MongoDB with Docker
docker run --name mongodb-tna -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=secret -d mongo

# Or use existing MongoDB instance
```

### Running the Server

```bash
cd parser/tna
uvicorn app:app --reload --port 8000
```

Server will start at `http://localhost:8000`

## API Endpoints

### 1. Upload Excel File

```http
POST /upload-excel
Content-Type: multipart/form-data

Body: file (Excel file)
```

**Response:**
```json
{
  "file_id": "uuid",
  "filename": "example.xlsx",
  "rows": 100,
  "columns": 20,
  "data": [[...], ...],
  "message": "File uploaded successfully"
}
```

### 2. Get Excel Data

```http
GET /excel/{file_id}?start_row=0&end_row=100
```

**Response:**
```json
{
  "file_id": "uuid",
  "filename": "example.xlsx",
  "total_rows": 100,
  "total_columns": 20,
  "data": [[...], ...]
}
```

### 3. Save Column Mapping

```http
POST /save-mapping
Content-Type: application/json

Body:
{
  "file_id": "uuid",
  "filename": "example.xlsx",
  "data_start_row": 2,
  "tags": [
    {
      "column_index": 0,
      "column_name": "IO",
      "tag_type": "io"
    },
    {
      "column_index": 3,
      "column_name": "VAP SEND",
      "tag_type": "item",
      "stage_name": "VAP",
      "stage_config": {
        "parameter_name": "VAP SEND",
        "deadline": "2024-12-31"
      },
      "item_config": {
        "name": "VAP SEND",
        "is_planned_date": true,
        "status": "ongoing"
      }
    }
  ]
}
```

**Response:**
```json
{
  "message": "Mapping saved successfully",
  "file_id": "uuid"
}
```

### 4. Get Saved Mapping

```http
GET /get-mapping/{file_id}
```

**Response:**
```json
{
  "file_id": "uuid",
  "filename": "example.xlsx",
  "data_start_row": 2,
  "tags": [...]
}
```

### 5. Extract and Create Dashboard

```http
POST /extract-and-create-dashboard/{file_id}
```

**Response:**
```json
{
  "message": "Dashboard created successfully from Excel",
  "dashboard_id": "mongodb_id",
  "tna_count": 50,
  "dashboard": {
    "name": "example",
    "order_id": "example.xlsx",
    "tna_items": [...]
  }
}
```

### 6. Create Dashboard (Direct)

```http
POST /dashboards
Content-Type: application/json

Body:
{
  "name": "Dashboard Name",
  "order_id": "ORDER123",
  "tna_items": [...]
}
```

## Data Models

### Dashboard
```python
{
  "name": str,
  "order_id": str,
  "tna_items": List[TNA]
}
```

### TNA
```python
{
  "io": str,              # Internal Order ID
  "style": str,           # Style identifier
  "color": str,           # Color identifier
  "stages": List[Stage],
  "start_date": str,
  "end_date": str,
  "status": str,
  "top_manager_contacts": List[str],
  "original_pdf_urls": List[str],
  "context": List[Message],
  "created_by": str
}
```

### Stage
```python
{
  "id": int,
  "name": str,
  "items": List[Item],
  "start_date": str,
  "deadline": str,
  "expected_delivery_date": str,
  "parameters": Dict[str, str],  # Stage-level data
  "manager": str,
  "top_manager": str,
  "context": List[Message]
}
```

### Item
```python
{
  "name": str,
  "start_date": str,
  "end_date": str,
  "actual_delivery_date": str,
  "status": str,
  "contact": str,
  "context": List[Message]
}
```

### ColumnTag
```python
{
  "column_index": int,
  "column_name": str,
  "tag_type": str,        # "io", "style", "color", "stage", "item"
  "stage_name": str,      # Optional
  "stage_config": dict,   # Optional
  "item_config": dict     # Optional
}
```

## Data Extraction Logic

### 1. Merged Cell Handling
- Uses pandas `ffill()` to forward-fill merged cells
- Ensures each row has complete io, style, color values

### 2. Stage Grouping
- Groups column tags by stage_name
- Assigns incremental IDs based on column order

### 3. Item vs Parameter Detection
- If `item_config.name` exists → Creates Item
- Otherwise → Adds to stage parameters

### 4. Planned Date Mapping
- If `is_planned_date=true` → Maps column value to item start_date
- Otherwise → Uses configured dates

### 5. TNA Creation
- Each unique (io, style, color) → One TNA item
- Skips rows with missing identifiers

## Directory Structure

```
parser/tna/
├── app.py              # Main FastAPI application
├── tna_parser.py       # Excel to CSV converter
├── xlsheets/           # Source Excel files
├── xlsump/             # Uploaded Excel files
├── csvfiles/           # Converted CSV files
└── README.md           # This file
```

## MongoDB Collections

### dashboards
Stores created dashboards with TNA items

### column_mappings
Stores column mapping configurations for uploaded files

## Error Handling

- File validation (Excel format only)
- Missing required tags validation
- File not found errors
- MongoDB connection errors
- Data extraction errors with detailed messages

## Configuration

### MongoDB Connection
```python
# Uses environment variables for security
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
MONGODB_USER = os.getenv("MONGODB_USER", "admin")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD", "secret")
```

### Upload Directory
```python
UPLOAD_DIR = Path("xlsump")
```

### CORS Settings
```python
allow_origins=["*"]  # Configure for production
```

## Testing

### Test Upload
```bash
curl -X POST http://localhost:8000/upload-excel \
  -F "file=@path/to/file.xlsx"
```

### Test Mapping Save
```bash
curl -X POST http://localhost:8000/save-mapping \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "uuid",
    "filename": "test.xlsx",
    "data_start_row": 2,
    "tags": [...]
  }'
```

### Test Extraction
```bash
curl -X POST http://localhost:8000/extract-and-create-dashboard/uuid
```

## Troubleshooting

### Excel Reading Issues
- Install openpyxl: `pip install openpyxl`
- Check file format (.xlsx vs .xls)

### MongoDB Connection Failed
- Verify MongoDB is running
- Check connection string
- Verify credentials

### Extraction Fails
- Check mapping has io, style, color tags
- Verify data_start_row is correct
- Check for empty required fields

## Future Enhancements

- File cleanup (delete old uploads)
- Mapping templates
- Validation preview before extraction
- Bulk file processing
- Export dashboards to Excel
- Advanced date parsing
- Custom field mappings
- Webhook notifications

## API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI)

Visit `http://localhost:8000/redoc` for alternative API documentation (ReDoc)
