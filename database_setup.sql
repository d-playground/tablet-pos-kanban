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
    status ENUM('pending', 'inprogress', 'completed', 'cancelled') DEFAULT 'pending',
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
CREATE INDEX idx_orderitem_updated ON order_items(updated_at);

-- Create views for analytics
CREATE OR REPLACE VIEW daily_sales AS
SELECT 
    DATE(created_at) as sale_date,
    COUNT(*) as total_orders,
    SUM(subtotal) as total_sales,
    AVG(subtotal) as average_order_value
FROM order_items
WHERE status = 'completed'
GROUP BY DATE(created_at);

CREATE OR REPLACE VIEW popular_items AS
SELECT 
    m.name,
    m.category,
    SUM(oi.quantity) as total_quantity,
    SUM(oi.subtotal) as total_revenue
FROM order_items oi
JOIN menus m ON oi.menu_id = m.id
WHERE oi.status = 'completed'
GROUP BY m.id
ORDER BY total_quantity DESC;

-- Insert sample data
INSERT INTO tables (name) VALUES 
('Table 1'), ('Table 2'), ('Table 3'), ('Table 4'),
('Table 5'), ('Table 6'), ('Bar 1'), ('Bar 2');

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

-- Insert test orders
INSERT INTO order_items (table_id, menu_id, quantity, unit_price, status, notes) VALUES
(1, 1, 2, 12.99, 'pending', 'Extra cold'),
(1, 2, 1, 13.99, 'pending', 'No ice'),
(2, 3, 3, 12.99, 'inprogress', 'With lime'),
(3, 4, 1, 14.99, 'completed', 'Regular');

-- Create triggers
DELIMITER //

CREATE TRIGGER after_orderitem_insert
AFTER INSERT ON order_items
FOR EACH ROW
BEGIN
    UPDATE tables t
    SET status = IF(
        EXISTS(
            SELECT 1 FROM order_items 
            WHERE table_id = NEW.table_id 
            AND status NOT IN ('completed', 'cancelled')
        ),
        'occupied', 'available'
    )
    WHERE t.id = NEW.table_id;
END//

CREATE TRIGGER after_orderitem_update
AFTER UPDATE ON order_items
FOR EACH ROW
BEGIN
    UPDATE tables t
    SET status = IF(
        EXISTS(
            SELECT 1 FROM order_items 
            WHERE table_id = NEW.table_id 
            AND status NOT IN ('completed', 'cancelled')
        ),
        'occupied', 'available'
    )
    WHERE t.id = NEW.table_id;
END//

CREATE TRIGGER after_orderitem_delete
AFTER DELETE ON order_items
FOR EACH ROW
BEGIN
    UPDATE tables t
    SET status = IF(
        EXISTS(
            SELECT 1 FROM order_items 
            WHERE table_id = OLD.table_id 
            AND status NOT IN ('completed', 'cancelled')
        ),
        'occupied', 'available'
    )
    WHERE t.id = OLD.table_id;
END//

DELIMITER ;

-- Create a dedicated user for the POS application
DROP USER IF EXISTS 'pos_user'@'localhost';
DROP USER IF EXISTS 'pos_user'@'%';
CREATE USER 'pos_user'@'%' IDENTIFIED BY '1234';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, REFERENCES, INDEX, ALTER, EXECUTE ON pos.* TO 'pos_user'@'%';
FLUSH PRIVILEGES;
  