from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import tempfile
import os
import uuid
from datetime import datetime
from typing import Optional, List
from dotenv import load_dotenv
from gemini import extract_pdf_data

load_dotenv()  # Load from current directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))  # Load from parent directory

app = FastAPI(title="Purchase Order API", description="API for managing purchase orders")

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get database configuration from environment variables
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "4000")
POSTGRES_USER = os.getenv("POSTGRES_USER", "parser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "parser123")
POSTGRES_DB = os.getenv("POSTGRES_DB", "parser")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

async def save_to_database(parsed_data: dict) -> dict:
    """Save parsed PDF data to PostgreSQL database with UPSERT logic"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        async with conn.transaction():
            # Parse order date
            order_date = None
            if parsed_data.get("order_date"):
                try:
                    order_date = datetime.strptime(parsed_data["order_date"], "%Y-%m-%d").date()
                except:
                    order_date = None
            
            # UPSERT order using ON CONFLICT
            order_id = str(uuid.uuid4())
            upsert_order_query = """
            INSERT INTO orders 
            (id, purchase_order_id, order_date, buyer_name, buyer_address, 
             supplier_name, supplier_address, currency, tax_amount, total_amount)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (purchase_order_id) 
            DO UPDATE SET
                order_date = EXCLUDED.order_date,
                buyer_name = EXCLUDED.buyer_name,
                buyer_address = EXCLUDED.buyer_address,
                supplier_name = EXCLUDED.supplier_name,
                supplier_address = EXCLUDED.supplier_address,
                currency = EXCLUDED.currency,
                tax_amount = EXCLUDED.tax_amount,
                total_amount = EXCLUDED.total_amount,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, (xmax = 0) AS is_new
            """
            
            result = await conn.fetchrow(
                upsert_order_query,
                order_id,
                parsed_data["purchase_order_id"],
                order_date,
                parsed_data["buyer"]["name"],
                parsed_data["buyer"]["address"],
                parsed_data["supplier"]["name"],
                parsed_data["supplier"]["address"],
                parsed_data.get("currency", "USD"),
                parsed_data.get("tax_amount", 0),
                parsed_data["total_amount"]
            )
            
            actual_order_id = result["id"]
            is_duplicate = not result["is_new"]
            
            if is_duplicate:
                await conn.execute("DELETE FROM line_items WHERE order_id = $1", actual_order_id)
            
            line_item_query = """
            INSERT INTO line_items 
            (id, order_id, model_id, item_code, description, color, size, quantity, unit_price, amount, delivery_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """
            
            for item in parsed_data["line_items"]:
                delivery_date = None
                if item.get("delivery_date"):
                    try:
                        delivery_date = datetime.strptime(item["delivery_date"], "%Y-%m-%d").date()
                    except:
                        delivery_date = None
                
                # Handle sizes object - create separate line items for each size
                if "sizes" in item and isinstance(item["sizes"], dict):
                    for size, quantity in item["sizes"].items():
                        if quantity > 0:  # Only create line items for sizes with quantity > 0
                            # Calculate amount for this size
                            unit_price = item.get("price", 0)
                            amount = unit_price * quantity
                            
                            await conn.execute(
                                line_item_query,
                                str(uuid.uuid4()),
                                actual_order_id,
                                item.get("model_id", ""),
                                item.get("item_code", ""),
                                item.get("description", ""),
                                item.get("color", ""),
                                size,  # Individual size like "M"
                                quantity,  # Individual quantity like 12
                                unit_price,  # Unit price like 68.0
                                amount,  # Calculated amount like 816.0
                                delivery_date
                            )
                else:
                    # Fallback for items without sizes object (shouldn't happen with current schema)
                    await conn.execute(
                        line_item_query,
                        str(uuid.uuid4()),
                        actual_order_id,
                        item.get("model_id", ""),
                        item.get("item_code", ""),
                        item.get("description", ""),
                        item.get("color", ""),
                        item.get("size", ""),
                        item.get("quantity", 0),
                        item.get("unit_price", 0),
                        item.get("amount", 0),
                        delivery_date
                    )
            
            return {
                "order_id": str(actual_order_id),
                "is_duplicate": is_duplicate,
                "purchase_order_id": parsed_data["purchase_order_id"]
            }
            
    finally:
        await conn.close()

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and parse a PDF purchase order"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        try:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            try:
                print(f"DEBUG: Parsing PDF with Gemini...")
                parsed_data = extract_pdf_data(temp_file.name)
                print(f"DEBUG: PDF parsed successfully")
            except Exception as e:
                print(f"ERROR: Failed to parse PDF: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to parse PDF: {str(e)}")
            
            try:
                print(f"DEBUG: Saving to database...")
                result = await save_to_database(parsed_data)
                print(f"DEBUG: Saved to database successfully")
            except Exception as e:
                print(f"ERROR: Failed to save to database: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")
            
            message = "PDF uploaded and processed successfully"
            if result["is_duplicate"]:
                message = f"Duplicate order '{result['purchase_order_id']}' updated successfully"
            
            return {
                "success": True,
                "message": message,
                "order_id": result["order_id"],
                "is_duplicate": result["is_duplicate"],
                "parsed_data": parsed_data
            }
            
        finally:
            try:
                os.unlink(temp_file.name)
            except:
                pass

@app.get("/orders")
async def get_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    model_id: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    size: Optional[str] = Query(None),
    sort_by: str = Query("order_date", pattern="^(order_date|total_amount|item_count)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$")
):
    """Get orders with filtering and pagination"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Build WHERE clause
        where_conditions = []
        params = []
        param_count = 0
        
        if search:
            param_count += 1
            where_conditions.append(f"(o.purchase_order_id ILIKE ${param_count} OR o.buyer_name ILIKE ${param_count} OR o.supplier_name ILIKE ${param_count})")
            params.append(f"%{search}%")
        
        if model_id:
            param_count += 1
            where_conditions.append(f"EXISTS (SELECT 1 FROM line_items li WHERE li.order_id = o.id AND li.model_id ILIKE ${param_count})")
            params.append(f"%{model_id}%")
            
        if color:
            param_count += 1
            where_conditions.append(f"EXISTS (SELECT 1 FROM line_items li WHERE li.order_id = o.id AND LOWER(li.color) LIKE LOWER(${param_count}))")
            params.append(f"%{color}%")
            
        if size:
            param_count += 1
            where_conditions.append(f"EXISTS (SELECT 1 FROM line_items li WHERE li.order_id = o.id AND li.size = ${param_count})")
            params.append(size)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM orders o {where_clause}"
        total = await conn.fetchval(count_query, *params)
        
        # Use subquery approach for cleaner sorting
        if sort_by == 'item_count':
            # For item_count sorting, we need the COUNT in a subquery
            orders_query = f"""
            SELECT o.*, COALESCE(item_counts.item_count, 0) as item_count
            FROM orders o
            LEFT JOIN (
                SELECT li.order_id, COUNT(li.id) as item_count
                FROM line_items li
                GROUP BY li.order_id
            ) item_counts ON o.id = item_counts.order_id
            {where_clause.replace('li.', 'item_counts.') if where_clause and 'li.' in where_clause else where_clause}
            ORDER BY item_count {sort_order.upper()}, o.created_at DESC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
            """
        else:
            # For simple column sorting
            sort_column_map = {
                'order_date': 'o.order_date',
                'total_amount': 'o.total_amount'
            }
            sort_column = sort_column_map.get(sort_by, 'o.order_date')
            
            orders_query = f"""
            SELECT o.*, COUNT(li.id) as item_count
            FROM orders o
            LEFT JOIN line_items li ON o.id = li.order_id
            {where_clause}
            GROUP BY o.id
            ORDER BY {sort_column} {sort_order.upper()}, o.created_at DESC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
            """

        # Get orders with pagination
        offset = (page - 1) * limit
        params.extend([limit, offset])
        
        print(f"DEBUG: Sort by: {sort_by}, Order: {sort_order}")
        print(f"DEBUG: Query: {orders_query}")
        
        orders = await conn.fetch(orders_query, *params)
        
        # Get matching line items for each order
        orders_with_items = []
        for order in orders:
            # Build line items filter conditions
            item_conditions = []
            item_params = [order["id"]]  # order_id is always first param
            item_param_count = 1
            
            if model_id:
                item_param_count += 1
                item_conditions.append(f"li.model_id ILIKE ${item_param_count}")
                item_params.append(f"%{model_id}%")
                
            if color:
                item_param_count += 1
                item_conditions.append(f"LOWER(li.color) LIKE LOWER(${item_param_count})")
                item_params.append(f"%{color}%")
                
            if size:
                item_param_count += 1
                item_conditions.append(f"li.size ILIKE ${item_param_count}")
                item_params.append(f"%{size}%")
            
            # Get matching line items
            item_where = " AND ".join(item_conditions) if item_conditions else "1=1"
            items_query = f"""
            SELECT li.*, 
                   CASE WHEN ({item_where}) THEN true ELSE false END as is_match
            FROM line_items li 
            WHERE li.order_id = $1
            ORDER BY is_match DESC, li.created_at
            """
            
            items = await conn.fetch(items_query, *item_params)
            
            # Separate matching and non-matching items
            matching_items = [dict(item) for item in items if item["is_match"]]
            item_match_count = len(matching_items)
            
            order_dict = dict(order)
            order_dict["item_match_count"] = item_match_count
            order_dict["items"] = matching_items
            
            orders_with_items.append(order_dict)
        
        return {
            "orders": orders_with_items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }
        
    finally:
        await conn.close()

@app.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    model_id: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    size: Optional[str] = Query(None)
):
    """Get order details with line items (with filtering and pagination)"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Get order
        order_query = "SELECT * FROM orders WHERE id::text = $1 OR purchase_order_id = $1"
        order = await conn.fetchrow(order_query, order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Build line items filter conditions
        where_conditions = ["li.order_id = $1"]
        params = [order["id"]]
        param_count = 1
        
        if model_id:
            param_count += 1
            where_conditions.append(f"li.model_id ILIKE ${param_count}")
            params.append(f"%{model_id}%")
            
        if color:
            param_count += 1
            where_conditions.append(f"LOWER(li.color) LIKE LOWER(${param_count})")
            params.append(f"%{color}%")
            
        if size:
            param_count += 1
            where_conditions.append(f"li.size = ${param_count}")
            params.append(size)
        
        where_clause = " AND ".join(where_conditions)
        
        # Get total count of matching line items
        count_query = f"SELECT COUNT(*) FROM line_items li WHERE {where_clause}"
        total_items = await conn.fetchval(count_query, *params)
        
        # Get paginated line items
        offset = (page - 1) * limit
        param_count += 1
        param_count += 1
        items_query = f"""
        SELECT li.* FROM line_items li 
        WHERE {where_clause}
        ORDER BY li.created_at
        LIMIT ${param_count - 1} OFFSET ${param_count}
        """
        params.extend([limit, offset])
        
        items = await conn.fetch(items_query, *params)
        
        return {
            "order": dict(order),
            "line_items": [dict(item) for item in items],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_items,
                "total_pages": (total_items + limit - 1) // limit
            }
        }
        
    finally:
        await conn.close()

@app.get("/filters")
async def get_filters():
    """Get available filter options"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Get unique model IDs
        models = await conn.fetch("SELECT DISTINCT model_id FROM line_items WHERE model_id IS NOT NULL AND model_id != '' ORDER BY model_id")
        
        # Get unique colors
        colors = await conn.fetch("SELECT DISTINCT color FROM line_items WHERE color IS NOT NULL AND color != '' ORDER BY color")
        
        # Get unique sizes
        sizes = await conn.fetch("SELECT DISTINCT size FROM line_items WHERE size IS NOT NULL AND size != '' ORDER BY size")
        
        return {
            "model_ids": [row["model_id"] for row in models],
            "colors": [row["color"] for row in colors],
            "sizes": [row["size"] for row in sizes]
        }
        
    finally:
        await conn.close()

@app.get("/stats")
async def get_stats():
    """Get dashboard statistics"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        stats = await conn.fetchrow("""
        SELECT 
            COUNT(o.id) as total_orders,
            (SELECT COUNT(id) FROM line_items) as total_items,
            SUM(o.total_amount) as total_value,
            COUNT(DISTINCT o.buyer_name) as total_buyers
        FROM orders o
        """)
        
        return dict(stats)
        
    finally:
        await conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
