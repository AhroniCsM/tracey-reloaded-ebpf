from flask import Flask, jsonify, request
import logging
import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager

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

@contextmanager
def get_db_connection():
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)

app = Flask(__name__)

@app.route('/checkstock')
def check_stock():
    product = request.args.get("product")
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT stock_quantity FROM stock WHERE product = %s;", (product,))
            stock = cursor.fetchone()
            if stock:
                custom_logger(f"Checked stock for product: {product}. Quantity: {stock[0]}.")
                return jsonify({"product": product, "quantity": stock[0]})
            custom_logger(f"Product: {product} not found in stock.", level='warning')
            return jsonify({"error": "Product not found"}), 404

@app.route('/increasestock', methods=['POST'])
def increase_stock():
    product = request.json.get("product")
    quantity = request.json.get("quantity")
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE stock SET stock_quantity = stock_quantity + %s WHERE product = %s;", (quantity, product))
            conn.commit()
            custom_logger(f"Increased stock for product: {product} by {quantity}.")
            return jsonify({"message": "Stock increased successfully"})

@app.route('/decreasestock', methods=['POST'])
def decrease_stock():
    product = request.json.get("product")
    quantity = request.json.get("quantity")
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE stock SET stock_quantity = stock_quantity - %s WHERE product = %s;", (quantity, product))
            conn.commit()
            custom_logger(f"Decreased stock for product: {product} by {quantity}.")
            return jsonify({"message": "Stock decreased successfully"})

if __name__ == "__main__":
    app.logger.info('Stock Controller is starting...')
    app.run(host="0.0.0.0", port=8081)

    # Close all connections in the pool when the app shuts down
    def shutdown():
        pool.closeall()
    import atexit
    atexit.register(shutdown)
