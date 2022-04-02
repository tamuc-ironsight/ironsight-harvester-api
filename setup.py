#!/usr/bin/env python3

import json
from pprint import pprint

if __name__ == "__main__":
    print("Setting up...")
    # If config.json exists, then read it
    try:
        with open('config.json') as json_file:
            config = json.load(json_file)
            print("Config file found.")
            pprint(config)
            exit(1)
    # If config.json doesn't exist, then create it
    except FileNotFoundError:
        print("Creating config file...")
    # Create config.json file
    with open('config.json', 'w') as f:
        f.write('''{
    "sql_server": "",
    "sql_user": "",
    "sql_pass": "",
    "sql_db": "",

    "harvester_api_url": "",
    "harvester_api_token": "",

    "elastic_fleet_url": "",
    "elastic_fleet_api_token": "",
    "elastic_version": "",

    "elasticsearch_url": "",
    "elasticsearch_api_token": ""
}''')
    print("Config file created.")