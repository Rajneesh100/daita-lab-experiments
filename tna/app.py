from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pymongo import MongoClient
import pandas as pd
import os
import json
from pathlib import Path

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
MONGODB_USER = os.getenv("MONGODB_USER", "admin")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD", "secret")

# Build connection string
if MONGODB_USER and MONGODB_PASSWORD:
    MONGODB_CONNECTION = f"mongodb://{MONGODB_USER}:{MONGODB_PASSWORD}@{MONGODB_URL.replace('mongodb://', '')}"
else:
    MONGODB_CONNECTION = MONGODB_URL

client = MongoClient(MONGODB_CONNECTION)
db = client["tracking_db"]
collection = db["dashboards"]
mappings_collection = db["column_mappings"]

app = FastAPI(title="Tracking Dashboard API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory
UPLOAD_DIR = Path("xlsump")
UPLOAD_DIR.mkdir(exist_ok=True)

# ---- Pydantic Models ----
class Message(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user: str
    text: str

class Item(BaseModel):
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    actual_delivery_date: Optional[str] = None
    status: Optional[str] = "ongoing"
    contact: Optional[str] = None
    context: Optional[List[Message]] = []

class Stage(BaseModel):
    id: int
    name: str
    items: List[Item] = []
    start_date: Optional[str] = None
    deadline: Optional[str] = None
    expected_delivery_date: Optional[str] = None
    parameters: Dict[str, str] = {} # New field for the map
    manager: Optional[str] = None
    top_manager: Optional[str] = None
    context: Optional[List[Message]] = []

class tna(BaseModel):
    io: str       # internal order id for tracking chunks of order placed by cutomer 
    style: str    
    color: str
    stages: List[Stage] = []
    start_date: str
    end_date: str
    status: Optional[str] = "ongoing"
    top_manager_contacts: Optional[List[str]] = []
    original_pdf_urls: Optional[List[str]] = []
    context: Optional[List[Message]] = []
    created_by: Optional[str] = None

class Dashboard(BaseModel):
    name: str
    order_id: str # original order id placed by customer, keep xlsheet name as order_id as of now
    tna_items: List[tna] = []

# ---- Column Mapping Models ----
class ColumnTag(BaseModel):
    column_index: int
    column_name: str
    tag_type: str  # "io", "style", "color", "stage", "item"
    stage_name: Optional[str] = None
    stage_config: Optional[Dict[str, Any]] = None  # For stage-level configs
    item_config: Optional[Dict[str, Any]] = None   # For item-level configs

class ColumnMapping(BaseModel):
    file_id: str
    filename: str
    data_start_row: int  # Row number where actual data starts
    tags: List[ColumnTag] = []

# ---- API Routes ----

@app.post("/dashboards")
def create_dashboard(dashboard: Dashboard):
    
    # let's ignore the duplicate check for now
    
    # # Check if any style in the styles array is already part of another tracking for the same order_id
    # for style in dashboard.styles:
    #     existing_with_style = collection.find_one({
    #         "order_id": dashboard.order_id,
    #         "styles": {"$in": [style]},
    #     })
    #     if existing_with_style:
    #         raise HTTPException(
    #             status_code=400, 
    #             detail=f"Style '{style}' is already being tracked for order_id '{dashboard.order_id}' in another dashboard"
    #         )
    
    # # Check if dashboard with same order_id and exact same styles already exists
    # existing_exact = collection.find_one({"order_id": dashboard.order_id, "styles": dashboard.styles})
    # if existing_exact:
    #     raise HTTPException(status_code=400, detail="Dashboard with this order_id and exact same styles already exists")

    doc = dashboard.dict()
    result = collection.insert_one(doc)
    return {"message": "Dashboard created", "id": str(result.inserted_id)}

@app.post("/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    """Upload an Excel file and return its structure"""
    try:
        # Validate file extension
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")
        
        # Generate unique file ID
        import uuid
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
        
        # Save file
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Read Excel file to get structure
        df = pd.read_excel(file_path, header=None)
        
        # Convert to list of lists for frontend
        data = df.values.tolist()
        
        # Handle NaN values
        for i in range(len(data)):
            for j in range(len(data[i])):
                if pd.isna(data[i][j]):
                    data[i][j] = ""
        
        return {
            "file_id": file_id,
            "filename": file.filename,
            "rows": len(data),
            "columns": len(data[0]) if data else 0,
            "data": data[:50],  # Return first 50 rows for preview
            "message": "File uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/excel/{file_id}")
async def get_excel_data(file_id: str, start_row: int = 0, end_row: int = 100):
    """Get Excel data for a specific file"""
    try:
        # Find file
        files = list(UPLOAD_DIR.glob(f"{file_id}_*"))
        if not files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = files[0]
        
        # Read Excel file
        df = pd.read_excel(file_path, header=None)
        data = df.values.tolist()
        
        # Handle NaN values
        for i in range(len(data)):
            for j in range(len(data[i])):
                if pd.isna(data[i][j]):
                    data[i][j] = ""
        
        return {
            "file_id": file_id,
            "filename": file_path.name.replace(f"{file_id}_", ""),
            "total_rows": len(data),
            "total_columns": len(data[0]) if data else 0,
            "data": data[start_row:end_row]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@app.post("/save-mapping")
async def save_mapping(mapping: ColumnMapping):
    """Save column mapping configuration"""
    try:
        # Check if mapping already exists
        existing = mappings_collection.find_one({"file_id": mapping.file_id})
        
        if existing:
            # Update existing mapping
            mappings_collection.update_one(
                {"file_id": mapping.file_id},
                {"$set": mapping.dict()}
            )
            message = "Mapping updated successfully"
        else:
            # Insert new mapping
            mappings_collection.insert_one(mapping.dict())
            message = "Mapping saved successfully"
        
        return {"message": message, "file_id": mapping.file_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving mapping: {str(e)}")

@app.get("/get-mapping/{file_id}")
async def get_mapping(file_id: str):
    """Get saved column mapping for a file"""
    try:
        mapping = mappings_collection.find_one({"file_id": file_id})
        
        if not mapping:
            return {"file_id": file_id, "tags": [], "data_start_row": 2}
        
        # Remove MongoDB _id field
        mapping.pop('_id', None)
        return mapping
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving mapping: {str(e)}")

@app.post("/extract-and-create-dashboard/{file_id}")
async def extract_and_create_dashboard(file_id: str):
    """Extract data from Excel using saved mapping and create dashboard"""
    try:
        # Get mapping
        mapping = mappings_collection.find_one({"file_id": file_id})
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found. Please tag columns first.")
        
        # Find file
        files = list(UPLOAD_DIR.glob(f"{file_id}_*"))
        if not files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = files[0]
        filename = file_path.name.replace(f"{file_id}_", "")
        
        # Read Excel file
        df = pd.read_excel(file_path, header=None)
        
        # Extract data starting from specified row
        data_start_row = mapping.get("data_start_row", 2)
        data_df = df.iloc[data_start_row:]
        
        # Handle merged cells by forward filling
        data_df = data_df.ffill()
        data_df = data_df.infer_objects(copy=False)
        
        # Get column tags
        tags = mapping.get("tags", [])
        
        # Find io, style, color column indices
        io_col = next((tag["column_index"] for tag in tags if tag["tag_type"] == "io"), None)
        style_col = next((tag["column_index"] for tag in tags if tag["tag_type"] == "style"), None)
        color_col = next((tag["column_index"] for tag in tags if tag["tag_type"] == "color"), None)
        
        if io_col is None or style_col is None or color_col is None:
            raise HTTPException(status_code=400, detail="Missing required tags: io, style, and color must be tagged")
        
        # Group tags by stage
        stage_tags = {}
        for tag in tags:
            if tag.get("stage_name"):
                stage_name = tag["stage_name"]
                if stage_name not in stage_tags:
                    stage_tags[stage_name] = []
                stage_tags[stage_name].append(tag)
        
        # Create TNA items
        tna_items = []
        
        for idx, row in data_df.iterrows():
            io_value = str(row.iloc[io_col]) if pd.notna(row.iloc[io_col]) else ""
            style_value = str(row.iloc[style_col]) if pd.notna(row.iloc[style_col]) else ""
            color_value = str(row.iloc[color_col]) if pd.notna(row.iloc[color_col]) else ""
            
            if not io_value or not style_value or not color_value:
                continue
            
            # Create stages for this TNA
            stages = []
            stage_id = 1
            
            for stage_name, stage_tag_list in stage_tags.items():
                # Get stage configuration from first tag
                stage_config = stage_tag_list[0].get("stage_config", {})
                
                # Create items for this stage
                items = []
                stage_parameters = {}
                stage_contexts = []
                
                for tag in stage_tag_list:
                    col_idx = tag["column_index"]
                    col_value = str(row.iloc[col_idx]) if pd.notna(row.iloc[col_idx]) else ""
                    
                    # Check if this is an item or stage parameter
                    item_config = tag.get("item_config")
                    
                    if item_config and item_config.get("name"):
                        # This is an item
                        item = {
                            "name": item_config.get("name"),
                            "start_date": col_value if item_config.get("is_planned_date") else item_config.get("start_date"),
                            "end_date": item_config.get("end_date"),
                            "actual_delivery_date": item_config.get("actual_delivery_date"),
                            "status": item_config.get("status", "ongoing"),
                            "contact": item_config.get("contact"),
                            "context": item_config.get("context", [])
                        }
                        items.append(item)
                    else:
                        # This is a stage parameter
                        param_name = tag.get("stage_config", {}).get("parameter_name", tag["column_name"])
                        stage_parameters[param_name] = col_value
                    
                    # Collect contexts
                    if stage_config.get("context"):
                        stage_contexts.extend(stage_config.get("context", []))
                
                stage = {
                    "id": stage_id,
                    "name": stage_name,
                    "items": items,
                    "start_date": stage_config.get("start_date"),
                    "deadline": stage_config.get("deadline"),
                    "expected_delivery_date": stage_config.get("expected_delivery_date"),
                    "parameters": stage_parameters,
                    "manager": stage_config.get("manager"),
                    "top_manager": stage_config.get("top_manager"),
                    "context": stage_contexts
                }
                stages.append(stage)
                stage_id += 1
            
            # Create TNA item
            tna_item = {
                "io": io_value,
                "style": style_value,
                "color": color_value,
                "stages": stages,
                "start_date": "",  # Can be derived from first stage
                "end_date": "",    # Can be derived from last stage
                "status": "ongoing",
                "top_manager_contacts": [],
                "original_pdf_urls": [],
                "context": [],
                "created_by": None
            }
            tna_items.append(tna_item)
        
        # Create dashboard
        dashboard_data = {
            "name": filename.replace(".xlsx", "").replace(".xls", ""),
            "order_id": filename,
            "tna_items": tna_items
        }
        
        # Save to database
        result = collection.insert_one(dashboard_data)
        
        # Remove MongoDB _id from response
        dashboard_data.pop('_id', None)
        
        return {
            "message": "Dashboard created successfully from Excel",
            "dashboard_id": str(result.inserted_id),
            "tna_count": len(tna_items),
            "dashboard": dashboard_data
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error extracting data: {str(e)}")
