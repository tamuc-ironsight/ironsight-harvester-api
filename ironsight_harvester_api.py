#!/usr/bin/env python3

import requests
import urllib3
from pprint import pprint
import ironsight_sql
import json
import random
import string
import sys

# Load in configuration file
with open('../config.json') as config_file:
    config = json.load(config_file)
    sql_server = config['sql_server']
    sql_user = config['sql_user']
    sql_pass = config['sql_pass']
    sql_db = config['sql_db']
    harvester_token = config['harvester_api_token']
    harvester_url = config['harvester_api_url']
    elastic_url = config['elasticsearch_url']
    elastic_token = config['elasticsearch_api_token']

# SQL utility functions
def get_vms():
    vmsJSON = ironsight_sql.query("SELECT * FROM virtual_machines", sql_server, sql_user, sql_pass, sql_db)
    return json.dumps(vmsJSON)

def get_templates():
    templatesJSON = ironsight_sql.query("SELECT * FROM templates", sql_server, sql_user, sql_pass, sql_db)
    return json.dumps(templatesJSON)

def get_users():
    usersJSON = ironsight_sql.query("SELECT * FROM users", sql_server, sql_user, sql_pass, sql_db)
    return json.dumps(usersJSON)

def get_labs():
    labsJSON = ironsight_sql.query("SELECT * FROM labs", sql_server, sql_user, sql_pass, sql_db)
    return json.dumps(labsJSON)

# Print templates nicely in console
def list_templates():
    templatesJSON = get_templates()
    ironsight_sql.pretty_response(templatesJSON)

# Make post request with JSON data
def post_request(url, data, token):
    urllib3.disable_warnings()
    response = requests.post(url, verify=False, json=data, headers={
                             'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Bearer ' + token})
    return response


def create_vm(vm_name, template_choice, user_name):
    # Load in templates from SQL
    templatesJSON = ironsight_sql.query("SELECT * FROM templates", sql_server, sql_user, sql_pass, sql_db)

    # Make sure template exists in SQL, if so, get image name and image size (in gigabytes)
    # Otherwise, print error and exit
    imageName = ""
    volumeSize = ""
    templateData = {}
    try:
        for template in templatesJSON:
            if template_choice == str(template['template_name']):
                imageName = str(template['template_image'])
                volumeSize = str(template['template_volume_size'])
                templateData = template
        if imageName == "":
            sys.exit(1)
    except:
        print("\nTemplate not found. Here are the available templates:")
        list_templates()
        sys.exit(1)

    # Configure VM properties
    # Change username to first letter of first name and last name
    if "_" in user_name:
        user_name_short = user_name[0].lower() + user_name.split("_")[1].lower()
    else:
        user_name_short = user_name.lower()
    vm_name = vm_name.replace("_", "-")
    vm_name = vm_name + "-" + user_name_short
    random_letters = "".join(random.choice(
    string.ascii_lowercase) for i in range(5))
    claim_name = vm_name + "-claim" + random_letters

    # Determine if VM should be enrolled in Elasticsearch or not
    if templateData['elastic_enrolled'] == 1:
        print("\nElasticsearch is enrolled in this template...")
        cloud_init_data = "#cloud-config\npackage_update: true\npackages:\n  - wget\nhostname: "+ vm_name + "\nusers:\n  - name: " + user_name + "\n    gecos: " + user_name + "\n    expiredate: '2032-09-01'\n    lock_passwd: false\n    passwd: $6$rounds=4096$Vd8W45YhfEELz1sq$HVp7eLIeJM.XOmN8o.RAwrg1UsqKpAXZBClx6uSX46j5Jwe4HN7cPdPYaKDLUVKYcAvjGTyRP3w26OrIo/.HD1\nruncmd:\n  - [ mkdir, /home/elastic ]\n  - [ wget, \"https://artifacts.elastic.co/downloads/beats/elastic-agent/elastic-agent-7.16.3-linux-x86_64.tar.gz\", -O, /home/elastic/agent.tar.gz ]\n  - [ tar, -xvf, /home/elastic/agent.tar.gz, -C, /home/elastic/ ]\n  - [ ./home/elastic/elastic-agent-7.16.3-linux-x86_64/elastic-agent, install, \"-f\",\"--url=" + elastic_url + "\", \"--enrollment-token=" + elastic_token + "\", \"--insecure\" ]\n  - [\"touch\", \"/etc/cloud/cloud-init.disabled\"]"
    else:
        print("\nSkipping Elasticsearch enrollment...")
        # cloud_init_data = "#cloud-config\npackage_update: false\nhostname: "+ vmName + "\nusers:\n  - name: " + userName + "\n    gecos: Student User\n    expiredate: '2032-09-01'\n    lock_passwd: false\n    passwd: $6$rounds=4096$Vd8W45YhfEELz1sq$HVp7eLIeJM.XOmN8o.RAwrg1UsqKpAXZBClx6uSX46j5Jwe4HN7cPdPYaKDLUVKYcAvjGTyRP3w26OrIo/.HD1"
        cloud_init_data = "#cloud-config"

    jsonData = {
        "apiVersion": "kubevirt.io/v1",
        "kind": "VirtualMachine",
        "metadata": {
            "namespace": "default",
            "annotations": {
                "harvesterhci.io/volumeClaimTemplates": "[{\"metadata\":{\"name\":\"" + claim_name + "\",\"annotations\":{\"harvesterhci.io/imageId\":\"default/" + imageName + "\"}},\"spec\":{\"accessModes\":[\"ReadWriteMany\"],\"resources\":{\"requests\":{\"storage\":\"" + str(volumeSize) + "Gi\"}},\"volumeMode\":\"Block\",\"storageClassName\":\"longhorn-" + imageName + "\"}}]",
                "network.harvesterhci.io/ips": "[]"
            },
            "labels": {
                "harvesterhci.io/creator": "harvester",
                "harvesterhci.io/os": "linux"
            },
            "name": vm_name
        },
        "__clone": True,
        "spec": {
            "running": True,
            "template": {
                "metadata": {
                    "annotations": {
                        "harvesterhci.io/sshNames": "[]"
                    },
                    "labels": {
                        "harvesterhci.io/vmName": vm_name
                    }
                },
                "spec": {
                    "domain": {
                        "machine": {
                            "type": "q35"
                        },
                        "cpu": {
                            "cores": 4,
                            "sockets": 1,
                            "threads": 1
                        },
                        "devices": {
                            "inputs": [],
                            "interfaces": [
                                {
                                    "masquerade": {},
                                    "model": "virtio",
                                    "name": "default"
                                }
                            ],
                            "disks": [
                                {
                                    "name": "disk-0",
                                    "disk": {
                                        "bus": "virtio"
                                    },
                                    "bootOrder": 1
                                },
                                {
                                    "name": "cloudinitdisk",
                                    "disk": {
                                        "bus": "virtio"
                                    }
                                }
                            ]
                        },
                        "resources": {
                            "limits": {
                                "memory": "8Gi",
                                "cpu": 4
                            }
                        }
                    },
                    "evictionStrategy": "LiveMigrate",
                    "hostname": vm_name,
                    "networks": [
                        {
                            "pod": {},
                            "name": "default"
                        }
                    ],
                    "volumes": [
                        {
                            "name": "disk-0",
                            "persistentVolumeClaim": {
                                "claimName": claim_name
                            }
                        },
                        {
                            "name": "cloudinitdisk",
                            "cloudInitConfigDrive": {
                                "userData" : 	cloud_init_data
                            }
                        }
                    ]
                }
            }
        }
    }

    print("VM Name: " + vm_name)
    print("Claim Name: " + claim_name)
    print("Image Name: " + imageName)
    print("User Name: " + user_name)
    print("Harvester Domin: " + harvester_url.split('apis')[0])
    print("Elastic Domin: " + elastic_url)
    print("Creating VM...")

    # Create VM with Harvester API
    postResponse = post_request(harvester_url, jsonData, harvester_token)
    print(postResponse.status_code)
    if postResponse.status_code == 409:
        print("VM already exists...")
        sys.exit(1)
    if postResponse.status_code == 201:
        print("VM Created Successfully")
    else:
        print("Error creating VM")
        pprint(postResponse.text.strip())
        sys.exit(1)

    # Add VM to the MySQL database
    port = -1
    # Get a free port between 5900 and 65535
    used_ports = ironsight_sql.query("SELECT port_number FROM virtual_machines", sql_server, sql_user, sql_pass, sql_db)
    # Map list of dictionaries to list of ports
    used_ports = [x['port_number'] for x in used_ports]
    for i in range(5900, 65535):
        if i not in used_ports:
            port = i
            break
    if port == -1:
        print("Error: No free ports available")
        sys.exit(1)
    print("Adding VM to the MySQL database...")
    query = str("INSERT INTO virtual_machines (vm_name, harvester_vm_name, port_number, lab_num, user_name, template_name) VALUES ('" + vm_name + "', '" + vm_name + "-harvester-name', '" + str(port) + "', '1', '" + user_name + "', '" + template_choice + "')")
    # print(query)
    ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db) 
    print("VM Added to the MySQL database with port: " + str(port))

if __name__ == "__main__":
    print("This script is a module for the Ironsight project. It is not meant to be run directly.")
    print("\nShowing configuration:")
    print("SQL Server: " + sql_server)
    print("SQL User: " + sql_user)
    print("SQL Password: " + ("Set" if sql_pass else "Not Set"))
    print("SQL Database: " + sql_db)
    print("Harvester URL: " + harvester_url)
    print("Elastic URL: " + elastic_url)
    print("Harvester Token: " + ("Set" if harvester_token else "Not Set"))
    print("Elastic Token: " + ("Set" if elastic_token else "Not Set"))
    sys.exit(1)