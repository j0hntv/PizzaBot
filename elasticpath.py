import requests
from slugify import slugify


def get_oauth_access_token(db, client_id, client_secret, expires=3000):
    access_token = db.get('elasticpath_token')

    if access_token:
        return access_token

    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    response.raise_for_status()
    access_token = response.json()['access_token']
    db.set('elasticpath_token', access_token, ex=expires)
    return access_token


def create_file(token, file, file_name, public=True):
    url = 'https://api.moltin.com/v2/files/'
    headers = {'Authorization': f'Bearer {token}'}

    files = {
        'file': (file_name, file),
        'public': public
    }
    
    response = requests.post(url, headers=headers, files=files)
    response.raise_for_status()

    return response.json()


def create_product(token, product_id, name, description, price):
    headers = {'Authorization': f'Bearer {token}'}
    url = 'https://api.moltin.com/v2/products/'

    payload = {
        'data': {
            'type': 'product',
            'name': name,
            'slug': slugify(name),
            'sku': str(product_id),
            'manage_stock': False,
            'description': description,
            'price': [
                {
                    'amount': price,
                    'currency': 'RUB',
                    'includes_tax': True,
                }
            ],
            'status': 'live',
            'commodity_type': 'physical',
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def create_main_image_relationship(token, product_id, image_id):
    url = f'https://api.moltin.com/v2/products/{product_id}/relationships/main-image'
    headers = {'Authorization': f'Bearer {token}'}

    payload = {
        'data': {
            'type': 'main_image',
            'id': image_id,
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def create_flow(token, name, description):
    headers = {'Authorization': f'Bearer {token}'}
    url = 'https://api.moltin.com/v2/flows/'

    payload = {
        'data': {
            'type': 'flow',
            'name': name,
            'slug': slugify(name),
            'description': description,
            'enabled': True,
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def create_entry(token, flow_slug, values):
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.moltin.com/v2/flows/{flow_slug}/entries'

    payload = {
        'data': {
            'type': 'entry',
            'Alias': 'value',
            **values,
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def get_entry(token, slug, id):
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.moltin.com/v2/flows/{slug}/entries/{id}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    entry = response.json()
    return entry['data']


def get_all_entries(token, slug):
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.moltin.com/v2/flows/{slug}/entries'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    entries = response.json()['data']
    return [
        {'Address': entry['Address'], 'coordinates': (entry['Latitude'], entry['Longitude']), 'id': entry['id']} for entry in entries]


def create_flow_field(token, name, field_type, description, flow_id):
    headers = {'Authorization': f'Bearer {token}'}
    url = 'https://api.moltin.com/v2/fields/'

    relationships = {
        'flow': {
            'data': {
                'type': 'flow',
                'id': flow_id,
            }
        }
    }

    payload = {
        'data': {
            'type': 'field',
            'name': name,
            'slug': slugify(name),
            'field_type': field_type,
            'description': description,
            'required': False,
            'enabled': True,
            'relationships': relationships,
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def get_products(token, product_id=None, limit=5, offset=0):
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.moltin.com/v2/products/'

    if product_id:
        url += product_id
    else:
        url += f'?page[limit]={limit}&page[offset]={offset}/'
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def add_product_to_cart(token, cart, product_id, quantity=1):
    headers = {'Authorization': f'Bearer {token}'}
    payload = {
        "data": {
            "id": product_id,
            "type": "cart_item",
            "quantity": quantity
        }
    }

    url = f'https://api.moltin.com/v2/carts/{cart}/items'
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def get_a_cart(token, cart):
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.moltin.com/v2/carts/{cart}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_cart_items(token, cart):
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.moltin.com/v2/carts/{cart}/items'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['data']


def remove_cart_item(token, cart, product_id):
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.moltin.com/v2/carts/{cart}/items/{product_id}'
    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_formatted_cart_items(cart, cart_items):
    items = []
    for item in cart_items:
        name = item['name']
        description = item['description']
        quantity = item['quantity']
        cost = item['meta']['display_price']['with_tax']['value']['formatted']
        items.append(f'{name}: *{quantity}* шт.\n_{description}_\n*{cost} ₽*')

    total_cost = cart['meta']['display_price']['with_tax']['formatted']
    items.append(f'\nИтого: *{total_cost} ₽*')

    return '\n\n'.join(items)


def get_formatted_cart_items_without_description(cart, cart_items):
    items = []
    for item in cart_items:
        name = item['name']
        quantity = item['quantity']
        cost = item['meta']['display_price']['with_tax']['value']['formatted']
        items.append(f'{name}: *{quantity}* шт.\n*{cost} ₽*')

    total_cost = cart['meta']['display_price']['with_tax']['formatted']
    items.append(f'\nИтого: *{total_cost} ₽*')

    return '\n'.join(items)


def get_image_url(token, image_id):
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.moltin.com/v2/files/{image_id}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['data']['link']['href']


def get_product_markdown_output(product):
    name = product['data']['name']
    description = product['data']['description']
    price = product['data']['price'][0]['amount']
    output = f'*{name}*\n_{description}_\n\n*{price} ₽*'
    return output


def create_customer(token, name, email, customer_type='customer'):
    url = 'https://api.moltin.com/v2/customers'
    headers = {'Authorization': f'Bearer {token}'}
    payload = {
        "data": {
            "name": name,
            "email": email,
            "type": customer_type
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()
