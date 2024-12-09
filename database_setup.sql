-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS pos CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE pos;

-- Create tables table
CREATE TABLE IF NOT EXISTS tables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    status ENUM('available', 'occupied') DEFAULT 'available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create menus table
CREATE TABLE IF NOT EXISTS menus (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create order_items table
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_id INT NOT NULL,
    menu_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    status ENUM('대기중', '진행중', '완료', '취소') DEFAULT '대기중',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE RESTRICT,
    FOREIGN KEY (menu_id) REFERENCES menus(id) ON DELETE RESTRICT
);

-- Create indexes
CREATE INDEX idx_table_status ON tables(status);
CREATE INDEX idx_menu_category ON menus(category);
CREATE INDEX idx_orderitem_status ON order_items(status);
CREATE INDEX idx_orderitem_table ON order_items(table_id);
CREATE INDEX idx_orderitem_created ON order_items(created_at);

-- Create a dedicated user for the POS application
CREATE USER IF NOT EXISTS 'pos_user'@'localhost' IDENTIFIED BY '1234';
GRANT SELECT, INSERT, UPDATE, DELETE ON pos.* TO 'pos_user'@'localhost';
FLUSH PRIVILEGES;

-- Insert sample tables
INSERT INTO tables (name) VALUES 
('Table 1'), ('Table 2'), ('Table 3'), ('Table 4'),
('Table 5'), ('Table 6'), ('Bar 1'), ('Bar 2');

-- Insert sample menu categories
INSERT INTO menus (name, price, category) VALUES 
-- Classic Cocktails
('Old Fashioned', 12.99, 'Classic Cocktails'),
('Manhattan', 13.99, 'Classic Cocktails'),
('Martini', 12.99, 'Classic Cocktails'),

-- Signature Cocktails
('Midnight Blue', 14.99, 'Signature Cocktails'),
('Spiced Mule', 13.99, 'Signature Cocktails'),
('Garden Fresh', 13.99, 'Signature Cocktails'),

-- Beer & Wine
('Draft Beer', 7.99, 'Beer & Wine'),
('House Red', 9.99, 'Beer & Wine'),
('House White', 9.99, 'Beer & Wine'),

-- Bar Snacks
('Mixed Nuts', 5.99, 'Bar Snacks'),
('Olive Medley', 6.99, 'Bar Snacks'),
('Cheese Board', 15.99, 'Bar Snacks');

-- Create views for analytics
DROP VIEW IF EXISTS daily_sales;
DROP VIEW IF EXISTS popular_items;

CREATE OR REPLACE VIEW daily_sales AS
SELECT 
    DATE(created_at) as sale_date,
    COUNT(*) as total_orders,
    SUM(subtotal) as total_sales,
    AVG(subtotal) as average_order_value
FROM order_items
WHERE status = '완료'
GROUP BY DATE(created_at);

CREATE OR REPLACE VIEW popular_items AS
SELECT 
    m.name,
    m.category,
    SUM(oi.quantity) as total_quantity,
    SUM(oi.subtotal) as total_revenue
FROM order_items oi
JOIN menus m ON oi.menu_id = m.id
WHERE oi.status = '완료'
GROUP BY m.id
ORDER BY total_quantity DESC;

-- Add trigger to update table status when order items change
DELIMITER //

CREATE OR REPLACE TRIGGER after_orderitem_insert
AFTER INSERT ON order_items
FOR EACH ROW
BEGIN
    UPDATE tables 
    SET status = 'occupied'
    WHERE id = NEW.table_id;
END//

CREATE OR REPLACE TRIGGER after_orderitem_update
AFTER UPDATE ON order_items
FOR EACH ROW
BEGIN
    DECLARE active_items INT;
    
    SELECT COUNT(*) INTO active_items
    FROM order_items
    WHERE table_id = NEW.table_id
    AND status NOT IN ('완료', '취소');
    
    IF active_items = 0 THEN
        UPDATE tables 
        SET status = 'available'
        WHERE id = NEW.table_id;
    ELSE
        UPDATE tables 
        SET status = 'occupied'
        WHERE id = NEW.table_id;
    END IF;
END//

DELIMITER ; 