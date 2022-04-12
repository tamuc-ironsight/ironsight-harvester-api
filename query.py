#!/usr/bin/env python3
import requests
import sys
import json
# sys.path.insert(0, './ironsight_harvester_api')
import ironsight_harvester_api as ironsight

# Example query
# curl --header "Authorization: ApiKey YU44dnIzNEJ0UFZoZkJIa19OYWs6emJRSk01LWhTMC1hNm0xMFBPUGZuUQ==" --header "Content-Type: application/json" -XGET "http://ssh.tylerharrison.dev:9200/_search" -d'
# {
#   "query": {
#     "match_all": {}
#   }
# }'

# Incoming data looks like this: '\{\"size\":100,\"aggs\":\{\"hostnames\":\{\"terms\":\{\"field\":\"host.name\",\"size\":100\}\}\}\}'

# Make a GET request to the Elastic API
def query_elastic(raw_query, index=""):
    # Undo PHP security escaping
    raw_query = raw_query.replace("\\", "")

    # Load in configuration file
    with open('config.json') as config_file:
        config = json.load(config_file)
        elastic_url = config['elasticsearch_url']
        elastic_token = config['elasticsearch_api_token']

    # elastic_url = elastic_url.replace(":8220", ":9200")
    if elastic_url[-1] != "/":
        elastic_url += "/"
    elastic_url = elastic_url + index + "/_search"
    
    headers = {"Content-Type" : "application/json", "Authorization": str("ApiKey " + elastic_token)}
    response = requests.get(elastic_url, headers=headers, data=raw_query)

    return json.dumps(response.json())

def query_ironsight(raw_query):
    with open('config.json') as config_file:
        config = json.load(config_file)
        sql_server = config['sql_server']
        sql_user = config['sql_user']
        sql_pass = config['sql_pass']
        sql_db = config['sql_db']

    if raw_query == "get_users":
        return(ironsight.get_users())

    elif raw_query == "get_vms":
        return(ironsight.get_vms())

    elif raw_query == "get_labs":
        return(ironsight.get_labs())

    elif raw_query == "get_templates":
        return(ironsight.get_templates())
    
    elif raw_query == "get_tags":
        return(ironsight.get_tags())

    else:
        return "Invalid query"

if __name__ == "__main__":
    # Queries Elastic directly
    if "--elastic" in sys.argv:
        sys.argv.remove("--elastic")
        # Default: query all
        if len(sys.argv) < 2:
            query = ""
            print(query_elastic(query))
    
        # User specified query
        elif len(sys.argv) == 2:
            query = sys.argv[1]
            print(query_elastic(query))

        # User specified query and index
        elif len(sys.argv) == 3:
            query = sys.argv[1]
            index = sys.argv[2]
            print(query_elastic(query, index))
    
    # Queries SQL or Harvester
    elif "--data" in sys.argv:
        sys.argv.remove("--data")
        # Default: Return blank json
        if len(sys.argv) < 2:
            print("{}")
        # User specified query
        elif len(sys.argv) == 2:
            query = sys.argv[1]
            print(query_ironsight(query))
