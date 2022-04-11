#!/usr/bin/env python3

import requests
import urllib3
from pprint import pprint
import ironsight_sql
import json
import random
import string
import sys
import time

# Determine if config.json is here or in parent directory


def get_config():
    try:
        with open('config.json') as f:
            return "config.json"
    except FileNotFoundError:
        try:
            with open('../config.json') as f:
                return "../config.json"
        except FileNotFoundError:
            print(
                "Config file not found. Please create config.json in current directory or parent directory.")
            exit(1)


# Load in configuration file
config_path = get_config()

with open(config_path) as config_file:
    config = json.load(config_file)
    sql_server = config['sql_server']
    sql_user = config['sql_user']
    sql_pass = config['sql_pass']
    sql_db = config['sql_db']
    harvester_token = config['harvester_api_token']
    harvester_url = config['harvester_api_url']
    elastic_url = config['elastic_fleet_url']
    elastic_token = config['elastic_fleet_api_token']
    elastic_version = config['elastic_version']

# SQL utility functions


def get_tags():
    tagsJSON = ironsight_sql.query(
        "SELECT * FROM tags", sql_server, sql_user, sql_pass, sql_db)
    # Sort by tag_id
    tagsJSON.sort(key=lambda x: x['tag_id'])
    return json.dumps(tagsJSON)

# Example:
    # {
    #     "vm_name": "android-tharrison",
    #     "harvester_vm_name": "android-tharrison-harvester-name",
    #     "port_number": 5904,
    #     "elastic_agent_id": null,
    #     "template_name": "android",
    #     "tags": [
    #         {
    #             "tag": "android",
    #             "type": "os",
    #             "tag_id": 10
    #         },
    #         {
    #             "tag": "tyler_harrison",
    #             "type": "user",
    #             "tag_id": 9
    #         }
    #     ],
    #     "users": []
    # }


def get_vms():
    vmsJSON = ironsight_sql.query(
        "SELECT * FROM virtual_machines", sql_server, sql_user, sql_pass, sql_db)
    # Pull out the tags
    for template in vmsJSON:
        template['tags'] = json.loads(template['tags'])['tags']

    # Populate the users field
    for vm in vmsJSON:
        vm['users'] = []

    # Handle the many-to-many relationship between virtual machines and users ("virtual_machine_has_users")
    # Stored like this: [{'vm_name': 'android-tharrison', 'user_name': 'tyler_harrison'}]
    virtual_machine_has_users = ironsight_sql.query(
        "SELECT * FROM virtual_machine_has_users", sql_server, sql_user, sql_pass, sql_db)
    for vm_user in virtual_machine_has_users:
        for vm in vmsJSON:
            if vm_user['vm_name'] == vm['vm_name']:
                vm['users'].append(vm_user['user_name'])

    # Populate labs with empty list
    for vm in vmsJSON:
        vm['labs'] = []

    # Handle the many-to-many relationship between virtual machines and labs ("virtual_machine_has_labs")
    # Stored like this: [{'vm_name': 'android-tharrison', 'lab_num': '1'}]
    virtual_machine_has_labs = ironsight_sql.query(
        "SELECT * FROM virtual_machine_has_labs", sql_server, sql_user, sql_pass, sql_db)
    for vm_lab in virtual_machine_has_labs:
        for vm in vmsJSON:
            if vm_lab['vm_name'] == vm['vm_name']:
                vm['labs'].append(vm_lab['lab_num'])

    return json.dumps(vmsJSON)


def get_templates():
    templatesJSON = ironsight_sql.query(
        "SELECT * FROM vm_templates", sql_server, sql_user, sql_pass, sql_db)
    # Pull out the tags
    for template in templatesJSON:
        template['tags'] = json.loads(template['tags'])['tags']
        template['template_data'] = json.loads(template['template_data'])

    # Populate labs with empty list
    for template in templatesJSON:
        template['labs'] = []

    # Handle the many-to-many relationship between templates and labs ("labs_has_vm_templates")
    # Stored like this: [{'id': '1', 'lab_num': '1', 'template_name': 'android'}]
    labs_has_vm_templates = ironsight_sql.query(
        "SELECT * FROM labs_has_vm_templates", sql_server, sql_user, sql_pass, sql_db)
    for lab_template in labs_has_vm_templates:
        for template in templatesJSON:
            if lab_template['template_name'] == template['template_name']:
                template['labs'].append(lab_template['lab_num'])

    return json.dumps(templatesJSON)


def get_users():
    usersJSON = ironsight_sql.query(
        "SELECT * FROM users", sql_server, sql_user, sql_pass, sql_db)
    # Pull out the tags
    for template in usersJSON:
        template['tags'] = json.loads(template['tags'])['tags']

    # Populate labs with empty list
    for user in usersJSON:
        user['virtual_machines'] = []

    # Handle the many-to-many relationship between virtual machines and users ("virtual_machine_has_users")
    # Stored like this: [{'vm_name': 'android-tharrison', 'user_name': 'tyler_harrison'}]
    virtual_machine_has_users = ironsight_sql.query(
        "SELECT * FROM virtual_machine_has_users", sql_server, sql_user, sql_pass, sql_db)
    for vm_user in virtual_machine_has_users:
        for user in usersJSON:
            if vm_user['user_name'] == user['user_name']:
                user['virtual_machines'].append(vm_user['vm_name'])

    return json.dumps(usersJSON)


def get_labs():
    labsJSON = ironsight_sql.query(
        "SELECT * FROM labs", sql_server, sql_user, sql_pass, sql_db)
    # Pull out the tags
    for template in labsJSON:
        template['tags'] = json.loads(template['tags'])['tags']
    # Fix datetime.datetime object to make it JSON serializable
    for lab in labsJSON:
        lab['date_start'] = str(lab['date_start'])
        lab['date_end'] = str(lab['date_end'])

    # Populate labs with empty lists
    for lab in labsJSON:
        lab['virtual_machines'] = []
        lab['templates'] = []

    # Handle the many-to-many relationship between virtual machines and labs ("virtual_machine_has_labs")
    # Stored like this: [{'vm_name': 'android-tharrison', 'lab_num': '1'}]
    virtual_machine_has_labs = ironsight_sql.query(
        "SELECT * FROM virtual_machine_has_labs", sql_server, sql_user, sql_pass, sql_db)
    for vm_lab in virtual_machine_has_labs:
        for lab in labsJSON:
            if vm_lab['lab_num'] == lab['lab_num']:
                lab['virtual_machines'].append(vm_lab['vm_name'])

    # Handle the many-to-many relationship between virtual machines and templates ("labs_has_vm_templates")
    # Stored like this: [{'id': '1', 'lab_num': '1', 'template_name': 'android'}]
    labs_has_vm_templates = ironsight_sql.query(
        "SELECT * FROM labs_has_vm_templates", sql_server, sql_user, sql_pass, sql_db)
    for lab_template in labs_has_vm_templates:
        for lab in labsJSON:
            if lab_template['lab_num'] == lab['lab_num']:
                lab['templates'].append(lab_template['template_name'])

    # Use get_vms() to get the users for each lab
    vmsJSON = get_vms()
    vms = json.loads(vmsJSON)
    for lab in labsJSON:
        lab['users'] = []
        for vm in vms:
            if lab['lab_num'] in vm['labs']:
                lab['users'] += vm['users']
                # Remove duplicates
                lab['users'] = list(set(lab['users']))
    return json.dumps(labsJSON)

def get_classes():
    tags = get_tags()
    tags = json.loads(tags)
    classes = []
    for tag in tags:
        if tag['type'] == 'class':
            classes.append(tag)
    return json.dumps(classes)

def get_lab_overview(lab_num):
    # Get the lab info by using the lab_num
    labs = get_labs()
    labs = json.loads(labs)
    lab_response = {}
    for lab in labs:
        if lab['lab_num'] == int(lab_num):
            lab_response = lab
    return json.dumps(lab_response)

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

def post_request_params(url, token):
    urllib3.disable_warnings()
    response = requests.post(url, verify=False, headers={
                                'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Bearer ' + token})
    return response


def get_request(url, token):
    urllib3.disable_warnings()
    response = requests.get(url, verify=False, headers={
                            'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Bearer ' + token})
    return response


def create_vm(vm_name, template_choice, user_name):
    # Load in templates from SQL
    templatesJSON = ironsight_sql.query(
        "SELECT * FROM vm_templates", sql_server, sql_user, sql_pass, sql_db)

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
        user_name_short = user_name[0].lower(
        ) + user_name.split("_")[1].lower()
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
        cloud_init_data = "#cloud-config\npackage_update: true\npackages:\n  - wget\nhostname: " + vm_name + "\nusers:\n  - name: " + user_name + "\n    gecos: " + user_name + \
            "\n    expiredate: '2032-09-01'\n    lock_passwd: false\n    passwd: $6$rounds=4096$Vd8W45YhfEELz1sq$HVp7eLIeJM.XOmN8o.RAwrg1UsqKpAXZBClx6uSX46j5Jwe4HN7cPdPYaKDLUVKYcAvjGTyRP3w26OrIo/.HD1\nruncmd:\n  - [ mkdir, /home/elastic ]\n  - [ wget, \"https://artifacts.elastic.co/downloads/beats/elastic-agent/elastic-agent-" + elastic_version + \
            "-linux-x86_64.tar.gz\", -O, /home/elastic/agent.tar.gz ]\n  - [ tar, -xvf, /home/elastic/agent.tar.gz, -C, /home/elastic/ ]\n  - [ ./home/elastic/elastic-agent-" + elastic_version + \
            "-linux-x86_64/elastic-agent, install, \"-f\",\"--url=" + elastic_url + "\", \"--enrollment-token=" + \
            elastic_token + \
            "\", \"--insecure\" ]\n  - [\"touch\", \"/etc/cloud/cloud-init.disabled\"]"
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
                                "userData": 	cloud_init_data
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

    # Add VM to the MySQL database
    port = -1
    # Get a free port between 5900 and 65535
    used_ports = ironsight_sql.query(
        "SELECT port_number FROM virtual_machines", sql_server, sql_user, sql_pass, sql_db)
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
    # INSERT INTO `ironsight`.`virtual_machines` (`vm_name`, `harvester_vm_name`, `port_number`, `template_name`, `tags`) VALUES ('android-tharrison', 'android-tharrison-harvester-name', '5904', 'android', '{\"tags\": [\"android\"]}');
    query = str("INSERT INTO virtual_machines (vm_name, harvester_vm_name, port_number, template_name, tags) VALUES ('" + vm_name +
                "', '" + vm_name + "-harvester-name', '" + str(port) + "', '" + template_choice + "', '{\"tags\": [\"" + user_name + "\"]}\')")
    # print(query)
    ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)
    print("VM Added to the MySQL database with port: " + str(port))

    # Create VM with Harvester API
    query_url = harvester_url + "/apis/kubevirt.io/v1/namespaces/default/virtualmachines"
    postResponse = post_request(query_url, jsonData, harvester_token)
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


def get_node_names():
    query_url = harvester_url + "/v1/harvester/nodes"
    getResponse = get_request(query_url, harvester_token)
    response = {'hosts': []}
    for node in getResponse.json()['data']:
        hostname = node['id']
        ip = node['metadata']['annotations']['rke2.io/internal-ip']
        response['hosts'].append({'hostname': hostname, 'ip': ip})
    response = json.dumps(response)
    return response


def get_num_vms():
    query_url = harvester_url + "/v1/harvester/kubevirt.io.virtualmachines/default"
    getResponse = get_request(query_url, harvester_token)
    return len(getResponse.json()['data'])

def get_harvester_vms():
    query_url = harvester_url + "/v1/harvester/kubevirt.io.virtualmachines/default"
    getResponse = get_request(query_url, harvester_token)
    return getResponse.json()['data']


def get_vms_on():
    # Statuses: Stopped, Starting, Running, Terminating
    query_url = harvester_url + "/v1/harvester/kubevirt.io.virtualmachines/default"
    getResponse = get_request(query_url, harvester_token)
    vms_on = []
    for vm in getResponse.json()['data']:
        if("Running" in vm['metadata']['fields'] or "Starting" in vm['metadata']['fields']):
            vms_on.append(vm['metadata']['fields'])

    # Convert to JSON
    json_response = {"vms_on": vms_on}
    json_response = json.dumps(json_response)
    return json_response


def get_num_vms_on():
    vms_on = get_vms_on()
    vms_on = json.loads(vms_on)
    return len(vms_on['vms_on'])


def get_metrics():
    query_url = harvester_url + "/v1/harvester/metrics.k8s.io.nodes"
    getResponse = get_request(query_url, harvester_token)
    return(getResponse.text)


def get_cpu_usage(start_time, end_time, step):
    nodemap = json.loads(get_node_names())
    query_url = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=1%20-%20avg(irate(%7B__name__%3D~%22node_cpu_seconds_total%7Cwindows_cpu_time_total%22%2Cmode%3D%22idle%22%7D%5B240s%5D))%20by%20(instance)&start={start_time}&end={end_time}&step={step}"
    getResponse = get_request(query_url, harvester_token)
    # Remove the port number from the instance name
    response = json.loads(getResponse.text)
    for i in range(len(response['data']['result'])):
        instance = response['data']['result'][i]['metric']['instance']
        instance = instance.split(":")[0]
        # If IP is in the nodemap then replace the IP with the hostname
        for host in nodemap['hosts']:
            if host['ip'] == instance:
                instance = host['hostname']
        response['data']['result'][i]['metric']['instance'] = instance
    return(json.dumps(response))


def get_network_usage(start_time, end_time, step):
    nodemap = json.loads(get_node_names())
    # Need to get 2 types of network usage:
    # 1. Packets sent
    # 2. Packets received

    response = {}

    # 1. Packets sent
    query_url = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=sum(rate(node_network_transmit_packets_total%7Bdevice!~%22lo%7Cveth.*%7Cdocker.*%7Cflannel.*%7Ccali.*%7Ccbr.*%22%7D%5B240s%5D))%20by%20(instance)%20OR%20sum(rate(windows_net_packets_sent_total%7Bnic!~%27.*isatap.*%7C.*VPN.*%7C.*Pseudo.*%7C.*tunneling.*%27%7D%5B240s%5D))%20by%20(instance)&start={start_time}&end={end_time}&step={step}"
    getResponseSent = get_request(query_url, harvester_token)

    # 2. Packets Received
    query_url = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=sum(rate(node_network_receive_packets_total%7Bdevice!~%22lo%7Cveth.*%7Cdocker.*%7Cflannel.*%7Ccali.*%7Ccbr.*%22%7D%5B240s%5D))%20by%20(instance)%20OR%20sum(rate(windows_net_packets_received_total_total%7Bnic!~%27.*isatap.*%7C.*VPN.*%7C.*Pseudo.*%7C.*tunneling.*%27%7D%5B240s%5D))%20by%20(instance)&start={start_time}&end={end_time}&step={step}"
    getResponseReceived = get_request(query_url, harvester_token)

    # Convert to JSON and add to response
    response = json.loads(getResponseSent.text)
    # Add (sent) to data.result.metric.instance
    for i in range(len(response['data']['result'])):
        # Remove the port number from the instance name
        instance = response['data']['result'][i]['metric']['instance']
        instance = instance.split(":")[0]
        # If IP is in the nodemap then replace the IP with the hostname
        for host in nodemap['hosts']:
            if host['ip'] == instance:
                instance = host['hostname']
        response['data']['result'][i]['metric']['instance'] = instance + \
            " (sent)"

    # Do the same for the received data
    response2 = json.loads(getResponseReceived.text)
    for i in range(len(response2['data']['result'])):
        instance = response2['data']['result'][i]['metric']['instance']
        instance = instance.split(":")[0]
        # If IP is in the nodemap then replace the IP with the hostname
        for host in nodemap['hosts']:
            if host['ip'] == instance:
                instance = host['hostname']
        response2['data']['result'][i]['metric']['instance'] = instance + \
            " (received)"

    # Add the received data to the response
    response['data']['result'] = response['data']['result'] + \
        response2['data']['result']

    # Print response
    return(json.dumps(response))


def get_memory_usage(start_time, end_time, step):
    nodemap = json.loads(get_node_names())
    query_url = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=1%20-%20sum(node_memory_MemAvailable_bytes%20OR%20windows_os_physical_memory_free_bytes)%20by%20(instance)%20%2F%20sum(node_memory_MemTotal_bytes%20OR%20windows_cs_physical_memory_bytes)%20by%20(instance)%20&start={start_time}&end={end_time}&step={step}"
    getResponse = get_request(query_url, harvester_token)
    # Remove the port number from the instance name
    response = json.loads(getResponse.text)
    for i in range(len(response['data']['result'])):
        instance = response['data']['result'][i]['metric']['instance']
        instance = instance.split(":")[0]
        # If IP is in the nodemap then replace the IP with the hostname
        for host in nodemap['hosts']:
            if host['ip'] == instance:
                instance = host['hostname']
        response['data']['result'][i]['metric']['instance'] = instance
    return(json.dumps(response))


def get_disk_usage(start_time, end_time, step):
    nodemap = json.loads(get_node_names())
    # Disk read
    query_url_read = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=sum(rate(node_disk_read_bytes_total%5B240s%5D)%20OR%20rate(windows_logical_disk_read_bytes_total%5B240s%5D))%20by%20(instance)&start={start_time}&end={end_time}&step={step}"
    getResponseRead = get_request(query_url_read, harvester_token)

    # Disk write
    query_url_write = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=sum(rate(node_disk_written_bytes_total%5B240s%5D)%20OR%20rate(windows_logical_disk_write_bytes_total%5B240s%5D))%20by%20(instance)&start={start_time}&end={end_time}&step={step}"
    getResponseWrite = get_request(query_url_write, harvester_token)

    # Convert to JSON and add to response
    response = json.loads(getResponseRead.text)
    # Add (sent) to data.result.metric.instance
    for i in range(len(response['data']['result'])):
        # Remove the port number from the instance name
        instance = response['data']['result'][i]['metric']['instance']
        instance = instance.split(":")[0]
        # If IP is in the nodemap then replace the IP with the hostname
        for host in nodemap['hosts']:
            if host['ip'] == instance:
                instance = host['hostname']
        response['data']['result'][i]['metric']['instance'] = instance + \
            " (read)"

    # Do the same for the write data
    response2 = json.loads(getResponseWrite.text)
    for i in range(len(response2['data']['result'])):
        instance = response2['data']['result'][i]['metric']['instance']
        instance = instance.split(":")[0]
        # If IP is in the nodemap then replace the IP with the hostname
        for host in nodemap['hosts']:
            if host['ip'] == instance:
                instance = host['hostname']
        response2['data']['result'][i]['metric']['instance'] = instance + \
            " (write)"

    # Add the received data to the response
    response['data']['result'] = response['data']['result'] + \
        response2['data']['result']

    # Print response
    return(json.dumps(response))

def power_on_vm(vm_name):
    query_url = harvester_url + \
        f"/v1/harvester/kubevirt.io.virtualmachines/default/{vm_name}?action=start"
    # POST request to stop the VM
    postResponse = post_request_params(query_url, harvester_token)
    jsonResponse = {}
    # If response is blank, it was successful
    if postResponse.text == "":
        jsonResponse['status'] = "success"
    else:
        jsonResponse['status'] = postResponse.text.split(": ")[1]
    return(json.dumps(jsonResponse))

def power_off_vm(vm_name):
    query_url = harvester_url + \
        f"/v1/harvester/kubevirt.io.virtualmachines/default/{vm_name}?action=stop"
    # POST request to stop the VM
    postResponse = post_request_params(query_url, harvester_token)
    jsonResponse = {}
    # If response is blank, it was successful
    if postResponse.text == "":
        jsonResponse['status'] = "success"
    else:
        jsonResponse['status'] = postResponse.text.split(": ")[1]
    return(json.dumps(jsonResponse))

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
