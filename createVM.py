from ironsight_harvester_api import createVM
import random
import string
import sys
import json
import ironsight_sql
from pprint import pprint

def listTemplates():
    templatesJSON = ironsight_sql.query("SELECT * FROM templates", sql_server, sql_user, sql_pass, sql_db)
    ironsight_sql.pretty_response(templatesJSON)

if __name__ == "__main__":

    if "--templates" in sys.argv:
        listTemplates()
        sys.exit(0)

    if len(sys.argv) < 4:
        print("Usage: python3 createVM.py [vmName] [template] [studentName]")
        sys.exit(1)
    
    # Load in configuration file
    with open('config.json') as config_file:
        config = json.load(config_file)
        sql_server = config['sql_server']
        sql_user = config['sql_user']
        sql_pass = config['sql_pass']
        sql_db = config['sql_db']
        harvester_token = config['harvester_api_token']
        harvester_url = config['harvester_api_url']
        elastic_url = config['elasticsearch_url']
        elastic_token = config['elasticsearch_api_token']

    # Load in templates from SQL
    templatesJSON = ironsight_sql.query("SELECT * FROM templates", sql_server, sql_user, sql_pass, sql_db)

    # Make sure template exists in SQL, if so, get image name and image size (in gigabytes)
    # Otherwise, print error and exit
    imageName = ""
    volumeSize = ""
    try:
        for template in templatesJSON:
            if str(sys.argv[2]) == str(template['template_name']):
                imageName = str(template['template_image'])
                volumeSize = str(template['template_volume_size'])
    except:
        print("Template not found. Here are the available templates:")
        listTemplates()
        sys.exit(1)

    # Configure VM properties
    userName = str(sys.argv[3])
    vmName = str(sys.argv[1]) + "-" + userName
    randomLetters = "".join(random.choice(
    string.ascii_lowercase) for i in range(5))
    claimName = vmName + "-claim" + randomLetters

    # Create virtual machine
    createVM(vmName, claimName, imageName, volumeSize, userName, harvester_url, harvester_token, elastic_url, elastic_token)