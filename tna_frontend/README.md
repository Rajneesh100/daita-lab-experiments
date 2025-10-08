# TNA Plan Mapper - Frontend

A React TypeScript application for mapping Excel TNA (Time and Action) plans to a structured dashboard format.

## Features

- **Excel Upload**: Upload TNA plan Excel sheets (.xlsx, .xls)
- **Interactive Viewer**: View Excel data with merged cell support
- **Column Tagging**: Click on header cells to tag them with:
  - **Identifiers**: io, style, color
  - **Stages**: Configure stage-level parameters
  - **Items**: Configure item-level deadlines and tasks
- **Smart Suggestions**: Recently used stages appear as suggestions
- **Validation**: Ensures required fields are tagged before extraction
- **Data Extraction**: Backend processes tagged data and creates dashboard entries

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- Backend API running on `http://localhost:8000`

### Installation

```bash
cd tna_frontend
npm install
```

### Running the Application

```bash
npm start
```

The application will open at `http://localhost:3000`

## Usage Workflow

### 1. Upload Excel File
- Click "Choose Excel File" and select your TNA plan
- Click "Upload and Continue"

### 2. Specify Data Start Row
- Enter the row number (0-indexed) where actual data begins
- Rows before this are treated as headers for tagging

### 3. Tag Columns

#### Identifier Tags (Required)
Click on header cells and tag:
- **IO**: Internal Order ID column
- **Style**: Style column
- **Color**: Color column

#### Stage/Item Tags
For each column representing a stage or item:

**Stage Configuration (Mandatory)**:
- **Name**: Use column name or enter custom (REQUIRED)
- **Start Date**: Optional
- **Deadline**: Optional
- **Expected Delivery Date**: Optional
- **Parameter Name**: For stage-level data storage
- **Manager**: Optional
- **Top Manager**: Optional

**Item Configuration (Optional)**:
- **Add Item**: Check if this column represents an item
- **Name**: Use column name or enter custom (REQUIRED if item added)
- **Planned Date**: Check if column contains date values (REQUIRED if item added)
- **Start/End Date**: If not using column dates
- **Status**: ongoing, completed, pending, delayed
- **Contact**: Contact person

### 4. Save Mapping
- Click "Save Mapping" to save your column configuration
- Mapping is stored and can be reloaded

### 5. Extract and Create Dashboard
- Click "Extract & Create Dashboard"
- Backend processes the Excel file using your mapping
- Creates TNA items for each unique (io, style, color) combination
- Saves to MongoDB

## Tag Types

### Identifier Tags
- `io`: Internal Order ID
- `style`: Style identifier
- `color`: Color identifier

### Stage/Item Tags
- **Stage-only**: Column contains stage-level parameters (e.g., "SUPPLIER")
- **Stage + Item**: Column contains item deadlines (e.g., "VAP SEND")

## Data Structure

### Input (Excel)
```
Row 0: [VAP, VAP, VAP, WASHING, ...]
Row 1: [SUPPLIER, VAP SEND, ..., WASHING DATE, ...]
Row 2+: Data rows with io, style, color, and values
```

### Output (Dashboard)
```json
{
  "name": "filename",
  "order_id": "filename.xlsx",
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
              "start_date": "2024-01-15",
              ...
            }
          ],
          "parameters": {
            "SUPPLIER": "Supplier Name"
          }
        }
      ]
    }
  ]
}
```

## API Endpoints Used

- `POST /upload-excel`: Upload Excel file
- `GET /excel/{file_id}`: Get Excel data
- `POST /save-mapping`: Save column mapping
- `GET /get-mapping/{file_id}`: Load saved mapping
- `POST /extract-and-create-dashboard/{file_id}`: Extract and create dashboard

## Components

- **App.tsx**: Main application component
- **FileUpload.tsx**: File upload interface
- **ExcelViewer.tsx**: Excel data viewer with tagging
- **TaggingModal.tsx**: Modal for configuring column tags

## Styling

- Modern, clean UI with color-coded tags
- Responsive design
- Interactive hover states
- Clear visual feedback for tagged columns

## Error Handling

- File type validation
- Required field validation
- API error messages
- User-friendly error displays

## Notes

- Merged cells in Excel are handled by forward-filling values
- Stages are ordered by column position (incremental IDs)
- Multiple contexts from different tagging sessions are merged
- Data extraction happens on the backend for efficiency

## Troubleshooting

### Backend Connection Issues
- Ensure backend is running on `http://localhost:8000`
- Check CORS settings if requests fail

### Excel Upload Fails
- Verify file is .xlsx or .xls format
- Check file size (large files may take longer)

### Extraction Fails
- Ensure io, style, and color are tagged
- Verify at least one stage is configured
- Check data start row is correct

## Future Enhancements

- Drag-and-drop file upload
- Preview extracted data before saving
- Edit existing mappings
- Export mapping templates
- Batch processing multiple files