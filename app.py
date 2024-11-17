from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'cafe_user',
    'password': 'your_password',
    'database': 'cafe_pos',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_general_ci'  # Changed from utf8mb4_0900_ai_ci
}

# Database connection function
def get_db():
    return mysql.connector.connect(**db_config)

# Initialize database and create tables if they don't exist
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            table_id INT,
            menu VARCHAR(255) NOT NULL,
            quantity INT NOT NULL,
            status VARCHAR(50) NOT NULL,
            created_at DATETIME NOT NULL,
            FOREIGN KEY (table_id) REFERENCES tables(id)
        )
    ''')
    
    # Add tables for table management
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tables (
            id INT AUTO_INCREMENT PRIMARY KEY,
            table_number VARCHAR(10) NOT NULL UNIQUE,
            capacity INT NOT NULL,
            status ENUM('available', 'occupied', 'reserved') DEFAULT 'available',
            current_order_id INT,
            last_updated DATETIME
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            table_id INT,
            customer_name VARCHAR(100),
            customer_phone VARCHAR(20),
            party_size INT,
            reservation_time DATETIME,
            status ENUM('pending', 'confirmed', 'completed', 'cancelled') DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (table_id) REFERENCES tables(id)
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

# Initialize database on startup
init_db()

# 기본 경로 라우트: POS 및 티켓 페이지로 이동하는 버튼 제공
@app.route('/')
def index():
    return render_template('index.html')

# POS 페이지 라우트
@app.route('/pos')
def pos():
    return render_template('pos.html')

# 티켓 페이지 라우트
@app.route('/tickets')
def tickets():
    return render_template('ticket.html')

# 새로운 주문 처리
@socketio.on('new_order')
def handle_new_order(order):
    conn = get_db()
    cursor = conn.cursor()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # Check if this is a new order or an update
        if 'id' not in order:
            # This is a new order - insert all items
            for item in order['items']:
                cursor.execute('''
                    INSERT INTO orders (menu, quantity, status, created_at)
                    VALUES (%s, %s, %s, %s)
                ''', (item['menu'], 1, order['status'], current_time))
        else:
            # This is an update to an existing order
            cursor.execute('''
                UPDATE orders 
                SET status = %s 
                WHERE id = %s
            ''', (order['status'], order['id']))
        
        conn.commit()
        socketio.emit('order_update', order)
    except Exception as e:
        print(f"Error handling order: {e}")
    finally:
        cursor.close()
        conn.close()

# New route to get all active orders
@app.route('/api/orders')
def get_orders():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT * FROM orders 
        WHERE status IN ('대기 중', '진행 중')
        ORDER BY created_at DESC
    ''')
    
    orders = cursor.fetchall()
    
    # Convert datetime objects to strings
    for order in orders:
        if 'created_at' in order:
            order['created_at'] = order['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.close()
    conn.close()
    
    return {'orders': orders}

# Test connection
try:
    conn = mysql.connector.connect(
        host='localhost',
        user='cafe_user',
        password='your_password',
        database='cafe_pos'
    )
    print("Successfully connected to database!")
    conn.close()
except Exception as e:
    print(f"Error connecting to database: {e}")

@app.route('/api/analytics')
def get_analytics():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Daily sales
    cursor.execute('''
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as order_count,
            SUM(total_amount) as daily_revenue
        FROM orders
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 30
    ''')
    
    return {'sales_data': cursor.fetchall()}

@app.route('/tables')
def table_management():
    return render_template('tables.html')

@app.route('/api/tables', methods=['GET'])
def get_tables():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT t.*, 
               COALESCE(o.id, 0) as has_active_order,
               r.reservation_time,
               r.customer_name
        FROM tables t
        LEFT JOIN orders o ON t.current_order_id = o.id
        LEFT JOIN reservations r ON t.id = r.table_id 
            AND r.status = 'confirmed' 
            AND r.reservation_time > NOW()
        ORDER BY table_number
    ''')
    
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify({'tables': tables})

@app.route('/api/tables/<int:table_id>/status', methods=['PUT'])
def update_table_status(table_id):
    status = request.json.get('status')
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE tables 
        SET status = %s, last_updated = NOW() 
        WHERE id = %s
    ''', (status, table_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/reservations', methods=['POST'])
def create_reservation():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO reservations 
        (table_id, customer_name, customer_phone, party_size, reservation_time, status)
        VALUES (%s, %s, %s, %s, %s, 'confirmed')
    ''', (
        data['table_id'],
        data['customer_name'],
        data['customer_phone'],
        data['party_size'],
        data['reservation_time']
    ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/tables/<int:table_id>', methods=['GET'])
def get_table(table_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT t.*, 
               COALESCE(o.id, 0) as has_active_order,
               r.reservation_time,
               r.customer_name
        FROM tables t
        LEFT JOIN orders o ON t.current_order_id = o.id
        LEFT JOIN reservations r ON t.id = r.table_id 
            AND r.status = 'confirmed' 
            AND r.reservation_time > NOW()
        WHERE t.id = %s
    ''', (table_id,))
    
    table = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not table:
        return jsonify({'error': 'Table not found'}), 404
        
    return jsonify({'table': table})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)