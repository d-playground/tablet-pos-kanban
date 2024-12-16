# Tablet POS System v0.5

A modern, real-time Point of Sale (POS) system built with Flask and WebSocket, featuring a sleek dark-themed UI and intuitive order management.

## 🌟 Features

### 💻 Core Features
- Real-time order management with WebSocket
- Table status tracking and management
- Order history tracking per table
- Modern dark-themed UI with glass-morphism design
- Responsive design for tablet devices

### 🎯 Key Components
- **POS Interface**: 
  - Quick order entry with menu categories
  - Real-time table status updates
  - Order history per table
  - Checkout and payment processing
- **Order Board**: 
  - Real-time ticket management
  - Status tracking (Pending, In Progress, Completed)
  - Order notes and timestamps
- **Menu Management**: 
  - Menu item CRUD operations
  - Category management
  - Price and availability control
- **Table Management**: 
  - Dynamic table setup
  - Automatic status tracking
  - Active order monitoring

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- MySQL 5.7+
- Modern web browser with WebSocket support

### Installation

1. Clone the repository
```bash
git clone [repository-url]
cd tablet_pos
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up the database
```bash
mysql -u root -p < database_setup.sql
```

5. Run the application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 🔧 Configuration

### Database Setup
The system uses MySQL with the following main tables:
- `tables`: Store table information and status
- `menus`: Store menu items and categories
- `order_items`: Store order information with status tracking

### Database Triggers
- `after_orderitem_insert`: Automatically marks table as occupied when new order is created
- `after_orderitem_update`: Updates table status based on active orders

## 📱 Usage

### POS Interface
1. Select a table from the grid
2. View table's order history
3. Add menu items to order
4. Submit order or complete payment

### Order Management
1. Track order status in real-time
2. View order history by table
3. Process payments and clear tables
4. Add notes to orders

### Menu Management
1. Add/edit menu items
2. Set prices and categories
3. Toggle item availability
4. Manage menu categories

### Table Management
1. Add/edit tables
2. Monitor table status
3. View active orders
4. Track order history

## 🛠 Technical Stack

### Backend
- Flask (Python web framework)
- Flask-SocketIO (WebSocket support)
- MySQL (Database)
- MySQL Connector/Python

### Frontend
- Vanilla JavaScript
- WebSocket (Socket.IO)
- Modern CSS with Glass-morphism
- Responsive Design

### Features
- Real-time updates via WebSocket
- Automatic table status management
- Order history tracking
- Modern UI/UX design

## 📝 API Documentation

### Order Endpoints
- `GET /api/orders`: Get all active orders
- `POST /api/orders`: Create new order
- `PUT /api/orders/<id>/status`: Update order status
- `POST /api/orders/complete`: Complete order and clear table

### Table Endpoints
- `GET /api/tables`: Get all tables
- `GET /api/tables/<id>/orders`: Get table's orders
- `PUT /api/tables`: Update table information

### Menu Endpoints
- `GET /api/menus`: Get all menu items
- `PUT /api/menus`: Update menu items

### WebSocket Events
- `order_status_updated`: Order status changes
- `new_orders`: New order notifications
- `table_updated`: Table status updates
- `order_completed`: Order completion notification
