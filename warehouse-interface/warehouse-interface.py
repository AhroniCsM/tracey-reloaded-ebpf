import requests
import time
import logging
import os
import random
import json

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

def generate_random_order():
    """Introduce errors at a 1 in 20 occurrence"""
    def random_computers():
        if random.randint(1, 20) == 1:
            return str("error")
        else:
            return random.randint(1, 10)

    def random_chairs():
        if random.randint(1, 20) == 1:
            return str("error")
        else:
            return random.randint(1, 10)

    def random_desks():
        if random.randint(1, 20) == 1:
            return str("error")
        else:
            return random.randint(1, 10)

    def random_cupboards():
        if random.randint(1, 20) == 1:
            return str("error")
        else:
            return random.randint(1, 10)
    """Generate a random order for products."""
    return {
        'computers': random_computers(),
        'chairs': random_chairs(),
        'desks': random_desks(),
        'cupboards': random_cupboards()
    }

def delete_order_from_order_processor(order_id):
    """Delete a processed order from the order-processor service."""
    url = f"http://order-processor-ebpf:8080/deleteorders/{order_id}"
    response = requests.get(url)
    custom_logger(f"Attempting to delete order with ID: {order_id}", level='info')

    if response.status_code != 200:
        custom_logger(f"Failed to delete order with ID: {order_id}", level='error')
        return None
    return response.json()

def get_order_from_order_processor():
    url = "http://order-processor-ebpf:8080/checkorders"
    response = requests.get(url)
    custom_logger(f"Getting orders from Processor", level='info')

    content_type = response.headers.get('Content-Type')
    if 'application/json' in content_type:
        return response.json()
    else:
        custom_logger(f"Unexpected response content type: {content_type}. Content: {response.text}", level='error')
        return None

def add_order_to_order_processor(order_data):
    url = "http://order-processor-ebpf:8080/addorders"
    response = requests.post(url, json=order_data)

    if response.status_code == 201:
        custom_logger(f"Order was added.", level='info')

    if response.text.strip():
        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            custom_logger(f"Failed to decode JSON from response. Content: {response.text}", level='error')
            return None
    else:
        custom_logger(f"Received an empty response from the server.", level='warning')
        return None

def check_stock_from_stock_processor(product):
    url = f"http://stock-controller-ebpf:8081/checkstock?product={product}"
    response = requests.get(url)
    custom_logger(f"Checking stock for product {product}.", level='info')

    if response.status_code != 200:
        custom_logger(f"Failed to check stock for {product}.", level='error')
        return None
    return response.json()

def increase_stock_from_stock_processor(product, quantity):
    url = "http://stock-controller-ebpf:8081/increasestock"
    data = {
        'product': product,
        'quantity': quantity
    }

    response = requests.post(url, json=data)
    custom_logger(f"Attempting to increase stock for {product} by {quantity}", level='info')

    if response.status_code != 200:
        custom_logger(f"Failed to increase stock for {product}", level='error')
        return None
    return response.json()

def decrease_stock_from_stock_processor(product, quantity):
    url = "http://stock-controller-ebpf:8081/decreasestock"
    data = {
        'product': product,
        'quantity': quantity
    }
    response = requests.post(url, json=data)
    custom_logger(f"Attempting to decrease stock for {product} by {quantity}", level='info')

    if response.status_code != 200:
        custom_logger(f"Failed to decrease stock for {product}", level='error')
        return None
    return response.json()

if __name__ == "__main__":
    while True:
        order = generate_random_order()
        add_order_to_order_processor(order)

        response = get_order_from_order_processor()

        if response:
            if isinstance(response, list):
                first_order = response[0] if response else None
                order_id = first_order.get('order_id', None) if first_order else None
            elif isinstance(response, dict):
                order_id = response.get('order_id', None)
            else:
                custom_logger("Unknown response type", level='error')
                order_id = None

            if order_id:
                for product, quantity in order.items():
                    stock_response = decrease_stock_from_stock_processor(product, quantity)
                    if stock_response and 'error' in stock_response:
                        logging.error(f"Failed to decrease stock for {product}")
                    else:
                        current_stock = check_stock_from_stock_processor(product)
                        if current_stock and current_stock['quantity'] < 100:
                            increase_stock_from_stock_processor(product, 100)
                        logging.info(f"Picked up order: {order_id} - {product} (Quantity: {quantity})")

                delete_order_response = delete_order_from_order_processor(order_id)
                if delete_order_response:
                    custom_logger("Deleted processed order with ID: {order_id}", level='info')
            else:
                custom_logger("No order_id found in the response", level='error')
        else:
            custom_logger("No more orders to pick up", level='info')

        time.sleep(10)
