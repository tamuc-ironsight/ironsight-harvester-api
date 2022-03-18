import requests
import urllib3
from pprint import pprint
import ironsight_sql
import json
import random
import string
import sys

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

# Make post request with JSON data
def post_request(url, data, token):
    urllib3.disable_warnings()
    response = requests.post(url, verify=False, json=data, headers={
                             'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Bearer ' + token})
    return response

def listTemplates():
    templatesJSON = ironsight_sql.query("SELECT * FROM templates", sql_server, sql_user, sql_pass, sql_db)
    ironsight_sql.pretty_response(templatesJSON)

def createVM(vmName, template_choice, userName):
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
        listTemplates()
        sys.exit(1)

    # Configure VM properties
    vmName = vmName + "-" + userName
    randomLetters = "".join(random.choice(
    string.ascii_lowercase) for i in range(5))
    claimName = vmName + "-claim" + randomLetters
    if templateData['elastic_enrolled'] == 1:
        print("\nElasticsearch is enrolled in this template...")
        cloud_init_data = "#cloud-config\npackage_update: true\npackages:\n  - wget\nhostname: "+ vmName + "\nusers:\n  - name: " + userName + "\n    gecos: Student User\n    expiredate: '2032-09-01'\n    lock_passwd: false\n    passwd: $6$rounds=4096$Vd8W45YhfEELz1sq$HVp7eLIeJM.XOmN8o.RAwrg1UsqKpAXZBClx6uSX46j5Jwe4HN7cPdPYaKDLUVKYcAvjGTyRP3w26OrIo/.HD1\nruncmd:\n  - [ mkdir, /home/elastic ]\n  - [ wget, \"https://artifacts.elastic.co/downloads/beats/elastic-agent/elastic-agent-7.16.3-linux-x86_64.tar.gz\", -O, /home/elastic/agent.tar.gz ]\n  - [ tar, -xvf, /home/elastic/agent.tar.gz, -C, /home/elastic/ ]\n  - [ ./home/elastic/elastic-agent-7.16.3-linux-x86_64/elastic-agent, install, \"-f\",\"--url=" + elastic_url + "\", \"--enrollment-token=" + elastic_token + "\", \"--insecure\" ]\n  - [\"touch\", \"/etc/cloud/cloud-init.disabled\"]"
    else:
        print("\nSkipping Elasticsearch enrollment...")
        cloud_init_data = "#cloud-config\npackage_update: false\nhostname: "+ vmName + "\nusers:\n  - name: " + userName + "\n    gecos: Student User\n    expiredate: '2032-09-01'\n    lock_passwd: false\n    passwd: $6$rounds=4096$Vd8W45YhfEELz1sq$HVp7eLIeJM.XOmN8o.RAwrg1UsqKpAXZBClx6uSX46j5Jwe4HN7cPdPYaKDLUVKYcAvjGTyRP3w26OrIo/.HD1"

    jsonData = {
        "apiVersion": "kubevirt.io/v1",
        "kind": "VirtualMachine",
        "metadata": {
            "namespace": "default",
            "annotations": {
                "harvesterhci.io/volumeClaimTemplates": "[{\"metadata\":{\"name\":\"" + claimName + "\",\"annotations\":{\"harvesterhci.io/imageId\":\"default/" + imageName + "\"}},\"spec\":{\"accessModes\":[\"ReadWriteMany\"],\"resources\":{\"requests\":{\"storage\":\"" + str(volumeSize) + "Gi\"}},\"volumeMode\":\"Block\",\"storageClassName\":\"longhorn-" + imageName + "\"}}]",
                "network.harvesterhci.io/ips": "[]"
            },
            "labels": {
                "harvesterhci.io/creator": "harvester",
                "harvesterhci.io/os": "linux"
            },
            "name": vmName
        },
        "__clone": True,
        "spec": {
            "running": False,
            "template": {
                "metadata": {
                    "annotations": {
                        "harvesterhci.io/sshNames": "[]"
                    },
                    "labels": {
                        "harvesterhci.io/vmName": vmName
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
                    "hostname": vmName,
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
                                "claimName": claimName
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

    print("VM Name: " + vmName)
    print("Claim Name: " + claimName)
    print("Image Name: " + imageName)
    print("User Name: " + userName)
    print("Harvester Domin: " + harvester_url.split('apis')[0])
    print("Elastic Domin: " + elastic_url)
    print("Creating VM...")
    postResponse = post_request(harvester_url, jsonData, harvester_token)
    print(postResponse.status_code)
    if postResponse.status_code == 201:
        print("VM Created Successfully")
    else:
        print("Error creating VM")
        pprint(postResponse.text.strip())