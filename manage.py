import argparse
import json
import os

import redis
import requests
from dotenv import load_dotenv
from tqdm import tqdm

import elasticpath


def get_json_menu(path):
    with open(path) as file:
        json_data = json.load(file)

    return json_data


def create_menu(token, path):
    menu = get_json_menu(path)

    for item in tqdm(menu):
        product_id = item['id']
        name = item['name']
        description = item['description']
        price = item['price']
        img_url = item['product_image']['url']
        img = requests.get(img_url).content

        try:
            create_file_response = elasticpath.create_file(token, img)
            create_product_response = elasticpath.create_product(token, product_id, name, description, price)

            image_id = create_file_response['data']['id']
            product_id = create_product_response['data']['id']
        
            elasticpath.create_main_image_relationship(token, product_id, image_id)
        except requests.exceptions.HTTPError as error:
            print(error)


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--create_menu', help='CMS product filling')
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
