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

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_id INT NOT NULL,
    status ENUM('대기중', '진행중', '완료', '취소') DEFAULT '대기중',
    total_amount DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (table_id) REFERENCES tables(id)
);

-- Create order_items table
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    menu_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (menu_id) REFERENCES menus(id)
);

-- Create some indexes for better performance
CREATE INDEX idx_table_status ON tables(status);
CREATE INDEX idx_menu_category ON menus(category);
CREATE INDEX idx_order_status ON orders(status);
CREATE INDEX idx_order_created ON orders(created_at);



-- Create a dedicated user for the POS application
CREATE USER 'pos_user'@'localhost' IDENTIFIED BY '1234';

-- Grant necessary permissions
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



-- Create view for daily sales
CREATE VIEW daily_sales AS
SELECT 
    DATE(o.created_at) as sale_date,
    COUNT(DISTINCT o.id) as total_orders,
    SUM(o.total_amount) as total_sales,
    AVG(o.total_amount) as average_order_value
FROM orders o
WHERE o.status = 'completed'
GROUP BY DATE(o.created_at);

-- Create view for popular items
CREATE VIEW popular_items AS
SELECT 
    m.name,
    m.category,
    SUM(oi.quantity) as total_quantity,
    SUM(oi.subtotal) as total_revenue
FROM order_items oi
JOIN menus m ON oi.menu_id = m.id
JOIN orders o ON oi.order_id = o.id
WHERE o.status = 'completed'
GROUP BY m.id
ORDER BY total_quantity DESC; 