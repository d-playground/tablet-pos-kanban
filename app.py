"""
POS Backend API
---------------

This module provides the backend API for the POS system.
It handles database operations and WebSocket events.
"""

import os
from datetime import datetime
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

# Custom exception class
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
class OrderItemSchema(Schema):
    menu_id = fields.Int(required=True)
    table_id = fields.Int(required=True)
    quantity = fields.Int(required=True, validate=validate.Range(min=1))
    notes = fields.Str(allow_none=True)

order_item_schema = OrderItemSchema()

# Utility functions
def get_db_connection():
    """Get a database connection from the pool."""
    try:
        return db_pool.get_connection()
    except Exception as e:
        app.logger.error(f"Database connection error: {str(e)}")
        raise InvalidUsage('Database connection failed', status_code=500)

def close_db_connection(conn):
    """Close the database connection."""
    conn.close()

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
        
        # Get tables with their current status
        cursor.execute("""
            SELECT t.*, 
                   COUNT(CASE WHEN oi.status NOT IN ('완료', '취소') THEN 1 END) as active_items
            FROM tables t
            LEFT JOIN order_items oi ON t.id = oi.table_id
            GROUP BY t.id
        """)
        tables = cursor.fetchall()
        
        # Get menus
        cursor.execute("SELECT id, name, price, category, description, is_available FROM menus")
        menus = cursor.fetchall()
        
        # Get menu categories
        cursor.execute("SELECT DISTINCT category FROM menus")
        categories = [row['category'] for row in cursor.fetchall()]
        
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

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get all active order items grouped by table."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                oi.id,
                oi.table_id,
                oi.menu_id,
                oi.quantity,
                oi.unit_price,
                oi.subtotal,
                oi.status,
                oi.notes,
                oi.created_at,
                m.name as menu_name,
                m.category as menu_category,
                t.name as table_name
            FROM order_items oi
            JOIN menus m ON oi.menu_id = m.id
            JOIN tables t ON oi.table_id = t.id
            WHERE oi.status NOT IN ('완료', '취소')
            ORDER BY oi.created_at DESC
        """)
        
        items = cursor.fetchall()
        close_db_connection(conn)
        
        # Group items by table
        tables = {}
        for item in items:
            table_id = item['table_id']
            if table_id not in tables:
                tables[table_id] = {
                    'table_id': table_id,
                    'table_name': item['table_name'],
                    'items': []
                }
            tables[table_id]['items'].append({
                'id': item['id'],
                'menu_id': item['menu_id'],
                'menu_name': item['menu_name'],
                'menu_category': item['menu_category'],
                'quantity': item['quantity'],
                'unit_price': float(item['unit_price']),
                'subtotal': float(item['subtotal']),
                'status': item['status'],
                'notes': item['notes'],
                'created_at': item['created_at'].isoformat()
            })
        
        return jsonify(list(tables.values()))
        
    except Exception as e:
        app.logger.error(f"Error fetching orders: {str(e)}")
        raise InvalidUsage('Failed to fetch orders', status_code=500)

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create new order items."""
    try:
        data = request.get_json()
        items = data.get('items', [])
        
        if not items:
            raise InvalidUsage('No items provided')
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        created_items = []
        for item in items:
            # Validate each item
            item_data = order_item_schema.load(item)
            
            # Get menu price to ensure price integrity
            cursor.execute("SELECT price FROM menus WHERE id = %s", (item_data['menu_id'],))
            menu = cursor.fetchone()
            if not menu:
                raise InvalidUsage(f"Menu item {item_data['menu_id']} not found")
            
            cursor.execute("""
                INSERT INTO order_items 
                (table_id, menu_id, quantity, unit_price, notes)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                item_data['table_id'],
                item_data['menu_id'],
                item_data['quantity'],
                menu[0],  # Use price from menu
                item_data.get('notes')
            ))
            created_items.append(cursor.lastrowid)
        
        conn.commit()
        close_db_connection(conn)
        
        # Emit socket event
        socketio.emit('new_orders', {'item_ids': created_items})
        
        return jsonify({'success': True, 'item_ids': created_items})
        
    except ValidationError as ve:
        app.logger.error(f"Validation error: {str(ve)}")
        raise InvalidUsage(ve.messages, status_code=400)
    except Exception as e:
        app.logger.error(f"Error creating order: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            close_db_connection(conn)
        raise InvalidUsage('Failed to create order', status_code=500)

@app.route('/api/orders/<int:item_id>', methods=['PUT'])
def update_order_status(item_id):
    """Update the status of an order item."""
    try:
        data = request.get_json()
        new_status = data['status']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE order_items SET status = %s WHERE id = %s",
            (new_status, item_id)
        )
        
        conn.commit()
        close_db_connection(conn)
        
        # Emit socket event
        socketio.emit('order_status_updated', {
            'item_id': item_id,
            'status': new_status
        })
        
        return jsonify({'success': True})
        
    except Exception as e:
        app.logger.error(f"Error updating order status: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            close_db_connection(conn)
        raise InvalidUsage('Failed to update order status', status_code=500)

@app.route('/api/orders/<int:item_id>', methods=['DELETE'])
def delete_order_item(item_id):
    """Delete an order item."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE order_items SET status = '취소' WHERE id = %s", (item_id,))
        
        conn.commit()
        close_db_connection(conn)
        
        socketio.emit('order_item_deleted', {'item_id': item_id})
        
        return jsonify({'success': True})
        
    except Exception as e:
        app.logger.error(f"Error deleting order item: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            close_db_connection(conn)
        raise InvalidUsage('Failed to delete order item', status_code=500)

# Additional route handlers
@app.route('/setup/menus')
def setup_menus():
    """Render the menu setup page."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT DISTINCT category FROM menus")
        categories = [row['category'] for row in cursor.fetchall()]
        close_db_connection(conn)
        return render_template('setup_menu.html', categories=categories)
    except Exception as e:
        app.logger.error(f"Error fetching menu categories: {str(e)}")
        raise InvalidUsage('Failed to fetch menu categories', status_code=500)

@app.route('/setup/tables')
def setup_tables():
    """Render the table setup page."""
    return render_template('setup_table.html')

@app.route('/api/menus', methods=['GET'])
def get_menus():
    """Get all menus."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, price, category, description, is_available 
            FROM menus 
            ORDER BY category, name
        """)
        menus = cursor.fetchall()
        close_db_connection(conn)
        return jsonify(menus)
    except Exception as e:
        app.logger.error(f"Error fetching menus: {str(e)}")
        raise InvalidUsage('Failed to fetch menus', status_code=500)

@app.route('/api/tables', methods=['GET'])
def get_tables():
    """Get all tables with their current status."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT t.*, 
                   COUNT(CASE WHEN oi.status NOT IN ('완료', '취소') THEN 1 END) as active_items
            FROM tables t
            LEFT JOIN order_items oi ON t.id = oi.table_id
            GROUP BY t.id
            ORDER BY t.name
        """)
        tables = cursor.fetchall()
        close_db_connection(conn)
        return jsonify(tables)
    except Exception as e:
        app.logger.error(f"Error fetching tables: {str(e)}")
        raise InvalidUsage('Failed to fetch tables', status_code=500)

@app.route('/api/menus', methods=['PUT'])
def update_menus():
    """Update menu items."""
    try:
        data = request.get_json()
        if not isinstance(data, list):
            raise InvalidUsage('Invalid input: expected array of menu items')
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for menu in data:
            if menu.get('id'):
                cursor.execute("""
                    UPDATE menus 
                    SET name = %s, price = %s, category = %s, 
                        description = %s, is_available = %s
                    WHERE id = %s
                """, (
                    menu['name'], menu['price'], menu['category'],
                    menu.get('description'), menu.get('is_available', True),
                    menu['id']
                ))
            else:
                cursor.execute("""
                    INSERT INTO menus (name, price, category, description, is_available)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    menu['name'], menu['price'], menu['category'],
                    menu.get('description'), menu.get('is_available', True)
                ))
        
        conn.commit()
        close_db_connection(conn)
        return jsonify({'success': True})
        
    except Exception as e:
        app.logger.error(f"Error updating menus: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            close_db_connection(conn)
        raise InvalidUsage('Failed to update menus', status_code=500)

@app.route('/api/tables', methods=['PUT'])
def update_tables():
    """Update tables."""
    try:
        data = request.get_json()
        if not isinstance(data, list):
            raise InvalidUsage('Invalid input: expected array of tables')
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for table in data:
            if table.get('id'):
                cursor.execute("""
                    UPDATE tables 
                    SET name = %s
                    WHERE id = %s
                """, (table['name'], table['id']))
            else:
                cursor.execute("""
                    INSERT INTO tables (name)
                    VALUES (%s)
                """, (table['name'],))
        
        conn.commit()
        close_db_connection(conn)
        return jsonify({'success': True})
        
    except Exception as e:
        app.logger.error(f"Error updating tables: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            close_db_connection(conn)
        raise InvalidUsage('Failed to update tables', status_code=500)

@app.route('/api/stats/tables', methods=['GET'])
def get_tables_stats():
    """Get tables statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'occupied' THEN 1 END) as active
            FROM tables
        """)
        
        stats = cursor.fetchone()
        close_db_connection(conn)
        
        return jsonify(stats)
        
    except Exception as e:
        app.logger.error(f"Error fetching table stats: {str(e)}")
        raise InvalidUsage('Failed to fetch table stats', status_code=500)

@app.route('/api/stats/orders', methods=['GET'])
def get_orders_stats():
    """Get orders statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN status = '대기중' THEN 1 END) as pending,
                COUNT(CASE WHEN status = '진행중' THEN 1 END) as in_progress,
                COUNT(CASE WHEN status = '완료' THEN 1 END) as completed
            FROM order_items
            WHERE DATE(created_at) = CURDATE()
        """)
        
        stats = cursor.fetchone()
        close_db_connection(conn)
        
        return jsonify(stats)
        
    except Exception as e:
        app.logger.error(f"Error fetching order stats: {str(e)}")
        raise InvalidUsage('Failed to fetch order stats', status_code=500)

@app.route('/api/stats/sales/today', methods=['GET'])
def get_today_sales():
    """Get today's sales statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                COALESCE(SUM(subtotal), 0) as total,
                COUNT(DISTINCT table_id) as tables_served,
                COUNT(*) as total_orders
            FROM order_items
            WHERE DATE(created_at) = CURDATE()
            AND status = '완료'
        """)
        
        stats = cursor.fetchone()
        if stats['total'] is None:
            stats['total'] = 0
            
        close_db_connection(conn)
        
        return jsonify(stats)
        
    except Exception as e:
        app.logger.error(f"Error fetching sales stats: {str(e)}")
        raise InvalidUsage('Failed to fetch sales stats', status_code=500)

@app.route('/api/orders/<int:item_id>/status', methods=['PUT'])
def update_order_item_status(item_id):
    """Update the status of an order item."""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            raise InvalidUsage('Status is required')
            
        if new_status not in ['대기중', '진행중', '완료', '취소']:
            raise InvalidUsage('Invalid status')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE order_items SET status = %s WHERE id = %s",
            (new_status, item_id)
        )
        
        if cursor.rowcount == 0:
            raise InvalidUsage('Order item not found', status_code=404)
        
        conn.commit()
        close_db_connection(conn)
        
        # Emit socket event
        socketio.emit('order_status_updated', {
            'item_id': item_id,
            'status': new_status
        })
        
        return jsonify({'success': True})
        
    except InvalidUsage:
        raise
    except Exception as e:
        app.logger.error(f"Error updating order status: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            close_db_connection(conn)
        raise InvalidUsage('Failed to update order status', status_code=500)

@app.route('/api/orders/<int:item_id>/notes', methods=['PUT'])
def update_order_notes(item_id):
    """Update the notes of an order item."""
    try:
        data = request.get_json()
        notes = data.get('notes', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE order_items SET notes = %s WHERE id = %s",
            (notes, item_id)
        )
        
        if cursor.rowcount == 0:
            raise InvalidUsage('Order item not found', status_code=404)
        
        conn.commit()
        close_db_connection(conn)
        
        # Emit socket event
        socketio.emit('order_notes_updated', {
            'item_id': item_id,
            'notes': notes
        })
        
        return jsonify({'success': True})
        
    except Exception as e:
        app.logger.error(f"Error updating order notes: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            close_db_connection(conn)
        raise InvalidUsage('Failed to update order notes', status_code=500)

@app.route('/api/orders/completed', methods=['GET'])
def get_completed_orders():
    """Get completed orders with pagination."""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        if page < 1 or per_page < 1:
            raise InvalidUsage('Invalid pagination parameters')
        
        offset = (page - 1) * per_page
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get total count
        cursor.execute("""
            SELECT COUNT(DISTINCT oi.id) as total
            FROM order_items oi
            WHERE oi.status = '완료'
        """)
        total = cursor.fetchone()['total']
        
        # Get paginated completed orders
        cursor.execute("""
            SELECT 
                oi.id,
                oi.table_id,
                oi.menu_id,
                oi.quantity,
                oi.unit_price,
                oi.subtotal,
                oi.status,
                oi.notes,
                oi.created_at,
                m.name as menu_name,
                m.category as menu_category,
                t.name as table_name
            FROM order_items oi
            JOIN menus m ON oi.menu_id = m.id
            JOIN tables t ON oi.table_id = t.id
            WHERE oi.status = '완료'
            ORDER BY oi.created_at DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))
        
        items = cursor.fetchall()
        close_db_connection(conn)
        
        # Group items by table
        tables = {}
        for item in items:
            table_id = item['table_id']
            if table_id not in tables:
                tables[table_id] = {
                    'table_id': table_id,
                    'table_name': item['table_name'],
                    'items': []
                }
            tables[table_id]['items'].append({
                'id': item['id'],
                'menu_id': item['menu_id'],
                'menu_name': item['menu_name'],
                'menu_category': item['menu_category'],
                'quantity': item['quantity'],
                'unit_price': float(item['unit_price']),
                'subtotal': float(item['subtotal']),
                'status': item['status'],
                'notes': item['notes'],
                'created_at': item['created_at'].isoformat()
            })
        
        return jsonify({
            'orders': list(tables.values()),
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
        
    except ValueError:
        raise InvalidUsage('Invalid pagination parameters')
    except Exception as e:
        app.logger.error(f"Error fetching completed orders: {str(e)}")
        raise InvalidUsage('Failed to fetch completed orders', status_code=500)

# Error handlers
@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    """Handle InvalidUsage exceptions."""
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    app.logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    app.logger.info('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
