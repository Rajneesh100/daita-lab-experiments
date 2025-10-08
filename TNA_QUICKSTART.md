# TNA Plan Mapper - Quick Start Guide

Complete solution for mapping Excel TNA plans to structured dashboards.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌──────────────┐
│  React Frontend │ ◄─────► │  FastAPI Backend │ ◄─────► │   MongoDB    │
│   (Port 3000)   │         │   (Port 8000)    │         │ (Port 27017) │
└─────────────────┘         └──────────────────┘         └──────────────┘
```

## Prerequisites

- Node.js 14+
- Python 3.8+
- MongoDB
- npm/yarn

## Setup Instructions

### 1. Start MongoDB

```bash
docker run --name mongodb-tna \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=secret \
  -d mongo
```

### 2. Start Backend

```bash
# Navigate to backend directory
cd /Users/rajneesh.kumar/Desktop/llm_games/parser/tna

# Install dependencies (if not already installed)
pip install fastapi uvicorn pymongo pandas openpyxl python-multipart

# Start server
uvicorn app:app --reload --port 8000
```

Backend will be available at: `http://localhost:8000`
API docs: `http://localhost:8000/docs`

### 3. Start Frontend

```bash
# Navigate to frontend directory
cd /Users/rajneesh.kumar/Desktop/llm_games/tna_frontend

# Install dependencies (if not already installed)
npm install

# Start development server
npm start
```

Frontend will open at: `http://localhost:3000`

## Usage Flow

### Step 1: Upload Excel File
1. Open `http://localhost:3000`
2. Click "Choose Excel File"
3. Select your TNA Excel sheet (.xlsx or .xls)
4. Click "Upload and Continue"

### Step 2: Configure Data Start Row
1. Enter the row number where actual data begins (0-indexed)
2. Example: If headers are in rows 0-1 and data starts at row 2, enter `2`

### Step 3: Tag Identifier Columns (Required)
Click on header cells to tag:
- **IO**: Internal Order ID column
- **Style**: Style identifier column
- **Color**: Color identifier column

### Step 4: Tag Stage/Item Columns
For each stage column (e.g., "VAP", "WASHING"):

**For Stage-Level Parameters** (e.g., "SUPPLIER"):
- Click the cell
- Select "Stage / Item"
- Enter Stage Name (or use column name)
- Leave Item section empty
- Save

**For Item Deadlines** (e.g., "VAP SEND", "WASHING DATE"):
- Click the cell
- Select "Stage / Item"
- Enter Stage Name
- Check "Add Item"
- Enter Item Name
- Check "This column contains planned dates"
- Save

### Step 5: Save and Extract
1. Click "Save Mapping" to save your configuration
2. Click "Extract & Create Dashboard" to process the data
3. Dashboard will be created in MongoDB

## Example Tagging

### Excel Structure:
```
Row 0: [IO, Style, Color, VAP,      VAP,       WASHING,      ...]
Row 1: [  ,      ,      , SUPPLIER, VAP SEND, WASHING DATE, ...]
Row 2+: Data rows...
```

### Tagging Configuration:

| Column | Row | Tag Type | Stage Name | Item Name | Planned Date |
|--------|-----|----------|------------|-----------|--------------|
| 0 | 0 | io | - | - | - |
| 1 | 0 | style | - | - | - |
| 2 | 0 | color | - | - | - |
| 3 | 1 | stage | VAP | - | - |
| 4 | 1 | item | VAP | VAP SEND | ✓ |
| 5 | 1 | item | WASHING | WASHING DATE | ✓ |

### Result:
```json
{
  "name": "example",
  "order_id": "example.xlsx",
  "tna_items": [
    {
      "io": "IO123",
      "style": "StyleA",
      "color": "Red",
      "stages": [
        {
          "id": 1,
          "name": "VAP",
          "items": [
            {
              "name": "VAP SEND",
              "start_date": "2024-01-15"
            }
          ],
          "parameters": {
            "SUPPLIER": "Supplier Name"
          }
        },
        {
          "id": 2,
          "name": "WASHING",
          "items": [
            {
              "name": "WASHING DATE",
              "start_date": "2024-01-20"
            }
          ]
        }
      ]
    }
  ]
}
```

## Key Features

### Merged Cell Handling
- Excel merged cells are automatically handled
- io, style, color values are forward-filled for combined rows

### Stage Ordering
- Stages are automatically ordered by column position
- Incremental IDs assigned (1, 2, 3, ...)

### Smart Suggestions
- Recently used stage names appear as suggestions
- Last 2 distinct stages shown for quick selection

### Validation
- Ensures io, style, color are tagged
- Validates at least one stage is configured
- Checks required item fields when item is added

## Troubleshooting

### Backend Not Starting
```bash
# Check if port 8000 is available
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

### Frontend Not Starting
```bash
# Check if port 3000 is available
lsof -i :3000

# Kill process if needed
kill -9 <PID>
```

### MongoDB Connection Failed
```bash
# Check if MongoDB is running
docker ps | grep mongodb-tna

# Restart if needed
docker restart mongodb-tna
```

### Excel Upload Fails
- Verify file is .xlsx or .xls format
- Check file size (very large files may timeout)
- Ensure backend is running

### Extraction Fails
- Verify io, style, color are tagged
- Check data start row is correct
- Ensure at least one stage is configured
- Check console for detailed error messages

## API Testing

### Test Backend Health
```bash
curl http://localhost:8000/docs
```

### Test Upload
```bash
curl -X POST http://localhost:8000/upload-excel \
  -F "file=@path/to/your/file.xlsx"
```

### View Dashboards in MongoDB
```bash
# Connect to MongoDB
docker exec -it mongodb-tna mongosh -u admin -p secret

# Switch to database
use tracking_db

# View dashboards
db.dashboards.find().pretty()

# View mappings
db.column_mappings.find().pretty()
```

## Directory Structure

```
llm_games/
├── tna_frontend/              # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileUpload.tsx
│   │   │   ├── ExcelViewer.tsx
│   │   │   └── TaggingModal.tsx
│   │   ├── App.tsx
│   │   └── App.css
│   └── package.json
│
└── parser/tna/                # FastAPI backend
    ├── app.py                 # Main API
    ├── tna_parser.py          # Excel converter
    ├── xlsheets/              # Source Excel files
    ├── xlsump/                # Uploaded files
    └── csvfiles/              # Converted CSVs
```

## Next Steps

1. Upload your first TNA Excel sheet
2. Tag the columns according to your structure
3. Extract and verify the dashboard in MongoDB
4. Customize the tagging for your specific needs
5. Process multiple Excel files

## Support

For issues or questions:
1. Check backend logs in terminal
2. Check frontend console in browser (F12)
3. Review API docs at `http://localhost:8000/docs`
4. Check MongoDB data for verification

## Tips

- Save mapping frequently to avoid losing work
- Use column names as default for consistency
- Test with a small Excel file first
- Verify data start row before tagging
- Check extracted data in MongoDB before processing large files

Happy mapping! 🎉
