#!/usr/bin/env python3
import json
import base64
import ironsight_harvester_api as ironsight
from pprint import pprint


def main_menu():
    print("1. Virtual Machine")
    print("2. Lab")
    print("3. User")
    print("4. Template")
    print("5. Course")
    print("6. Tag")
    print("7. Exit")
    print("")


def sub_menu():
    print("1. Create")
    print("2. Update")
    print("3. Delete")
    print("4. Back")
    print("")


def send_event(data):
    # Turn data into strings
    data_string = json.dumps(data)
    print("Formatted JSON data:")
    pprint(data)

    # Encode data
    encoded_data = base64.b64encode(data_string.encode('utf-8'))
    print("\nBase64 encoded data: ")
    print(encoded_data.decode('utf-8'))

    print("Are you sure you want to send this data to the API? (y/n)")
    choice = input("Enter your choice: ")
    if choice == "y":
        ironsight.handle_event(encoded_data.decode('utf-8'))
    else:
        print("Exiting...")


if __name__ == "__main__":

    print("Ironsight CLI")
    print("============")
    print("")

    data = {}

    # Main menu
    main_menu()
    choice = input("Enter your choice: ")

    # Virtual Machine
    if choice == "1":
        sub_menu()
        choice = input("Enter your choice: ")

        # Create
        if choice == "1":
            print("Create Virtual Machine")
            print("======================")
            print("")
            # Get data
            data["action"] = "create"
            data["type"] = "vm"
            data["data"] = {}
            data["data"]["vm_name"] = input("Enter VM name: ")
            data["data"]["user_name"] = input("Enter user name: ")
            data["data"]["template_name"] = input("Enter template name: ")
            data["data"]["lab_num"] = input("Enter lab number: ")
            data["data"]["course_id"] = input("Enter course ID: ")
            data["data"]["template_override"] = {}
            data["data"]["template_override"]["cpu_cores"] = input(
                "Enter CPU override: ")
            data["data"]["template_override"]["memory"] = input(
                "Enter Memory override: ")
            data["data"]["template_override"]["elastic_enrolled"] = bool(input(
                "Enter Elastic Enrolled override (0-1): ") == "1")
            data["data"]["template_override"]["redeploy"] = bool(input(
                "Enter Is Redeploy (0-1): ") == "1")
            data["data"]["template_override"]["running"] = bool(input(
                "Enter Is Running (0-1): ") == "1")
            send_event(data)
        if choice == "2":
            print("Update Virtual Machine")
        if choice == "3":
            print("Delete Virtual Machine")
            print("======================")
            print("")
            # Get data
            data["action"] = "delete"
            data["type"] = "vm"
            data["data"] = {}
            data["data"]["vm_name"] = input("Enter VM name: ")
            print("Are you sure you want to delete " + data["data"]["vm_name"] + "? (y/N)")
            choice = input("Enter your choice: ")
            if choice == "y":
                send_event(data)
            else:
                print("Exiting...")
    if choice == "2":
        sub_menu()
        choice = input("Enter your choice: ")
        if choice == "1":
            print("Create Lab")
            print("======================")
        if choice == "2":
            print("Update Lab")
        if choice == "3":
            print("Delete Lab")
            print("======================")
            data["action"] = "delete"
            data["type"] = "lab"
            data["data"] = {}
            data["data"]["lab_num"] = str(input("Enter lab number: "))
            print("Are you sure you want to delete " + data["data"]["lab_num"] + "? (y/N)")
            choice = input("Enter your choice: ")
            if choice == "y":
                send_event(data)
            else:
                print("Exiting...")
    if choice == "4":
        ironsight.list_templates()
