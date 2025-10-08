-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    purchase_order_id VARCHAR(100) UNIQUE NOT NULL,
    order_date DATE,
    buyer_name VARCHAR(255),
    buyer_address TEXT,
    supplier_name VARCHAR(255),
    supplier_address TEXT,
    currency VARCHAR(10) DEFAULT 'USD',
    tax_amount NUMERIC(10,2),
    total_amount NUMERIC(10,2),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS line_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL,
    model_id VARCHAR(100),
    item_code VARCHAR(100),
    description TEXT,
    color VARCHAR(50),
    size VARCHAR(20),
    quantity INTEGER,
    unit_price NUMERIC(10,2),
    amount NUMERIC(10,2),
    delivery_date DATE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT line_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_orders_purchase_order_id ON orders(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_buyer_name ON orders(buyer_name);
CREATE INDEX IF NOT EXISTS idx_orders_supplier_name ON orders(supplier_name);

CREATE INDEX IF NOT EXISTS idx_line_items_order_id ON line_items(order_id);
CREATE INDEX IF NOT EXISTS idx_line_items_model_id ON line_items(model_id);
CREATE INDEX IF NOT EXISTS idx_line_items_color ON line_items(color);
CREATE INDEX IF NOT EXISTS idx_line_items_size ON line_items(size);

CREATE TRIGGER update_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
