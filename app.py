import mysql.connector
from datetime import datetime
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
from typing import List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, filename='app.log',
                    format='%(asctime)s:%(levelname)s:%(message)s')

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
            # Create menus table with category as ENUM
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS menus (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    category ENUM('칵테일', '커스텀칵테일', '간식거리', '위스키(잔)','위스키(병)') NOT NULL
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
            # Create orders table with category as ENUM and menu as VARCHAR
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_id INT,
                    menu VARCHAR(255) NOT NULL,
                    quantity INT NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    category ENUM('칵테일', '커스텀칵테일', '간식거리', '위스키(잔)','위스키(병)') NOT NULL,
                    created_at DATETIME NOT NULL,
                    total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                    FOREIGN KEY (table_id) REFERENCES tables(id)
                )
            ''')
            conn.commit()

# Initialize the database (optional if tables already exist)
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
        logging.info(f"Client connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info(f"Client disconnected: {websocket.client}")

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

@app.get("/order", response_class=HTMLResponse)
async def order(request: Request):
    return templates.TemplateResponse('order.html', {"request": request})

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
    # Fetch menus
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('''
                SELECT id, name, price, category
                FROM menus
            ''')
            menus = cursor.fetchall()
    
    # Fetch distinct categories from 'menus' table
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT DISTINCT category FROM menus')
            categories_records = cursor.fetchall()
            categories = [record[0] for record in categories_records]
    
    return templates.TemplateResponse('menu.html', {"request": request, "menus": menus, "categories": categories})

# API routes
@app.post('/api/menu')
async def add_menu_item(request: Request):
    data = await request.json()
    name = data.get('name')
    price = data.get('price')
    category = data.get('category')
    
    if not name or not price or not category:
        return JSONResponse({'success': False, 'error': 'All fields are required.'}, status_code=400)
    
    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('''
                    INSERT INTO menus (name, price, category)
                    VALUES (%s, %s, %s)
                ''', (name, price, category))
                conn.commit()
                return JSONResponse({'success': True})
            except Exception as e:
                logging.error(f"Error adding menu item: {e}", exc_info=True)
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.put('/api/menu/{menu_id}')
async def edit_menu_item(menu_id: int, request: Request):
    data = await request.json()
    logging.info(f"Received PUT request for menu_id {menu_id}: {data}")
    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                # Ensure the category exists by ENUM validation
                cursor.execute('''
                    UPDATE menus
                    SET name = %s, price = %s, category = %s
                    WHERE id = %s
                ''', (data['name'], data['price'], data['category'], menu_id))
                if cursor.rowcount == 0:
                    logging.warning(f"Menu item with id {menu_id} not found.")
                    return JSONResponse({'success': False, 'error': 'Menu item not found.'}, status_code=404)
                conn.commit()
                logging.info(f"Menu item with id {menu_id} updated successfully.")
                return JSONResponse({'success': True})
            except mysql.connector.IntegrityError as e:
                if 'ER_TRUNCATED_WRONG_VALUE' in str(e):
                    logging.warning(f"Invalid category name: {data['category']}")
                    return JSONResponse({'success': False, 'error': 'Invalid category name.'}, status_code=400)
                logging.error(f"Integrity error editing menu item: {e}", exc_info=True)
                return JSONResponse({'success': False, 'error': 'Database integrity error.'}, status_code=500)
            except Exception as e:
                logging.error(f"Error editing menu item: {e}", exc_info=True)
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.delete('/api/menu/{menu_id}')
async def delete_menu_item(menu_id: int):
    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('DELETE FROM menus WHERE id = %s', (menu_id,))
                if cursor.rowcount == 0:
                    logging.warning(f"Menu item with id {menu_id} not found.")
                    return JSONResponse({'success': False, 'error': 'Menu item not found.'}, status_code=404)
                conn.commit()
                logging.info(f"Menu item with id {menu_id} deleted successfully.")
                return JSONResponse({'success': True})
            except Exception as e:
                logging.error(f"Error deleting menu item: {e}", exc_info=True)
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
                logging.info(f"Order {order_id} status updated to {new_status}.")
                # Broadcast status update to all clients
                await manager.broadcast({
                    'action': 'status_update',
                    'orderId': order_id,
                    'status': new_status
                })
            except Exception as e:
                logging.error(f"Error updating order status: {e}", exc_info=True)
                await manager.send_personal_message({'success': False, 'error': str(e)}, websocket)

async def handle_test_event(data: dict, websocket: WebSocket):
    logging.info(f"Test event received: {data}")
    await manager.send_personal_message({'action': 'test_response', 'message': 'Hello, client!'}, websocket)

@app.get('/api/orders/{category}')
async def get_orders_by_category(category: str):
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            try:
                cursor.execute('''
                    SELECT o.*, t.number as table_number 
                    FROM orders o
                    JOIN tables t ON o.table_id = t.id
                    WHERE o.category = %s AND o.status IN ('대기 중', '진행 중')
                    ORDER BY o.created_at DESC
                ''', (category,))
                orders = cursor.fetchall()
                for order in orders:
                    if 'created_at' in order and isinstance(order['created_at'], datetime):
                        order['created_at'] = order['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                logging.info(f"Fetched orders for category {category}.")
                return {'orders': orders}
            except Exception as e:
                logging.error(f"Error fetching orders by category: {e}", exc_info=True)
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.get('/api/analytics')
async def get_analytics():
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            try:
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
                sales_data = cursor.fetchall()
                logging.info("Fetched sales analytics data.")
                return {'sales_data': sales_data}
            except Exception as e:
                logging.error(f"Error fetching analytics data: {e}", exc_info=True)
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.get('/api/menus')
async def get_menus(category_name: str = None):
    query = '''
        SELECT * 
        FROM menus 
    '''
    params = ()
    if category_name:
        query += ' WHERE category = %s'
        params = (category_name,)
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            try:
                cursor.execute(query, params)
                menus = cursor.fetchall()
                logging.info(f"Fetched menus with category filter: {category_name}")
                return JSONResponse(menus)
            except Exception as e:
                logging.error(f"Error fetching menus: {e}", exc_info=True)
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.get('/api/categories')
async def get_categories():
    # Since categories are now ENUM, you can define them directly
    categories = ['칵테일', '커스텀칵테일', '간식거리', '위스키(잔)','위스키(병)']
    return JSONResponse({'categories': categories})

@app.get('/api/tables')
async def get_tables():
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            try:
                cursor.execute('SELECT id, number, name FROM tables')
                tables = cursor.fetchall()
                logging.info("Fetched tables data.")
                return JSONResponse(tables)
            except Exception as e:
                logging.error(f"Error fetching tables: {e}", exc_info=True)
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.post('/api/orders')
async def create_order(request: Request):
    data = await request.json()
    current_time = datetime.now()
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            try:
                order_items = []
                for item in data['items']:
                    # Fetch menu details
                    cursor.execute('SELECT price, category FROM menus WHERE name = %s', (item['menu'],))
                    menu = cursor.fetchone()
                    if not menu:
                        raise ValueError(f"Menu item '{item['menu']}' not found.")

                    price = float(menu['price'])
                    total_price = price * item['quantity']
                    category_name = menu['category']

                    # Insert order
                    cursor.execute('''
                        INSERT INTO orders (table_id, menu, quantity, status, category, created_at, total_amount)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (data['table_id'], item['menu'], item['quantity'], data['status'], category_name, current_time, total_price))
                    order_id = cursor.lastrowid

                    order_items.append({
                        'id': order_id,
                        'table_id': data['table_id'],
                        'menu': item['menu'],
                        'quantity': item['quantity'],
                        'status': data['status'],
                        'category': category_name,
                        'created_at': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'total_amount': total_price
                    })

                conn.commit()
                logging.info(f"Created new orders: {order_items}")

                # Broadcast to connected clients
                await manager.broadcast({
                    'action': 'order_update',
                    'order': order_items  # List of order items
                })

                return JSONResponse({'success': True})
            except ValueError as ve:
                logging.warning(f"Invalid data: {ve}")
                return JSONResponse({'success': False, 'error': str(ve)}, status_code=400)
            except Exception as e:
                logging.error(f"Error creating order: {e}", exc_info=True)
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
                    category_name = menu['category']
                else:
                    total_price = data.get('total_amount', 0.00)
                    category_name = data.get('category', None)

                # Update order
                cursor.execute('''
                    UPDATE orders
                    SET table_id = COALESCE(%s, table_id),
                        menu = COALESCE(%s, menu),
                        quantity = COALESCE(%s, quantity),
                        status = COALESCE(%s, status),
                        category = COALESCE(%s, category),
                        total_amount = COALESCE(%s, total_amount)
                    WHERE id = %s
                ''', (
                    data.get('table_id'),
                    data.get('menu'),
                    data.get('quantity'),
                    data.get('status'),
                    category_name,
                    total_price,
                    order_id
                ))
                if cursor.rowcount == 0:
                    return JSONResponse({'success': False, 'error': 'Order not found.'}, status_code=404)
                conn.commit()
                logging.info(f"Order {order_id} updated successfully.")
                return JSONResponse({'success': True})
            except Exception as e:
                logging.error(f"Error editing order: {e}", exc_info=True)
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.delete('/api/orders/{order_id}')
async def delete_order(order_id: int):
    with get_db() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('DELETE FROM orders WHERE id = %s', (order_id,))
                if cursor.rowcount == 0:
                    logging.warning(f"Order with id {order_id} not found.")
                    return JSONResponse({'success': False, 'error': 'Order not found.'}, status_code=404)
                conn.commit()
                logging.info(f"Order with id {order_id} deleted successfully.")
                return JSONResponse({'success': True})
            except Exception as e:
                logging.error(f"Error deleting order: {e}", exc_info=True)
                return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

# Additional API endpoints remain unchanged

def get_enum_values(table_name: str, column_name: str) -> List[str]:
    query = """
        SELECT COLUMN_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
    """
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (db_config['database'], table_name, column_name))
            result = cursor.fetchone()
            if not result:
                return []
            column_type = result[0]
            # Extract ENUM values
            enum_values = column_type.strip("enum()").split(",")
            enum_values = [val.strip("'") for val in enum_values]
            return enum_values

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=5000)
