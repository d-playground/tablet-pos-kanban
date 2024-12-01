# Kanban POS System for Tablet PC

Toy Project for Full-stack Web Application Development.

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Technologies Used](#technologies-used)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Setup Instructions](#setup-instructions)
- [Usage](#usage)
- [File Structure](#file-structure)
- [API Endpoints](#api-endpoints)
- [SocketIO Events](#socketio-events)

## Introduction

The **Kanban POS System for Tablet** is a application designed for managing restaurant operations. Built with Flask, MySQL, and SocketIO, this system facilitates table management, menu administration, order processing, and real-time order tracking through a Kanban-style board. It provides intuitive interfaces for both front-of-house staff and kitchen/bar personnel, ensuring seamless communication and efficient workflow.

## Features

- **Table Management:** Add, update, and delete tables with ease.
- **Menu Management:** Manage menu items, including adding new dishes, updating existing ones, and removing discontinued items.
- **Order Processing:** Select tables, choose menu items, and place orders with real-time updates.
- **Real-Time Updates:** Orders and their statuses are updated in real-time across all connected clients using SocketIO.
- **Kanban Board for Orders:** Visualize orders in different stages (Pending, In Progress, Completed) through an interactive Kanban board.
- **Responsive Design:** User-friendly interfaces optimized for various devices.
- **Database Connection Pooling:** Efficient handling of database connections using MySQL connection pooling.

## Stacks Used

- **Backend:**
  - [Flask](https://flask.palletsprojects.com/) - Web framework for Python.
  - [Flask-SocketIO](https://flask-socketio.readthedocs.io/) - Enables real-time communication.
  - [MySQL](https://www.mysql.com/) - Relational database management system.
  - [mysql-connector-python](https://dev.mysql.com/doc/connector-python/en/) - MySQL driver for Python.

- **Frontend:**
  - HTML5 & CSS3
  - Vanilla JavaScript

- **Others:**
  - [Socket.IO](https://socket.io/) - Real-time bidirectional event-based communication.

## Installation

### Prerequisites

Ensure you have the following installed on your system:

- [Python 3.7+](https://www.python.org/downloads/)
- [MySQL Server](https://dev.mysql.com/downloads/mysql/)
- [Git](https://git-scm.com/downloads)

### Setup Instructions

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/d-playground/tablet-pos-kanban.git
   cd tablet-pos-kanban
   ```

2. **Create and Activate Virtual Environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the Database:**

   - **Create MySQL Database:**

     Log in to your MySQL server and create the `pos` database:

     ```sql
     CREATE DATABASE pos CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
     ```

   - **Create Tables:**

     Execute the following SQL commands to create necessary tables:

     ```sql
     USE pos;

     CREATE TABLE tables (
         id INT AUTO_INCREMENT PRIMARY KEY,
         name VARCHAR(50) NOT NULL
     );

     CREATE TABLE menus (
         id INT AUTO_INCREMENT PRIMARY KEY,
         name VARCHAR(100) NOT NULL,
         price DECIMAL(10,2) NOT NULL,
         category VARCHAR(50) NOT NULL
     );

     CREATE TABLE orders (
         id INT AUTO_INCREMENT PRIMARY KEY,
         table_id INT NOT NULL,
         status VARCHAR(20) NOT NULL,
         created_at DATETIME NOT NULL,
         FOREIGN KEY (table_id) REFERENCES tables(id)
     );

     CREATE TABLE order_items (
         id INT AUTO_INCREMENT PRIMARY KEY,
         order_id INT NOT NULL,
         menu_id INT NOT NULL,
         quantity INT NOT NULL,
         FOREIGN KEY (order_id) REFERENCES orders(id),
         FOREIGN KEY (menu_id) REFERENCES menus(id)
     );
     ```

5. **Configure Application Settings:**

   - Open `app.py` and update the `db_config` dictionary with your MySQL credentials:

     ```python
     db_config = {
         'host': 'your_mysql_host',
         'user': 'your_mysql_user',
         'password': 'your_mysql_password',
         'database': 'pos',
         'charset': 'utf8mb4',
         'collation': 'utf8mb4_general_ci'
     }
     ```

6. **Run the Application:**

   ```bash
   python app.py
   ```

   The application will be accessible at `http://127.0.0.1:5000/`.

## Usage

1. **Access the POS Interface:**

   Navigate to `http://127.0.0.1:5000/pos` to access the main POS interface where you can select tables, choose menu items, and place orders.

2. **Manage Tables:**

   Go to `http://127.0.0.1:5000/table-map` to add, update, or delete tables.

3. **Manage Menus:**

   Access `http://127.0.0.1:5000/menu` to manage menu items.

4. **Monitor Orders:**

   Visit `http://127.0.0.1:5000/bar1` to view and manage orders through the Kanban board.

## File Structure

```plaintext
tablet-pos-kanban/
├── app.py
├── requirements.txt
├── templates/
│   ├── index.html
│   ├── pos.html
│   ├── order.html
│   ├── bar1.html
│   ├── bar2.html
│   ├── kitchen.html
│   ├── table_map.html
│   └── menu.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── scripts.js
└── README.md
```

- **app.py:** Main Flask application containing routes, database interactions, and SocketIO event handlers.
- **requirements.txt:** Lists all Python dependencies.
- **templates/:** Contains HTML templates for different pages.
- **static/:** Holds static files like CSS and JavaScript.
- **README.md:** Documentation for the project.

## API Endpoints

### Routes

- **`GET /`**
  - **Description:** Renders the home page.
  - **Response:** `index.html`

- **`GET /pos`**
  - **Description:** Renders the POS interface.
  - **Response:** `pos.html`

- **`GET /order`**
  - **Description:** Renders the order management page.
  - **Response:** `order.html`

- **`GET /bar1`**
  - **Description:** Renders the Bar1 Kanban board.
  - **Response:** `bar1.html`

- **`GET /bar2`**
  - **Description:** Renders the Bar2 Kanban board.
  - **Response:** `bar2.html`

- **`GET /kitchen`**
  - **Description:** Renders the kitchen management page.
  - **Response:** `kitchen.html`

- **`GET /table-map`**
  - **Description:** Renders the table map management page.
  - **Response:** `table_map.html`

- **`GET /menu`**
  - **Description:** Renders the menu management page.
  - **Response:** `menu.html`

### API Endpoints

- **`GET /get_tables`**
  - **Description:** Retrieves the list of tables.
  - **Response:** JSON object containing tables.

- **`POST /manage_tables`**
  - **Description:** Adds, updates, or deletes tables based on the action specified.
  - **Request Body:** JSON array of table objects with `id`, `name`, and `action`.
  - **Response:** JSON status.

- **`POST /place_order`**
  - **Description:** Places a new order.
  - **Request Body:** JSON object with `table_id` and `items`.
  - **Response:** JSON status and `order_id`.

- **`POST /update_order_status`**
  - **Description:** Updates the status of an existing order.
  - **Request Body:** JSON object with `order_id` and `status`.
  - **Response:** JSON status.

- **`POST /manage_menus`**
  - **Description:** Adds, updates, or deletes menu items based on the action specified.
  - **Request Body:** JSON array of menu objects with `id`, `name`, `price`, `category`, and `action`.
  - **Response:** JSON status.

- **`GET /get_menus`**
  - **Description:** Retrieves the list of menu items.
  - **Response:** JSON object containing menus.

- **`GET /get_orders`**
  - **Description:** Retrieves the list of orders.
  - **Response:** JSON object containing orders.

## SocketIO Events

- **`connect`**
  - **Description:** Triggered when a client connects to the SocketIO server.
  - **Handler:** Logs the connection.

- **`disconnect`**
  - **Description:** Triggered when a client disconnects from the SocketIO server.
  - **Handler:** Logs the disconnection.

- **`new_order`**
  - **Description:** Emitted when a new order is placed.
  - **Payload:** `{ 'order_id': <order_id> }`
  - **Broadcast:** Sent to all connected clients.

- **`order_status_update`**
  - **Description:** Emitted when an order's status is updated.
  - **Payload:** `{ 'order_id': <order_id>, 'status': <new_status> }`
  - **Broadcast:** Sent to all connected clients.
