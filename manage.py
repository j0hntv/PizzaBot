import argparse
import json
import os

import redis
import requests
from dotenv import load_dotenv
from tqdm import tqdm

import elasticpath


def get_json(path):
    with open(path) as file:
        json_data = json.load(file)

    return json_data


def create_menu(token, path):
    print('- Create menu')
    menu = get_json(path)

    for item in tqdm(menu):
        product_id = item['id']
        name = item['name']
        description = item['description']
        price = item['price']
        img_url = item['product_image']['url']
        img_name = img_url.split('/')[-1]
        img = requests.get(img_url).content

        try:
            create_file_response = elasticpath.create_file(token, img, img_name)
            create_product_response = elasticpath.create_product(token, product_id, name, description, price)

            image_id = create_file_response['data']['id']
            product_id = create_product_response['data']['id']
        
            elasticpath.create_main_image_relationship(token, product_id, image_id)
        except requests.exceptions.HTTPError as error:
            print(error)


def create_flows(token, path):
    flows = get_json(path)
    for flow in flows:
        print(f'- Create flow {flow["name"]}...', end=' ')
        try:
            create_flow_response = elasticpath.create_flow(token, flow['name'], flow['description'])
            print('OK!')

            flow_id = create_flow_response['data']['id']
            for field_name, field_type in flow['fields'].items():
                print(f'\t- Add field {field_name}...', end=' ')
                elasticpath.create_flow_field(token, field_name, field_type, field_name, flow_id)
                print('OK!')

        except requests.exceptions.HTTPError:
            print('Already exists')


def add_addresses(token, path, flow='Pizzeria'):
    addresses = get_json(path)
    print('\n- Add addresses...')

    for item in tqdm(addresses):
        values = {
            'Address': item['address']['full'],
            'Alias': item['alias'],
            'Latitude': item['coordinates']['lat'],
            'Longitude': item['coordinates']['lon'],
        }

        elasticpath.create_entry(token, flow, values)

    print('- Done.')


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--create_flows', help='Add pizzeria models (flows)')
    parser.add_argument('-a', '--add_addresses', help='Add pizzeria addresses')
    parser.add_argument('-m', '--create_menu', help='CMS product filling')
    return parser


if __name__ == "__main__":
    load_dotenv()
    args = create_arg_parser().parse_args()

    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    REDIS_HOST = os.getenv('REDIS_HOST')
    REDIS_PORT = os.getenv('REDIS_PORT')
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

    db = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)
    token = elasticpath.get_oauth_access_token(db, CLIENT_ID, CLIENT_SECRET)

    if args.create_menu:
        create_menu(token, args.create_menu)

    if args.create_flows:
        create_flows(token, args.create_flows)

    if args.add_addresses:
        add_addresses(token, args.add_addresses)
