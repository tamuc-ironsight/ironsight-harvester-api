import requests
import random
import string
import time
from pprint import pprint

# Make post request with JSON data


def post_request(url, data, token):
    response = requests.post(url, json=data, headers={
                             'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Bearer ' + token})
    return response


def createVM(vmName, claimName, studentName, domain, token):

    jsonData = {
        "apiVersion": "kubevirt.io/v1",
        "kind": "VirtualMachine",
        "metadata": {
            "namespace": "default",
            "annotations": {
                "harvesterhci.io/volumeClaimTemplates": "[{\"metadata\":{\"name\":\"" + claimName + "\",\"annotations\":{\"harvesterhci.io/imageId\":\"default/image-vk9x6\"}},\"spec\":{\"accessModes\":[\"ReadWriteMany\"],\"resources\":{\"requests\":{\"storage\":\"25Gi\"}},\"volumeMode\":\"Block\",\"storageClassName\":\"longhorn-image-vk9x6\"}}]",
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
            "running": True,
            "template": {
                "metadata": {
                    "annotations": {
                        "harvesterhci.io/sshNames": "[]"
                    },
                    "labels": {
                        "harvesterhci.io/vmName": "test-api"
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
                    "hostname": "test-api",
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
                                # "userData": "#cloud-config\npackage_update: true\npackages:\n  - wget\nhostname: kali-lab1-tharrison\nruncmd:\n  - [ mkdir, /home/kali/elastic-setup ]\n  - [ wget, \"https://artifacts.elastic.co/downloads/beats/elastic-agent/elastic-agent-7.16.3-linux-x86_64.tar.gz\", -O, /home/kali/elastic-setup/agent.tar.gz ]\n  - [ tar, -xvf, /home/kali/elastic-setup/agent.tar.gz, -C, /home/kali/elastic-setup/ ]\n  - [ ./home/kali/elastic-setup/elastic-agent-7.16.3-linux-x86_64/elastic-agent, install, \"-f\",\"--url=http://ssh.tylerharrison.dev:8220\", \"--enrollment-token=a1VJbXBYNEJZOEUtRnJyRlhvc0Q6U3VFZGRPcldUcW0tRzMyX2s3UmtTUQ==\", \"--insecure\" ]"
                                # "userData" : "#cloud-config\npackage_update: true\nusers:\n  - default\n  - name: tyler\n    gecos: Student User\n    expiredate: '2032-09-01'\n    lock_passwd: false\n    passwd: $6$rounds=4096$Vd8W45YhfEELz1sq$HVp7eLIeJM.XOmN8o.RAwrg1UsqKpAXZBClx6uSX46j5Jwe4HN7cPdPYaKDLUVKYcAvjGTyRP3w26OrIo/.HD1"
                                "userData" : 	"#cloud-config\npackage_update: true\npackages:\n  - wget\nhostname: "+ vmName + "\nruncmd:\n  - [ mkdir, /home/kali/elastic-setup ]\n  - [ wget, \"https://artifacts.elastic.co/downloads/beats/elastic-agent/elastic-agent-7.16.3-linux-x86_64.tar.gz\", -O, /home/kali/elastic-setup/agent.tar.gz ]\n  - [ tar, -xvf, /home/kali/elastic-setup/agent.tar.gz, -C, /home/kali/elastic-setup/ ]\n  - [ ./home/kali/elastic-setup/elastic-agent-7.16.3-linux-x86_64/elastic-agent, install, \"-f\",\"--url=http://ssh.tylerharrison.dev:8220\", \"--enrollment-token=a1VJbXBYNEJZOEUtRnJyRlhvc0Q6U3VFZGRPcldUcW0tRzMyX2s3UmtTUQ==\", \"--insecure\" ]\nusers:\n  - default\n  - name: " + studentName + "\n    gecos: Student User\n    expiredate: '2032-09-01'\n    lock_passwd: false\n    passwd: $6$rounds=4096$Vd8W45YhfEELz1sq$HVp7eLIeJM.XOmN8o.RAwrg1UsqKpAXZBClx6uSX46j5Jwe4HN7cPdPYaKDLUVKYcAvjGTyRP3w26OrIo/.HD1"
                            }
                        }
                    ]
                }
            }
        }
    }

    postResponse = post_request(domain, jsonData, token)
    # pprint(postResponse.text.strip())
    print(postResponse.status_code)


students = ["Tyler", "Truman", "Sudip", "Augustine"]
for student in students:
    student = student.lower()
    vmName = "kali-lab1-" + str(student)
    randomLetters = "".join(random.choice(
        string.ascii_lowercase) for i in range(5))
    claimName = vmName + "-claim" + randomLetters

    token = "token-llcfk:dxqlvcxglvg744z2hlpvwgjfqkcxlsczprkbtg4vrxqckgdbq7z7cg"
    domain = "https://vm.tylerharrison.dev/apis/kubevirt.io/v1/namespaces/default/virtualmachines"

    print("Creating VM: " + vmName)
    createVM(vmName, claimName, student, domain, token)
    # Sleep for 10 seconds
    time.sleep(10)
