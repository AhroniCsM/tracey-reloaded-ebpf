from flask import Flask, jsonify, request
import logging
import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool

logging.basicConfig(level=logging.INFO)

def custom_logger(message, level='info'):
    log_message = f"[CustomLogger] {message}"

    if level == 'info':
        logging.info(log_message)
    elif level == 'error':
        logging.error(log_message)
    elif level == 'warning':
        logging.warning(log_message)
    else:
        logging.debug(log_message)

# Constants
DATABASE_MAX_CONNECTIONS = 10

# Database parameters:
db_params = {
    'dbname': "mydatabase",
    'user': "user",
    'password': "password",
    'host': "postgresql",
    'port': 5432,
}

# Set up a database connection pool
pool = SimpleConnectionPool(
    minconn=1, maxconn=DATABASE_MAX_CONNECTIONS, **db_params)

def get_db_connection():
    return pool.getconn()

def release_db_connection(conn):
    pool.putconn(conn)

app = Flask(__name__)

@app.route('/checkorders')
def check_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT order_id, cupboards, computers, chairs, desks FROM orders WHERE is_processed = FALSE;")
        orders = cursor.fetchall()
        response_data = [
            {"order_id": row[0], "cupboards": row[1], "computers": row[2], "chairs": row[3], "desks": row[4]}
            for row in orders
        ]
        custom_logger(f"Fetched unprocessed orders: {response_data}", level='info')
        return jsonify(response_data)
    finally:
        cursor.close()
        release_db_connection(conn)

@app.route('/addorders', methods=['POST'])
def add_orders():
    order_data = request.get_json()
    cupboards = order_data.get("cupboards", 0)
    computers = order_data.get("computers", 0)
    chairs = order_data.get("chairs", 0)
    desks = order_data.get("desks", 0)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO orders (cupboards, computers, chairs, desks) VALUES (%s, %s, %s, %s) RETURNING order_id;",
            (cupboards, computers, chairs, desks)
        )
        order_id = cursor.fetchone()[0]
        custom_logger(f"Inserted new order with order_id: {order_id}", level='info')
        conn.commit()
        return jsonify({"message": "Order added successfully", "order_id": order_id}), 201
    finally:
        cursor.close()
        release_db_connection(conn)

@app.route('/deleteorders/<int:order_id>')
def delete_orders(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM orders WHERE order_id = %s;", (order_id,))
        if cursor.rowcount == 0:
            custom_logger(f"No order found to delete.", level='error')
            return jsonify({"message": "Order not found"}), 404
        custom_logger(f"Deleted order with order_id: {order_id}", level='info')
        conn.commit()
        return jsonify({"message": f"Order {order_id} deleted successfully"}), 200
    finally:
        cursor.close()
        release_db_connection(conn)

if __name__ == "__main__":
    custom_logger(f"Processor is starting...", level='info')
    app.run(host="0.0.0.0", port=8080)

    # Close all connections in the pool when the app shuts down
    def shutdown():
        pool.closeall()
    import atexit
    atexit.register(shutdown)
