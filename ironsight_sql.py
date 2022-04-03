#!/usr/bin/env python3

import pymysql
import json
import sys
from pprint import pprint

# Query the database and return the response in JSON format
# If the query is setting data, then the response will be a blank list
def query(queryString, sql_server, sql_user, sql_pass, sql_db):
    # Connect to SQL server and store users in a list
    try:
        data = []
        keys = []
        conn = pymysql.connect(host=sql_server, user=sql_user, passwd=sql_pass, db=sql_db)
        cursor = conn.cursor()
        cursor.execute(queryString)
        # Get columns for key assignment
        try:
            for column in cursor.description:
                keys.append(column[0])
            for row in cursor:
                data.append(dict(zip(keys, row)))
        except:
            pass
        conn.commit()
        cursor.close()
        conn.close()
        return data
    except pymysql.Error as e:
        print("Error %d: %s" % (e.args[0], e.args[1]))
        sys.exit(1)

def query_no_return(queryString, sql_server, sql_user, sql_pass, sql_db):
    # Connect to SQL server and store users in a list
    try:
        conn = pymysql.connect(host=sql_server, user=sql_user, passwd=sql_pass, db=sql_db)
        cursor = conn.cursor()
        cursor.execute(queryString)
        conn.commit()
        cursor.close()
        conn.close()
    except pymysql.Error as e:
        print("Error %d: %s" % (e.args[0], e.args[1]))
        sys.exit(1)

# Print the JSON response in a table format
def pretty_response(queryResponse):
    print()
    if len(queryResponse) == 0:
        print("No results found.")
        return
    # Handle edge case with nested JSON
    try:
        keys = list(queryResponse[0].keys())
    except:
        queryResponse = json.loads(queryResponse)
        # Delete tags from response
        for entry in queryResponse:
            del entry['tags']
        keys = list(queryResponse[0].keys())
    values = []

    # Convert from JSON response to list of dictionaries
    for row in queryResponse:
        # Append each value in the row to the values list
        values.append(list(row.values()))
    
    # Obfuscate any passwords if in query response
    if "password" in keys:
        # Find the index of the password column
        passwordIndex = keys.index("password")
        for row in values:
            if str(row[passwordIndex]) != "":
                row[passwordIndex] = "********"
            else:
                row[passwordIndex] = "(No password)"

    # Don't display template_data, it's too long
    if "template_data" in keys:
        # Find the index of the template_data column
        templateIndex = keys.index("template_data")
        for row in values:
            row[templateIndex] = "(Too long)"

    # Print the response in a table format using dashes
    print("-" * (len(keys) * 20 + len(keys) - 1))
    print("|", end="")
    for key in keys:
        print("{:^20}".format(key), end="|")
    # Print dashed line
    print()
    print("-" * (len(keys) * 20 + len(keys) - 1))
    # Print each row in the table
    for value in values:
        print("|", end="")
        for item in value:
            if item is None:
                item = "None"
            print("{:^20}".format(item), end="|")
        print()
    print("-" * (len(keys) * 20 + len(keys) - 1))

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
            print("Config file not found. Please create config.json in current directory or parent directory.")
            exit(1)

if __name__ == '__main__':
    print("This is a module and should not be run directly.")
    unitTest = input("Run unit tests? (y/n): ")
    if unitTest.lower() == 'y':
        # Setup unit tests
        # Get config.json and set variables
        # Load in configuration file
        config_path = get_config()
        with open(config_path) as config_file:
            config = json.load(config_file)
            sql_server = config['sql_server']
            sql_user = config['sql_user']
            sql_pass = config['sql_pass']
            sql_db = config['sql_db']
        print("Which test to run? (1-4): ")
        print("\n1. List all users\n2. List all templates\n3. List all VMs\n4. List all labs\n5. List all tags")
        userChoice = str(input("Input: "))
        if userChoice == '1':
            queryString = "SELECT * FROM users"
        elif userChoice == '2':
            queryString = "SELECT * FROM vm_templates"
        elif userChoice == '3':
            queryString = "SELECT * FROM virtual_machines"
        elif userChoice == '4':
            queryString = "SELECT * FROM labs"
        elif userChoice == '5':
            queryString = "SELECT * FROM tags"
        else:
            print("Invalid choice")
            sys.exit(1)
            
        print()
        print("Query: " + queryString)
        print("User:" + sql_user)
        print("DB: " + sql_db)
        print("Server: " + sql_server)

        # Run query and assign response to a variable
        queryResponse = query(queryString, sql_server, sql_user, sql_pass, sql_db)
        
        # Pretty print the response
        pretty_response(queryResponse)
        print("\nQuery successful.\n")
        
        # Print the response in JSON format
        print("Raw JSON:")
        pprint(queryResponse)
    else:
        print("Exiting...")
        sys.exit(1)