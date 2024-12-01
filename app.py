from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import mysql.connector
from mysql.connector import pooling
from datetime import datetime

# 데이터베이스 설정
db_config = {
    'host': 'localhost',
    'user': 'user1',
    'password': '1234',
    'database': 'pos',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_general_ci'
}

# 데이터베이스 연결 풀 생성
db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="pos_pool",
    pool_size=5,
    **db_config
)

def get_db():
    return db_pool.get_connection()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 라우트 정의
@app.route("/")
def index():
    return render_template('index.html')

@app.route("/pos")
def pos():
    return render_template('pos.html')

@app.route("/order")
def order():
    return render_template('order.html')

@app.route("/bar1")
def bar1():
    return render_template('bar1.html')

@app.route("/bar2")
def bar2():
    return render_template('bar2.html')

@app.route("/kitchen")
def kitchen():
    return render_template('kitchen.html')

@app.route("/table-map")
def table_map():
    return render_template('table_map.html')

@app.route("/menu")
def menu():
    # 메뉴 가져오기
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('''
                SELECT id, name, price, category
                FROM menus
            ''')
            menus = cursor.fetchall()

    # 카테고리 가져오기
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT DISTINCT category FROM menus')
            categories_records = cursor.fetchall()
            categories = [record[0] for record in categories_records]

    return render_template('menu.html', menus=menus, categories=categories)

# 테이블 목록 가져오기
@app.route("/get_tables")
def get_tables():
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT id, name FROM tables')
            tables = cursor.fetchall()
    return jsonify({'status': 'success', 'tables': tables})

# 테이블 맵 관리 (테이블 추가/수정/삭제)
@app.route("/manage_tables", methods=['POST'])
def manage_tables():
    data = request.get_json()
    tables = data.get('tables')  # [{id, name, action}, ...]

    conn = get_db()
    cursor = conn.cursor()
    try:
        for table in tables:
            action = table.get('action')
            table_id = table.get('id')
            if action == 'add':
                cursor.execute("""
                    INSERT INTO tables (name) VALUES (%s)
                """, (table['name'],))
            elif action == 'update':
                if not table_id:
                    raise ValueError("테이블 ID가 필요합니다.")
                cursor.execute("""
                    UPDATE tables SET name=%s WHERE id=%s
                """, (table['name'], table_id))
            elif action == 'delete':
                if not table_id:
                    # id가 없으면 삭제 시도를 생략
                    continue
                cursor.execute("""
                    DELETE FROM tables WHERE id=%s
                """, (table_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(e)
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        cursor.close()
        conn.close()
    return jsonify({'status': 'success'})

# 주문 생성
@app.route("/place_order", methods=['POST'])
def place_order():
    data = request.get_json()
    table_id = data.get('table_id')
    items = data.get('items')  # [{'menu_id': ..., 'quantity': ...}, ...]

    conn = get_db()
    cursor = conn.cursor()
    try:
        # 새로운 주문 생성
        cursor.execute("""
            INSERT INTO orders (table_id, status, created_at)
            VALUES (%s, %s, %s)
        """, (table_id, 'pending', datetime.now()))
        order_id = cursor.lastrowid

        # 주문 아이템 추가
        for item in items:
            menu_id = item['menu_id']
            quantity = item['quantity']
            cursor.execute("""
                INSERT INTO order_items (order_id, menu_id, quantity)
                VALUES (%s, %s, %s)
            """, (order_id, menu_id, quantity))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(e)
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

    # 새로운 주문이 생성되었음을 모든 클라이언트에게 알림
    try:
        socketio.emit('new_order', {'order_id': order_id}, broadcast=True)
    except TypeError as te:
        print(f"Emit failed: {te}")
        # 대안: Namespace를 명시하거나, 다른 방법으로 브로드캐스트
        socketio.emit('new_order', {'order_id': order_id}, broadcast=True, namespace='/')

    return jsonify({'status': 'success', 'order_id': order_id})

# 주문 상태 업데이트
@app.route("/update_order_status", methods=['POST'])
def update_order_status():
    data = request.get_json()
    order_id = data.get('order_id')
    status = data.get('status')

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE orders SET status=%s WHERE id=%s
        """, (status, order_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(e)
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

    # 주문 상태 변경 알림
    try:
        socketio.emit('order_status_update', {'order_id': order_id, 'status': status}, broadcast=True)
    except TypeError as te:
        print(f"Emit failed: {te}")
        socketio.emit('order_status_update', {'order_id': order_id, 'status': status}, broadcast=True, namespace='/')

    return jsonify({'status': 'success'})

# 메뉴 관리 (메뉴 추가/수정/삭제)
@app.route("/manage_menus", methods=['POST'])
def manage_menus():
    data = request.get_json()
    menus = data.get('menus')  # [{id, name, price, category, action}, ...]

    conn = get_db()
    cursor = conn.cursor()
    try:
        for menu in menus:
            action = menu.get('action')
            if action == 'add':
                cursor.execute("""
                    INSERT INTO menus (name, price, category)
                    VALUES (%s, %s, %s)
                """, (menu['name'], menu['price'], menu['category']))
            elif action == 'update':
                cursor.execute("""
                    UPDATE menus SET name=%s, price=%s, category=%s WHERE id=%s
                """, (menu['name'], menu['price'], menu['category'], menu['id']))
            elif action == 'delete':
                cursor.execute("""
                    DELETE FROM menus WHERE id=%s
                """, (menu['id'],))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(e)
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        cursor.close()
        conn.close()
    return jsonify({'status': 'success'})

# SocketIO 이벤트 핸들러
@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected:', request.sid)

@app.route("/get_menus")
def get_menus():
    with get_db() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('''
                SELECT id, name, price, category
                FROM menus
            ''')
            menus = cursor.fetchall()
    return jsonify({'status': 'success', 'menus': menus})

if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000)
