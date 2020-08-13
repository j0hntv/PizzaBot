import json
from pprint import pprint

import elasticpath


def get_json(path):
    with open(path) as file:
        json_data = json.load(file)

    return json_data


def main():
    menu = get_json('menu.json')
    addresses = get_json('addresses.json')
    pprint(menu)
    pprint(addresses)


if __name__ == "__main__":
    main()

