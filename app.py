import mysql.connector
from datetime import datetime
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
from typing import List

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
            # Create categories table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE
                )
            ''')
            # Create menus table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS menus (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    category INT,
                    FOREIGN KEY (category) REFERENCES categories(id)
                )
            ''')
            # Create tables table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tables (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    number INT NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL
                )
            ''')
            # Create orders table with corrected schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_id INT,
                    menu VARCHAR(255) NOT NULL,
                    quantity INT NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    category INT,
                    created_at DATETIME NOT NULL,
                    total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                    FOREIGN KEY (table_id) REFERENCES tables(id),
                    FOREIGN KEY (category) REFERENCES categories(id)
                )
            ''')
            conn.commit()

init_db()

app = FastAPI()
templates = Jinja2Templates(directory='templates')
app.mount("/static", StaticFiles(directory="static"), name="static")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"Client disconnected: {websocket.client}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# Routes for rendering templates
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {"request": request})

@app.get("/pos", response_class=HTMLResponse)
async def pos(request: Request):
    return templates.TemplateResponse('pos.html', {"request": request})

@app.get("/bar1", response_class=HTMLResponse)
async def bar1(request: Request):
    return templates.TemplateResponse('bar1.html', {"request": request})

@app.get("/bar2", response_class=HTMLResponse)
async def bar2(request: Request):
    return templates.TemplateResponse('bar2.html', {"request": request})

@app.get("/kitchen", response_class=HTMLResponse)
async def kitchen(request: Request):
    return templates.TemplateResponse('kitchen.html', {"request": request})

@app.get("/table-map", response_class=HTMLResponse)
async def table_map(request: Request):
    return templates.TemplateResponse('table_map.html', {"request": request})

@app.get("/menu", response_class=HTMLResponse)
async def menu(request: Request):
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT * FROM menus')
            menus = cursor.fetchall()
    return templates.TemplateResponse('menu.html', {"request": request, "menus": menus})

# API routes
@app.post('/api/menu')
async def add_menu_item(request: Request):
    data = await request.json()
    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                # Ensure the category exists
                cursor.execute('SELECT id FROM categories WHERE id = %s', (data['category'],))
                category = cursor.fetchone()
                if not category:
                    return JSONResponse({'success': False, 'error': 'Invalid category ID.'}, status_code=400)

                cursor.execute('''
                    INSERT INTO menus (name, price, category)
                    VALUES (%s, %s, %s)
                ''', (data['name'], data['price'], data['category']))
                conn.commit()
                return JSONResponse({'success': True})
            except Exception as e:
                print(f"Error adding menu item: {e}")
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.put('/api/menu/{menu_id}')
async def edit_menu_item(menu_id: int, request: Request):
    data = await request.json()
    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                # Ensure the category exists
                cursor.execute('SELECT id FROM categories WHERE id = %s', (data['category'],))
                category = cursor.fetchone()
                if not category:
                    return JSONResponse({'success': False, 'error': 'Invalid category ID.'}, status_code=400)

                cursor.execute('''
                    UPDATE menus
                    SET name = %s, price = %s, category = %s
                    WHERE id = %s
                ''', (data['name'], data['price'], data['category'], menu_id))
                if cursor.rowcount == 0:
                    return JSONResponse({'success': False, 'error': 'Menu item not found.'}, status_code=404)
                conn.commit()
                return JSONResponse({'success': True})
            except Exception as e:
                print(f"Error editing menu item: {e}")
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.delete('/api/menu/{menu_id}')
async def delete_menu_item(menu_id: int):
    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('DELETE FROM menus WHERE id = %s', (menu_id,))
                if cursor.rowcount == 0:
                    return JSONResponse({'success': False, 'error': 'Menu item not found.'}, status_code=404)
                conn.commit()
                return JSONResponse({'success': True})
            except Exception as e:
                print(f"Error deleting menu item: {e}")
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get('action')
            if action == 'change_status':
                await handle_change_status(data, websocket)
            elif action == 'test_event':
                await handle_test_event(data, websocket)
            # You can handle more actions here
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def handle_change_status(data: dict, websocket: WebSocket):
    order_id = data.get('orderId')
    new_status = data.get('status')
    if not order_id or not new_status:
        await manager.send_personal_message({'success': False, 'error': 'Invalid data.'}, websocket)
        return

    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('''
                    UPDATE orders
                    SET status = %s
                    WHERE id = %s
                ''', (new_status, order_id))
                if cursor.rowcount == 0:
                    await manager.send_personal_message({'success': False, 'error': 'Order not found.'}, websocket)
                    return
                conn.commit()
                # Broadcast status update to all clients
                await manager.broadcast({
                    'action': 'status_update',
                    'orderId': order_id,
                    'status': new_status
                })
            except Exception as e:
                print(f"Error updating order status: {e}")
                await manager.send_personal_message({'success': False, 'error': str(e)}, websocket)

async def handle_test_event(data: dict, websocket: WebSocket):
    print('Test event received:', data)
    await manager.send_personal_message({'action': 'test_response', 'message': 'Hello, client!'}, websocket)

@app.get('/api/orders/{category}')
async def get_orders_by_category(category: str):
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('''
                SELECT o.*, c.name as category_name, t.number as table_number 
                FROM orders o
                JOIN categories c ON o.category = c.id
                JOIN tables t ON o.table_id = t.id
                WHERE c.name = %s AND o.status IN ('대기 중', '진행 중')
                ORDER BY o.created_at DESC
            ''', (category,))
            orders = cursor.fetchall()
            for order in orders:
                if 'created_at' in order:
                    order['created_at'] = order['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            return {'orders': orders}

@app.get('/api/analytics')
async def get_analytics():
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

@app.get('/api/menus')
async def get_menus(category: str = None):
    query = '''
        SELECT menus.*, categories.name as category_name 
        FROM menus 
        LEFT JOIN categories ON menus.category = categories.id
    '''
    params = ()
    if category:
        query += ' WHERE categories.name = %s'
        params = (category,)
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            menus = cursor.fetchall()
    return JSONResponse(menus)

@app.get('/api/categories')
async def get_categories():
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('''
                SELECT DISTINCT categories.id, categories.name 
                FROM menus 
                JOIN categories ON menus.category = categories.id
            ''')
            categories = cursor.fetchall()
    return JSONResponse(categories)

@app.get('/api/tables')
async def get_tables():
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT id, number, name FROM tables')
            tables = cursor.fetchall()
    return JSONResponse(tables)

@app.post('/api/orders')
async def create_order(request: Request):
    data = await request.json()
    current_time = datetime.now()
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            try:
                order_items = []
                for item in data['items']:
                    # Fetch menu price and category
                    cursor.execute('SELECT price, category FROM menus WHERE name = %s', (item['menu'],))
                    menu = cursor.fetchone()
                    if not menu:
                        raise ValueError(f"Menu item '{item['menu']}' not found.")

                    price = float(menu['price'])
                    total_price = price * item['quantity']
                    category_id = menu['category']

                    # Insert order
                    cursor.execute('''
                        INSERT INTO orders (table_id, menu, quantity, status, category, created_at, total_amount)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (data['table_id'], item['menu'], item['quantity'], data['status'], category_id, current_time, total_price))
                    order_id = cursor.lastrowid

                    order_items.append({
                        'id': order_id,
                        'table_id': data['table_id'],
                        'menu': item['menu'],
                        'quantity': item['quantity'],
                        'status': data['status'],
                        'category': category_id,
                        'created_at': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'total_amount': total_price
                    })

                conn.commit()

                # Broadcast to connected clients
                await manager.broadcast({
                    'action': 'order_update',
                    'order': order_items  # List of order items
                })

                return JSONResponse({'success': True})
            except Exception as e:
                print(f"Error creating order: {e}")
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.put('/api/orders/{order_id}')
async def edit_order(order_id: int, request: Request):
    data = await request.json()
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            try:
                # If menu is being updated, fetch the new price and category
                if 'menu' in data:
                    cursor.execute('SELECT price, category FROM menus WHERE name = %s', (data['menu'],))
                    menu = cursor.fetchone()
                    if not menu:
                        return JSONResponse({'success': False, 'error': 'Menu item not found.'}, status_code=400)
                    price = float(menu['price'])
                    total_price = price * data.get('quantity', 1)
                    category_id = menu['category']
                else:
                    total_price = data.get('total_amount', 0.00)
                    category_id = data.get('category', None)

                # Update order
                cursor.execute('''
                    UPDATE orders
                    SET table_id = %s, menu = %s, quantity = %s, status = %s, category = %s, total_amount = %s
                    WHERE id = %s
                ''', (
                    data.get('table_id', None),
                    data.get('menu', None),
                    data.get('quantity', 1),
                    data.get('status', None),
                    category_id,
                    total_price,
                    order_id
                ))
                if cursor.rowcount == 0:
                    return JSONResponse({'success': False, 'error': 'Order not found.'}, status_code=404)
                conn.commit()
                return JSONResponse({'success': True})
            except Exception as e:
                print(f"Error editing order: {e}")
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.delete('/api/orders/{order_id}')
async def delete_order(order_id: int):
    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('DELETE FROM orders WHERE id = %s', (order_id,))
                if cursor.rowcount == 0:
                    return JSONResponse({'success': False, 'error': 'Order not found.'}, status_code=404)
                conn.commit()
                return JSONResponse({'success': True})
            except Exception as e:
                print(f"Error deleting order: {e}")
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5000)
