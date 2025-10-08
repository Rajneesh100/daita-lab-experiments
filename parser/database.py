# database.py
import asyncpg
import json
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime
import uuid

class DatabaseManager:
    def __init__(self, host="localhost", port=4000, user="parser", password="parser123", database="parser"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool = None

    async def create_pool(self):
        """Create database connection pool"""
        self.pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            min_size=1,
            max_size=10
        )

    async def close_pool(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()

    async def create_tables(self):
        """Create database tables if they don't exist - This is handled by database_schema.sql"""
        # This method is kept for compatibility but tables should be created using the SQL file
        print("Tables should be created using database_schema.sql file")
        pass

    async def save_purchase_order(self, order_data: Dict[Any, Any]) -> str:
        """Save purchase order and line items to database"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Generate UUID for the order
                    order_id = str(uuid.uuid4())
                    
                    # Insert purchase order
                    order_query = """
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
                    RETURNING id
                    """
                    
                    # Parse order date
                    order_date = None
                    if order_data.get("order_date"):
                        try:
                            order_date = datetime.strptime(order_data["order_date"], "%Y-%m-%d").date()
                        except:
                            order_date = None
                    
                    result = await conn.fetchrow(
                        order_query,
                        order_id,
                        order_data["purchase_order_id"],
                        order_date,
                        order_data["buyer"]["name"],
                        order_data["buyer"]["address"],
                        order_data["supplier"]["name"],
                        order_data["supplier"]["address"],
                        order_data.get("currency", "USD"),
                        order_data.get("tax_amount", 0),
                        order_data.get("total_amount", 0)
                    )
                    
                    # Use the returned order_id or the original one if it was an update
                    actual_order_id = result["id"] if result else order_id

                    # Delete existing line items for this order
                    await conn.execute(
                        "DELETE FROM line_items WHERE order_id = (SELECT id FROM orders WHERE purchase_order_id = $1)",
                        order_data["purchase_order_id"]
                    )

                    # Insert line items
                    line_item_query = """
                    INSERT INTO line_items 
                    (id, order_id, model_id, item_code, description, color, size, quantity, unit_price, amount, delivery_date)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """
                    
                    for item in order_data.get("line_items", []):
                        # Parse delivery date
                        delivery_date = None
                        if item.get("delivery_date"):
                            try:
                                delivery_date = datetime.strptime(item["delivery_date"], "%Y-%m-%d").date()
                            except:
                                delivery_date = None

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
                        
                    return str(actual_order_id)
                    
        except Exception as e:
            print(f"Error saving purchase order: {e}")
            raise e

    async def get_purchase_orders(self, limit: int = 50, offset: int = 0, 
                                 model_id: Optional[str] = None, 
                                 color: Optional[str] = None,
                                 size: Optional[str] = None,
                                 search: Optional[str] = None):
        """Get purchase orders with optional filtering"""
        base_query = """
        SELECT DISTINCT o.*, 
               COUNT(*) OVER() as total_count
        FROM orders o
        LEFT JOIN line_items li ON o.id = li.order_id
        WHERE 1=1
        """
        
        params = []
        param_count = 0
        
        if model_id:
            param_count += 1
            base_query += f" AND li.model_id ILIKE ${param_count}"
            params.append(f"%{model_id}%")
            
        if color:
            param_count += 1
            base_query += f" AND li.color ILIKE ${param_count}"
            params.append(f"%{color}%")
            
        if size:
            param_count += 1
            base_query += f" AND li.size ILIKE ${param_count}"
            params.append(f"%{size}%")
            
        if search:
            param_count += 1
            base_query += f" AND (o.purchase_order_id ILIKE ${param_count} OR o.buyer_name ILIKE ${param_count} OR o.supplier_name ILIKE ${param_count})"
            params.append(f"%{search}%")
        
        base_query += " ORDER BY o.order_date DESC, o.created_at DESC"
        
        param_count += 1
        base_query += f" LIMIT ${param_count}"
        params.append(limit)
        
        param_count += 1
        base_query += f" OFFSET ${param_count}"
        params.append(offset)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(base_query, *params)
            return rows

    async def get_purchase_order_details(self, purchase_order_id: str):
        """Get purchase order with line items"""
        order_query = "SELECT * FROM orders WHERE purchase_order_id = $1 OR id::text = $1"
        items_query = """
        SELECT li.* FROM line_items li 
        JOIN orders o ON li.order_id = o.id 
        WHERE o.purchase_order_id = $1 OR o.id::text = $1 
        ORDER BY li.created_at
        """
        
        async with self.pool.acquire() as conn:
            order = await conn.fetchrow(order_query, purchase_order_id)
            if not order:
                return None
                
            items = await conn.fetch(items_query, purchase_order_id)
            
            return {
                "order": dict(order),
                "line_items": [dict(item) for item in items]
            }

    async def get_filter_options(self):
        """Get unique values for filters"""
        model_query = "SELECT DISTINCT model_id FROM line_items WHERE model_id IS NOT NULL AND model_id != '' ORDER BY model_id"
        color_query = "SELECT DISTINCT color FROM line_items WHERE color IS NOT NULL AND color != '' ORDER BY color"
        size_query = "SELECT DISTINCT size FROM line_items WHERE size IS NOT NULL AND size != '' ORDER BY size"
        
        async with self.pool.acquire() as conn:
            models = await conn.fetch(model_query)
            colors = await conn.fetch(color_query)
            sizes = await conn.fetch(size_query)
            
            return {
                "models": [row["model_id"] for row in models],
                "colors": [row["color"] for row in colors],
                "sizes": [row["size"] for row in sizes]
            }

    async def delete_purchase_order(self, purchase_order_id: str) -> bool:
        """Delete a purchase order and its line items"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Delete order (line items will be deleted due to CASCADE)
                    result = await conn.execute(
                        "DELETE FROM orders WHERE purchase_order_id = $1 OR id::text = $1",
                        purchase_order_id
                    )
                    return result != "DELETE 0"
        except Exception as e:
            print(f"Error deleting purchase order: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager()