"""
POS Backend API
---------------

This module provides the backend API for the POS system.
It handles database operations, API routes, and WebSocket events.
"""

import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from marshmallow import Schema, fields, validate, ValidationError
import mysql.connector
from mysql.connector import pooling

# Load environment variables
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'pos_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '1234')
DB_NAME = os.environ.get('DB_NAME', 'pos')

# Database configuration
db_config = {
    'host': DB_HOST,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME,
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_general_ci'
}

# Create a database connection pool
db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="pos_pool",
    pool_size=5,
    **db_config
)

app = Flask(__name__)
socketio = SocketIO(app)

# Custom exception classes
class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

# Marshmallow schemas for input validation
class TableSchema(Schema):
    id = fields.Int(allow_none=True)
    name = fields.Str(required=True)
    status = fields.Str(required=True, validate=validate.OneOf(['available', 'occupied']))

class MenuSchema(Schema):
    id = fields.Int(allow_none=True)
    name = fields.Str(required=True)
    price = fields.Decimal(required=True, validate=validate.Range(min=0))
    category = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    is_available = fields.Bool(required=True)

class OrderItemSchema(Schema):
    menu_id = fields.Int(required=True)
    quantity = fields.Int(required=True, validate=validate.Range(min=1))
    notes = fields.Str(allow_none=True)

class OrderSchema(Schema):
    table_id = fields.Int(required=True)
    items = fields.List(fields.Nested(OrderItemSchema), required=True)

table_schema = TableSchema()
menu_schema = MenuSchema()
order_schema = OrderSchema()

# Utility functions
def get_db_connection():
    """Get a database connection from the pool."""
    return db_pool.get_connection()

def close_db_connection(conn):
    """Close the database connection."""
    conn.close()

def commit_and_close(conn):
    """Commit changes and close the database connection."""
    conn.commit()
    close_db_connection(conn)

# Route handlers
@app.route('/')
def index():
    """Render the index page."""
    return render_template('index.html')

@app.route('/pos')
def pos():
    """Render the POS page with tables and menus data."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, name, status FROM tables")
        tables = cursor.fetchall()
        
        cursor.execute("SELECT id, name, price, category, description, is_available FROM menus")
        menus = cursor.fetchall()
        
        cursor.execute("SELECT DISTINCT category FROM menus")
        categories = [row['category'] for row in cursor.fetchall() if row['category'] is not None]
        
        cursor.close()
        close_db_connection(conn)
        
        return render_template('pos.html', tables=tables, menus=menus, categories=categories)
    except Exception as e:
        app.logger.error(f"Error fetching POS data: {str(e)}")
        raise InvalidUsage('Failed to fetch POS data', status_code=500)

@app.route('/tickets')
def tickets():
    """Render the order tickets page."""
    return render_template('ticket.html')

@app.route('/setup/menus')
def setup_menus():
    """Render the menu setup page."""
    return render_template('setup_menu.html')

@app.route('/setup/tables')
def setup_tables():
    """Render the table setup page."""
    return render_template('setup_table.html')

@app.route('/api/tables')
def get_tables():
    """Get all tables."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, status FROM tables")
        tables = cursor.fetchall()
        cursor.close()
        close_db_connection(conn)
        return jsonify(tables)
    except Exception as e:
        app.logger.error(f"Error fetching tables: {str(e)}")
        raise InvalidUsage('Failed to fetch tables', status_code=500)

@app.route('/api/tables', methods=['PUT'])
def update_tables():
    """Update tables data."""
    try:
        data = request.get_json()
        if not isinstance(data, list):
            raise InvalidUsage('Invalid input: expected array of tables')
        
        # Validate input
        tables = table_schema.load(data, many=True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for table in tables:
            table_id = table.get('id')
            table_name = table.get('name')
            table_status = table.get('status')
            
            if table_id:
                # Update existing table
                cursor.execute("""
                    UPDATE tables 
                    SET name = %s, status = %s 
                    WHERE id = %s
                """, (table_name, table_status, table_id))
            else:
                # Insert new table
                cursor.execute("""
                    INSERT INTO tables (name, status) 
                    VALUES (%s, %s)
                """, (table_name, table_status))
        
        commit_and_close(conn)
        
        return jsonify({'success': True})
    except ValidationError as ve:
        app.logger.error(f"Validation error: {str(ve)}")
        raise InvalidUsage({'validation_errors': ve.messages}, status_code=400)
    except Exception as e:
        app.logger.error(f"Error updating tables: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            close_db_connection(conn)
        raise InvalidUsage('Failed to update tables', status_code=500)

@app.route('/api/menus')
def get_menus():
    """Get all menus."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, price, category, description, is_available FROM menus")
        menus = cursor.fetchall()
        cursor.close()
        close_db_connection(conn)
        return jsonify(menus)
    except Exception as e:
        app.logger.error(f"Error fetching menus: {str(e)}")
        raise InvalidUsage('Failed to fetch menus', status_code=500)

@app.route('/api/menus', methods=['PUT'])
def update_menus():
    """Update menus data."""
    try:
        data = request.get_json()
        if not isinstance(data, list):
            raise InvalidUsage('Invalid input: expected array of menu items')
        
        # Validate input
        menus = menu_schema.load(data, many=True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for menu in menus:
            menu_id = menu.get('id')
            menu_name = menu.get('name')
            menu_price = menu.get('price')
            menu_category = menu.get('category')
            menu_description = menu.get('description')
            menu_is_available = menu.get('is_available')
            
            if menu_id:
                # Update existing menu
                cursor.execute("""
                    UPDATE menus 
                    SET name = %s, price = %s, category = %s, description = %s, is_available = %s
                    WHERE id = %s
                """, (menu_name, menu_price, menu_category, menu_description, menu_is_available, menu_id))
            else:
                # Insert new menu
                cursor.execute("""
                    INSERT INTO menus (name, price, category, description, is_available)
                    VALUES (%s, %s, %s, %s, %s)
                """, (menu_name, menu_price, menu_category, menu_description, menu_is_available))
        
        commit_and_close(conn)
        
        return jsonify({'success': True})
    except ValidationError as ve:
        app.logger.error(f"Validation error: {str(ve)}")
        raise InvalidUsage({'validation_errors': ve.messages}, status_code=400)
    except Exception as e:
        app.logger.error(f"Error updating menus: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            close_db_connection(conn)
        raise InvalidUsage('Failed to update menus', status_code=500)

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create a new order."""
    try:
        data = request.get_json()
        
        # Validate input
        order_data = order_schema.load(data)
        
        table_id = order_data['table_id']
        items = order_data['items']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Insert order with initial total of 0
        cursor.execute(
            "INSERT INTO orders (table_id, status, total_amount) VALUES (%s, '대기중', 0)", 
            (table_id,)
        )
        order_id = cursor.lastrowid

        # Insert order items and calculate total
        total_amount = 0
        for item in items:
            # Get menu item price
            cursor.execute(
                "SELECT price FROM menus WHERE id = %s",
                (item['menu_id'],)
            )
            menu_item = cursor.fetchone()
            if not menu_item:
                raise InvalidUsage(f"Menu item {item['menu_id']} not found")

            unit_price = menu_item['price']
            quantity = item['quantity']
            subtotal = unit_price * quantity
            total_amount += subtotal

            # Insert order item
            cursor.execute("""
                INSERT INTO order_items (order_id, menu_id, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, item['menu_id'], quantity, unit_price))

        # Update order total
        cursor.execute(
            "UPDATE orders SET total_amount = %s WHERE id = %s",
            (total_amount, order_id)
        )

        conn.commit()
        close_db_connection(conn)

        # Emit socket event to update tickets
        socketio.emit('new_order', {'order_id': order_id})

        return jsonify({'order_id': order_id, 'success': True}), 201

    except ValidationError as ve:
        app.logger.error(f"Validation error: {str(ve)}")
        raise InvalidUsage(ve.messages, status_code=400)
    except Exception as e:
        app.logger.error(f"Error creating order: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            close_db_connection(conn)
        raise InvalidUsage('Failed to create order', status_code=500)

@app.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order_status(order_id):
    """Update the status of an order."""
    try:
        data = request.get_json()
        status = data['status']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
        commit_and_close(conn)

        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error updating order status: {str(e)}")
        raise InvalidUsage('Failed to update order status', status_code=500)

@app.route('/api/sales')
def get_sales_data():
    """Get sales data."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM daily_sales")
        daily_sales = cursor.fetchall()
        cursor.execute("SELECT * FROM popular_items")
        popular_items = cursor.fetchall()
        cursor.close()
        close_db_connection(conn)
        return jsonify({
            'daily_sales': daily_sales,
            'popular_items': popular_items
        })
    except Exception as e:
        app.logger.error(f"Error fetching sales data: {str(e)}")
        raise InvalidUsage('Failed to fetch sales data', status_code=500)

@app.route('/api/orders')
def get_orders():
    """Get all active orders."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get orders with their items
        cursor.execute("""
            SELECT o.id, o.table_id, o.status, o.total_amount, o.created_at,
                   oi.menu_id, oi.quantity, m.name as item_name
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN menus m ON oi.menu_id = m.id
            WHERE o.status != '취소'
            ORDER BY o.created_at DESC
        """)
        
        rows = cursor.fetchall()
        close_db_connection(conn)
        
        # Group items by order
        orders = {}
        for row in rows:
            order_id = row['id']
            if order_id not in orders:
                orders[order_id] = {
                    'id': order_id,
                    'table_id': row['table_id'],
                    'status': row['status'],
                    'total_amount': float(row['total_amount']),
                    'created_at': row['created_at'].isoformat(),
                    'items': []
                }
            
            if row['menu_id']:  # Check if there are items
                orders[order_id]['items'].append({
                    'menu_id': row['menu_id'],
                    'name': row['item_name'],
                    'quantity': row['quantity']
                })
        
        return jsonify(list(orders.values()))
        
    except Exception as e:
        app.logger.error(f"Error fetching orders: {str(e)}")
        raise InvalidUsage('Failed to fetch orders', status_code=500)

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection event."""
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection event."""
    print('Client disconnected')

@socketio.on('update_order_status')
def handle_update_order_status(data):
    """Handle update order status event."""
    try:
        order_id = data['order_id']
        status = data['status']
        # Update in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
        commit_and_close(conn)
        # Broadcast update to all clients
        emit('order_status_updated', {'order_id': order_id, 'status': status}, broadcast=True)
    except Exception as e:
        app.logger.error(f"Error updating order status via WebSocket: {str(e)}")

# Error handlers
@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    """Handle InvalidUsage exceptions."""
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
