from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import mysql.connector
from datetime import datetime

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'user1',
    'password': '1234',
    'database': 'pos',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_general_ci'
}

def get_db():
    return mysql.connector.connect(**db_config)

def init_db():
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS menus (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    category INT,
                    FOREIGN KEY (category) REFERENCES categories(id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tables (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    number INT NOT NULL,
                    name VARCHAR(255) NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_id INT,
                    menu VARCHAR(255) NOT NULL,
                    quantity INT NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    category ENUM('drink', 'food') NOT NULL,
                    created_at DATETIME NOT NULL
                )
            ''')
            conn.commit()

init_db()

# Routes for rendering templates
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pos')
def pos():
    return render_template('pos.html')

@app.route('/bar1')
def bar1():
    return render_template('bar1.html')

@app.route('/bar2')
def bar2():
    return render_template('bar2.html')

@app.route('/kitchen')
def kitchen():
    return render_template('kitchen.html')

@app.route('/table-map')
def table_map():
    return render_template('table_map.html')

@app.route('/menu')
def menu():
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT * FROM menus')
            menus = cursor.fetchall()
    return render_template('menu.html', menus=menus)

# API routes
@app.route('/api/menu', methods=['POST'])
def add_menu_item():
    data = request.json
    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('''
                    INSERT INTO menus (name, price, category)
                    VALUES (%s, %s, %s)
                ''', (data['name'], data['price'], data['category']))
                conn.commit()
                return jsonify({'success': True})
            except Exception as e:
                print(f"Error adding menu item: {e}")
                return jsonify({'success': False, 'error': str(e)})

@app.route('/api/menu/<int:menu_id>', methods=['PUT'])
def edit_menu_item(menu_id):
    data = request.json
    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('''
                    UPDATE menus
                    SET name = %s, price = %s, category = %s
                    WHERE id = %s
                ''', (data['name'], data['price'], data['category'], menu_id))
                conn.commit()
                return jsonify({'success': True})
            except Exception as e:
                print(f"Error editing menu item: {e}")
                return jsonify({'success': False, 'error': str(e)})

@app.route('/api/menu/<int:menu_id>', methods=['DELETE'])
def delete_menu_item(menu_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('DELETE FROM menus WHERE id = %s', (menu_id,))
                conn.commit()
                return jsonify({'success': True})
            except Exception as e:
                print(f"Error deleting menu item: {e}")
                return jsonify({'success': False, 'error': str(e)})

@socketio.on('new_order')
def handle_new_order(order):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                for item in order['items']:
                    cursor.execute('''
                        INSERT INTO orders (table_id, menu, quantity, status, category, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (order['table'], item['menu'], 1, order['status'], item['category'], current_time))
                conn.commit()
                if any(item['category'] == '음료' for item in order['items']):
                    socketio.emit('order_update', order)
            except Exception as e:
                print(f"Error handling order: {e}")

@socketio.on('test_event')
def handle_test_event(data):
    print('Test event received:', data)
    emit('test_response', {'message': 'Hello, client!'})

@app.route('/api/orders/<category>')
def get_orders_by_category(category):
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('''
                SELECT * FROM orders 
                WHERE category = %s AND status IN ('대기 중', '진행 중')
                ORDER BY created_at DESC
            ''', (category,))
            orders = cursor.fetchall()
            for order in orders:
                if 'created_at' in order:
                    order['created_at'] = order['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    return {'orders': orders}

@app.route('/api/analytics')
def get_analytics():
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
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

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/api/menus', methods=['GET'])
def get_menus():
    category = request.args.get('category')
    query = 'SELECT * FROM menus'
    params = ()
    if category:
        query += ' WHERE category = %s'
        params = (category,)
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            menus = cursor.fetchall()
    return jsonify(menus)

@app.route('/api/categories', methods=['GET'])
def get_categories():
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT DISTINCT category FROM menus')
            categories = [{'id': idx, 'name': category['category']} for idx, category in enumerate(cursor.fetchall())]
    return jsonify(categories)

@app.route('/api/tables', methods=['GET'])
def get_tables():
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT number, name FROM tables')
            tables = cursor.fetchall()
    return jsonify(tables)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)