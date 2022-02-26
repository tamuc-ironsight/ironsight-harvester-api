import requests
import urllib3
from pprint import pprint

# Make post request with JSON data


def post_request(url, data, token):
    urllib3.disable_warnings()
    response = requests.post(url, verify=False, json=data, headers={
                             'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Bearer ' + token})
    return response


def createVM(vmName, claimName, imageName, userName, harvesterDomain, harvesterToken, elasticDomain, elasticToken):

    jsonData = {
        "apiVersion": "kubevirt.io/v1",
        "kind": "VirtualMachine",
        "metadata": {
            "namespace": "default",
            "annotations": {
                "harvesterhci.io/volumeClaimTemplates": "[{\"metadata\":{\"name\":\"" + claimName + "\",\"annotations\":{\"harvesterhci.io/imageId\":\"default/" + imageName + "\"}},\"spec\":{\"accessModes\":[\"ReadWriteMany\"],\"resources\":{\"requests\":{\"storage\":\"25Gi\"}},\"volumeMode\":\"Block\",\"storageClassName\":\"longhorn-" + imageName + "\"}}]",
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
                                "memory": "2Gi",
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
                                "userData" : 	"#cloud-config\npackage_update: true\npackages:\n  - wget\nhostname: "+ vmName + "\nusers:\n  - default\n  - name: " + userName + "\n    gecos: Student User\n    expiredate: '2032-09-01'\n    lock_passwd: false\n    passwd: $6$rounds=4096$Vd8W45YhfEELz1sq$HVp7eLIeJM.XOmN8o.RAwrg1UsqKpAXZBClx6uSX46j5Jwe4HN7cPdPYaKDLUVKYcAvjGTyRP3w26OrIo/.HD1\nruncmd:\n  - [ mkdir, /home/elastic ]\n  - [ wget, \"https://artifacts.elastic.co/downloads/beats/elastic-agent/elastic-agent-7.16.3-linux-x86_64.tar.gz\", -O, /home/elastic/agent.tar.gz ]\n  - [ tar, -xvf, /home/elastic/agent.tar.gz, -C, /home/elastic/ ]\n  - [ ./home/elastic/elastic-agent-7.16.3-linux-x86_64/elastic-agent, install, \"-f\",\"--url=" + elasticDomain + "\", \"--enrollment-token=" + elasticToken + "\", \"--insecure\" ]\n  - [\"touch\", \"/etc/cloud/cloud-init.disabled\"]"
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
    print("Harvester Domin: " + harvesterDomain.split('apis')[0])
    print("Elastic Domin: " + elasticDomain)
    print("Creating VM...")
    postResponse = post_request(harvesterDomain, jsonData, harvesterToken)
    print(postResponse.status_code)
    if postResponse.status_code == 201:
        print("VM Created Successfully")
    else:
        print("Error creating VM")
        pprint(postResponse.text.strip())