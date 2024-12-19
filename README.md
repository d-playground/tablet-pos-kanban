# Tablet POS System (v0.9)

![image](https://github.com/user-attachments/assets/0508a6d7-d38a-40d7-be0e-c05528c2b094)
![image](https://github.com/user-attachments/assets/82ccc075-2476-4475-917a-084ef637a9a3)


You can test here: http://15.165.189.74:5555/

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
- Docker (optional)

### Installation

#### Option 1: Local Installation

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

#### Option 2: Docker Installation

1. Clone the repository
```bash
git clone [repository-url]
cd tablet_pos
```

2. Build the Docker image
```bash
docker build -t tablet_pos .
```

3. Run MySQL container (if you don't have MySQL installed)
```bash
docker run --name pos-mysql \
  -e MYSQL_ROOT_PASSWORD=your_root_password \
  -e MYSQL_DATABASE=pos \
  -e MYSQL_USER=pos_user \
  -e MYSQL_PASSWORD=1234 \
  -p 3306:3306 \
  -d mysql:5.7
```

4. Initialize the database
```bash
docker exec -i pos-mysql mysql -uroot -pyour_root_password < database_setup.sql
```

5. Run the application container
```bash
docker run -d \
  --name tablet_pos \
  -p 5000:5000 \
  --link pos-mysql:mysql \
  -e DB_HOST=mysql \
  -e DB_USER=pos_user \
  -e DB_PASSWORD=1234 \
  -e DB_NAME=pos \
  tablet_pos
```

The application will be available at `http://localhost:5000`

### Docker Compose (Recommended)

1. Create a `docker-compose.yml` file:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DB_HOST=mysql
      - DB_USER=pos_user
      - DB_PASSWORD=1234
      - DB_NAME=pos
    depends_on:
      - mysql

  mysql:
    image: mysql:5.7
    environment:
      - MYSQL_ROOT_PASSWORD=your_root_password
      - MYSQL_DATABASE=pos
      - MYSQL_USER=pos_user
      - MYSQL_PASSWORD=1234
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./database_setup.sql:/docker-entrypoint-initdb.d/database_setup.sql

volumes:
  mysql_data:
```

2. Start the application using Docker Compose:
```bash
docker-compose up -d
```

3. Stop the application:
```bash
docker-compose down
```

## 🔧 Configuration

### Environment Variables
- `DB_HOST`: Database host (default: localhost)
- `DB_USER`: Database user (default: pos_user)
- `DB_PASSWORD`: Database password (default: 1234)
- `DB_NAME`: Database name (default: pos)
- `FLASK_ENV`: Application environment (development/production)

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
- Docker & Docker Compose

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
- Containerized deployment

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
