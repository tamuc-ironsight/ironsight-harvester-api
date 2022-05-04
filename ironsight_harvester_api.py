#!/usr/bin/env python3

from curses import meta
from importlib.metadata import metadata
import requests
import urllib3
from pprint import pprint
import ironsight_sql
import json
import random
import string
import sys
import base64
import subprocess

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
    # Sort by tag
    tagsJSON.sort(key=lambda x: x['tag'])
    return json.dumps(tagsJSON)


def get_courses():
    courses = ironsight_sql.query(
        "SELECT * FROM courses", sql_server, sql_user, sql_pass, sql_db)

    # Add labs to the response
    course_has_labs = ironsight_sql.query(
        "SELECT * FROM courses_has_labs", sql_server, sql_user, sql_pass, sql_db)
    for course in courses:
        course['labs'] = []
    for lab in course_has_labs:
        for course in courses:
            if lab['course_id'] == course['course_id']:
                course['labs'].append(lab['lab_num'])

    # Add users to the response
    course_has_users = ironsight_sql.query(
        "SELECT * FROM courses_has_users", sql_server, sql_user, sql_pass, sql_db)
    for course in courses:
        course['users'] = []
    for user in course_has_users:
        for course in courses:
            if user['course_id'] == course['course_id']:
                course['users'].append(user['user_name'])

    # Add tags to the response
    courses_has_tags = ironsight_sql.query(
        "SELECT * FROM courses_has_tags", sql_server, sql_user, sql_pass, sql_db)
    for course in courses:
        course['tags'] = []
    for tag in courses_has_tags:
        for course in courses:
            if tag['course_id'] == course['course_id']:
                course['tags'].append(tag['tag'])

    # Add the vms to the response
    courses_has_vms = ironsight_sql.query(
        "SELECT * FROM courses_has_virtual_machines", sql_server, sql_user, sql_pass, sql_db)
    for course in courses:
        course['virtual_machines'] = []
    for vm in courses_has_vms:
        for course in courses:
            if vm['course_id'] == course['course_id']:
                course['virtual_machines'].append(vm['vm_name'])

    # Sort by course
    courses.sort(key=lambda x: x['course_id'])
    return json.dumps(courses)

    # Sort by course_id
    courses.sort(key=lambda x: x['course_id'])
    return json.dumps(courses)


def get_permissions():
    permissionsJSON = ironsight_sql.query(
        "SELECT * FROM permissions", sql_server, sql_user, sql_pass, sql_db)
    return json.dumps(permissionsJSON)


def get_roles():
    rolesJSON = ironsight_sql.query(
        "SELECT * FROM roles", sql_server, sql_user, sql_pass, sql_db)

    # Add permissions to the response
    permissions = ironsight_sql.query(
        "SELECT * FROM roles_has_permissions", sql_server, sql_user, sql_pass, sql_db)

    # Add permissions to the response
    for role in rolesJSON:
        role['permissions'] = []
        for permission in permissions:
            if role['role'] == permission['role']:
                role['permissions'].append(permission['permission_name'])

    return json.dumps(rolesJSON)


def get_vms():
    vmsJSON = ironsight_sql.query(
        "SELECT * FROM virtual_machines", sql_server, sql_user, sql_pass, sql_db)

    # Populate the users field
    for vm in vmsJSON:
        vm['users'] = []

    # Handle the many-to-many relationship between virtual machines and users ("virtual_machine_has_users")
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
    virtual_machine_has_labs = ironsight_sql.query(
        "SELECT * FROM virtual_machine_has_labs", sql_server, sql_user, sql_pass, sql_db)
    for vm_lab in virtual_machine_has_labs:
        for vm in vmsJSON:
            if vm_lab['vm_name'] == vm['vm_name']:
                vm['labs'].append(vm_lab['lab_num'])

    # Handle the many-to-many relationship between virtual machines and tags ("virtual_machine_has_tags")
    virtual_machine_has_tags = ironsight_sql.query(
        "SELECT * FROM virtual_machines_has_tags", sql_server, sql_user, sql_pass, sql_db)

    # Add tags to vms
    for vm in vmsJSON:
        vm['tags'] = []
    for vm_tag in virtual_machine_has_tags:
        for vm in vmsJSON:
            if vm_tag['vm_name'] == vm['vm_name']:
                vm['tags'].append(vm_tag['tag'])

    return json.dumps(vmsJSON)


def get_templates():
    templatesJSON = ironsight_sql.query(
        "SELECT * FROM vm_templates", sql_server, sql_user, sql_pass, sql_db)

    # Populate labs with empty list
    for template in templatesJSON:
        template['labs'] = []

    # Handle the many-to-many relationship between templates and labs ("labs_has_vm_templates")
    labs_has_vm_templates = ironsight_sql.query(
        "SELECT * FROM labs_has_vm_templates", sql_server, sql_user, sql_pass, sql_db)
    for lab_template in labs_has_vm_templates:
        for template in templatesJSON:
            if lab_template['template_name'] == template['template_name']:
                template['labs'].append(lab_template['lab_num'])

    # Handle the many-to-many relationship between templates and tags ("vm_templates_has_tags")
    vm_templates_has_tags = ironsight_sql.query(
        "SELECT * FROM vm_templates_has_tags", sql_server, sql_user, sql_pass, sql_db)

    # Add tags to templates
    for template in templatesJSON:
        template['tags'] = []
    for template_tag in vm_templates_has_tags:
        for template in templatesJSON:
            if template_tag['template_name'] == template['template_name']:
                template['tags'].append(template_tag['tag'])

    return json.dumps(templatesJSON)


def get_users():
    usersJSON = ironsight_sql.query(
        "SELECT * FROM users", sql_server, sql_user, sql_pass, sql_db)

    # Populate users with the needed empty lists
    for user in usersJSON:
        user['virtual_machines'] = []
        user['roles'] = []
        user['tags'] = []
        user['courses'] = []

    # Handle the many-to-many relationship between virtual machines and users ("virtual_machine_has_users")
    virtual_machine_has_users = ironsight_sql.query(
        "SELECT * FROM virtual_machine_has_users", sql_server, sql_user, sql_pass, sql_db)
    for vm_user in virtual_machine_has_users:
        for user in usersJSON:
            if vm_user['user_name'] == user['user_name']:
                user['virtual_machines'].append(vm_user['vm_name'])

    # Get the roles for each user
    user_has_roles = ironsight_sql.query(
        "SELECT * FROM users_has_roles", sql_server, sql_user, sql_pass, sql_db)
    for user_role in user_has_roles:
        for user in usersJSON:
            if user_role['user_name'] == user['user_name']:
                user['roles'].append(user_role['role'])

    # Get the courses for each user
    courses = json.loads(get_courses())
    courses_has_users = ironsight_sql.query(
        "SELECT * FROM courses_has_users", sql_server, sql_user, sql_pass, sql_db)

    # Add courses to users using course_id
    for course in courses:
        for course_user in courses_has_users:
            for user in usersJSON:
                if course_user['user_name'] == user['user_name'] and course['course_id'] == course_user['course_id']:
                    user['courses'].append(course)

    # Get the tags for each user
    user_has_tags = ironsight_sql.query(
        "SELECT * FROM users_has_tags", sql_server, sql_user, sql_pass, sql_db)
    tags = ironsight_sql.query(
        "SELECT * FROM tags", sql_server, sql_user, sql_pass, sql_db)

    for user_tag in user_has_tags:
        for user in usersJSON:
            if user_tag['user_name'] == user['user_name']:
                for tag in tags:
                    if tag['tag'] == user_tag['tag']:
                        user['tags'].append(tag)

    return json.dumps(usersJSON)


def get_labs():
    labsJSON = ironsight_sql.query(
        "SELECT * FROM labs", sql_server, sql_user, sql_pass, sql_db)
    # Populate labs with empty lists
    # Fix datetime.datetime object to make it JSON serializable
    for lab in labsJSON:
        lab['date_start'] = str(lab['date_start'])
        lab['date_end'] = str(lab['date_end'])
        lab['virtual_machines'] = []
        lab['templates'] = []
        lab['course_id'] = ""
        lab['tags'] = []
        lab['users'] = []

    # Handle the many-to-many relationship between virtual machines and labs ("virtual_machine_has_labs")
    virtual_machine_has_labs = ironsight_sql.query(
        "SELECT * FROM virtual_machine_has_labs", sql_server, sql_user, sql_pass, sql_db)
    for vm_lab in virtual_machine_has_labs:
        for lab in labsJSON:
            if vm_lab['lab_num'] == lab['lab_num']:
                lab['virtual_machines'].append(vm_lab['vm_name'])

    # Handle the many-to-many relationship between virtual machines and templates ("labs_has_vm_templates")
    labs_has_vm_templates = ironsight_sql.query(
        "SELECT * FROM labs_has_vm_templates", sql_server, sql_user, sql_pass, sql_db)
    for lab_template in labs_has_vm_templates:
        for lab in labsJSON:
            if lab_template['lab_num'] == lab['lab_num']:
                lab['templates'].append(lab_template['template_name'])

    # Get the course for each lab
    courses_has_labs = ironsight_sql.query(
        "SELECT * FROM courses_has_labs", sql_server, sql_user, sql_pass, sql_db)
    for course_lab in courses_has_labs:
        for lab in labsJSON:
            if course_lab['lab_num'] == lab['lab_num']:
                lab['course_id'] = (course_lab['course_id'])

    # Add the tags for each lab
    labs_has_tags = ironsight_sql.query(
        "SELECT * FROM labs_has_tags", sql_server, sql_user, sql_pass, sql_db)
    for lab_tag in labs_has_tags:
        for lab in labsJSON:
            if lab_tag['lab_num'] == lab['lab_num']:
                lab['tags'].append(lab_tag['tag'])

    # Add the users to each lab
    for course in json.loads(get_courses()):
        for lab in labsJSON:
            if course['course_id'] == lab['course_id']:
                for user in course['users']:
                    lab['users'].append(user)

    return json.dumps(labsJSON)


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

def delete_request(url, token):
    urllib3.disable_warnings()
    response = requests.delete(url, verify=False, headers={
                            'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Bearer ' + token})
    return response


def create_user(user_data):
    # Check if user already exists
    users = get_users()
    users = json.loads(users)
    for user in users:
        if user['user_name'] == user_data['user_name']:
            print("Error: User already exists")
            return

    # Get the courses, tags, and roles for the user
    if 'courses' in user_data:
        courses = user_data['courses']
    else:
        courses = []
    if 'tags' in user_data:
        tags = user_data['tags']
    else:
        tags = []
    if 'roles' in user_data:
        roles = user_data['roles']
    else:
        roles = []
    if 'password' in user_data:
        user_password = user_data['password']
    else:
        user_password = "1"
    if 'profile_pic_data' in user_data:
        if user_data['profile_pic_data'] != "":
            profile_pic_data = user_data['profile_pic_data']
        else:
            profile_pic_data = "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460__480.png"
    else:
        profile_pic_data = "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460__480.png"

    # Run mkpasswd --method=SHA-512 --rounds=4096 to generate the password hash
    user_password = subprocess.check_output(
        "mkpasswd --method=SHA-512 --rounds=4096 " + user_password, shell=True)
    user_password = user_password.decode("utf-8")
    user_password = user_password.rstrip()

    # Create user
    query = "INSERT INTO users (`user_name`, `first_name`, `last_name`, `password`, `profile_pic_data`) VALUES ('" + \
        user_data['user_name'] + "', '" + user_data['first_name'] + "', '" + user_data['last_name'] + \
            "', '" + user_password + "', '" + \
        profile_pic_data + "')"
    ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    # Insert the user into the many-to-many relationship between courses and users ("courses_has_users")
    for course in courses:
        query = "INSERT INTO courses_has_users (`course_id`, `user_name`) VALUES ('" + \
            course + "', '" + user_data['user_name'] + "')"
        ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    # Insert the user into the many-to-many relationship between tags and users ("users_has_tags")
    for tag in tags:
        query = "INSERT INTO users_has_tags (`user_name`, `tag`) VALUES ('" + \
            user_data['user_name'] + "', '" + tag + "')"
        ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    # Insert the user into the many-to-many relationship between roles and users ("users_has_roles")
    for role in roles:
        query = "INSERT INTO users_has_roles (`user_name`, `role`) VALUES ('" + \
            user_data['user_name'] + "', '" + role + "')"
        ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    print("User created successfully")
    return json.dumps(user_data)


def delete_user(user_data):
    # Check if user exists
    users = get_users()
    users = json.loads(users)
    for user in users:
        if user['user_name'] == user_data['user_name']:
            # Delete user from many-to-many relationship between courses and users ("courses_has_users")
            query = "DELETE FROM courses_has_users WHERE `user_name` = '" + \
                user_data['user_name'] + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

            # Delete user from many-to-many relationship between tags and users ("users_has_tags")
            query = "DELETE FROM users_has_tags WHERE `user_name` = '" + \
                user_data['user_name'] + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

            # Delete user from many-to-many relationship between roles and users ("users_has_roles")
            query = "DELETE FROM users_has_roles WHERE `user_name` = '" + \
                user_data['user_name'] + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

            # Delete user
            query = "DELETE FROM users WHERE `user_name` = '" + \
                user_data['user_name'] + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    print("Successfully deleted user: " + user_data['user_name'])


def create_lab(lab_data):
    # Check if lab already exists
    labs = get_labs()
    labs = json.loads(labs)
    for lab in labs:
        if lab['lab_name'] == lab_data['lab_name']:
            print("Error: Lab already exists")
            return

    # Get a lab_num that is not in the database
    lab_num = -1
    for lab in labs:
        if lab['lab_num'] > lab_num:
            lab_num = lab['lab_num']
    lab_num += 1

    # Add the lab to the database
    query = "INSERT INTO labs (`lab_num`, `lab_name`, `lab_description`, `date_start`, `date_end`) VALUES ('" + \
        str(lab_num) + "', '" + lab_data['lab_name'] + "', '" + lab_data['lab_description'] + "', '" + \
        lab_data['date_start'] + "', '" + lab_data['date_end'] + "')"
    ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    # Add the lab to the many-to-many relationship between courses and labs ("courses_has_labs")
    query = "INSERT INTO courses_has_labs (`course_id`, `lab_num`) VALUES ('" + \
        lab_data['course'] + "', '" + str(lab_num) + "')"
    ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    # Add the lab to the many-to-many relationship between tags and labs ("labs_has_tags")
    for tag in lab_data['tags']:
        query = "INSERT INTO labs_has_tags (`lab_num`, `tag`) VALUES ('" + \
            str(lab_num) + "', '" + tag + "')"
        ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    # Add the lab to the many-to-many relationship between vm_templates and labs ("labs_has_vm_templates")
    for vm_template in lab_data['vm_templates']:
        query = "INSERT INTO labs_has_vm_templates (`lab_num`, `template_name`) VALUES ('" + \
            str(lab_num) + "', '" + vm_template + "')"
        ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    print("Lab created successfully")


def delete_lab(lab_data):
    # Check if lab exists
    labs = get_labs()
    labs = json.loads(labs)
    for lab in labs:
        lab['lab_num'] = str(lab['lab_num'])
        print("Checking lab: " + lab['lab_name'] + ", " + lab['lab_num'])
        if lab['lab_num'] == lab_data['lab_num']:
            print("Lab exists")
            # Delete lab from many-to-many relationship between courses and labs ("courses_has_labs")
            query = "DELETE FROM courses_has_labs WHERE `lab_num` = '" + \
                str(lab['lab_num']) + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

            # Delete lab from many-to-many relationship between tags and labs ("labs_has_tags")
            query = "DELETE FROM labs_has_tags WHERE `lab_num` = '" + \
                str(lab['lab_num']) + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

            # Delete lab from many-to-many relationship between vm_templates and labs ("labs_has_vm_templates")
            query = "DELETE FROM labs_has_vm_templates WHERE `lab_num` = '" + \
                str(lab['lab_num']) + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

            # Delete lab from many-to-many relationship between virtual machines and labs ("virtual_machine_has_labs")
            query = "DELETE FROM virtual_machine_has_labs WHERE `lab_num` = '" + \
                str(lab['lab_num']) + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

            # Delete lab
            query = "DELETE FROM labs WHERE `lab_num` = '" + \
                str(lab['lab_num']) + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    print("Successfully deleted lab: " + lab_data['lab_num'])


def create_course(course_data):
    # Check if course already exists
    courses = get_courses()
    courses = json.loads(courses)
    for course in courses:
        if course['course_id'] == course_data['course_id']:
            print("Error: Course already exists")
            return

    # Add the course to the database
    query = "INSERT INTO courses (`course_id`, `course_name`, `course_thumbnail`) VALUES ('" + \
        course_data['course_id'] + "', '" + course_data['course_name'] + "', '" + \
        course_data['thumbnail'] + "')"
    ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    # Add the course to the many-to-many relationship between tags and courses ("courses_has_tags")
    for tag in course_data['tags']:
        query = "INSERT INTO courses_has_tags (`course_id`, `tag`) VALUES ('" + \
            course_data['course_id'] + "', '" + tag + "')"
        ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    print("Course created successfully")


def delete_course(course_data):
    # Check if course exists
    courses = get_courses()
    courses = json.loads(courses)
    for course in courses:
        if course['course_id'] == course_data['course_id']:
            # Delete course from many-to-many relationship between tags and courses ("courses_has_tags")
            query = "DELETE FROM courses_has_tags WHERE `course_id` = '" + \
                course_data['course_id'] + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

            # Delete course from many-to-many relationship between labs and courses ("courses_has_labs")
            query = "DELETE FROM courses_has_labs WHERE `course_id` = '" + \
                course_data['course_id'] + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

            # Delete course from many-to-many relationship between users and courses ("courses_has_users")
            query = "DELETE FROM courses_has_users WHERE `course_id` = '" + \
                course_data['course_id'] + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

            # Delete course
            query = "DELETE FROM courses WHERE `course_id` = '" + \
                course_data['course_id'] + "'"
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

    print("Successfully deleted course: " + course_data['course_id'])


def create_vm(vm_data):

    # Check if vm already exists
    vms = get_vms()
    vms = json.loads(vms)
    for vm in vms:
        if vm['vm_name'] == vm_data['vm_name']:
            print("Error: VM already exists")
            return

    # Get a few variables from the user
    vm_name = vm_data['vm_name']
    user_name = vm_data['user_name']
    template_choice = vm_data['template_name']
    if 'course_id' in vm_data:
        course_id = vm_data['course_id']
    if 'lab_num' in vm_data:
        lab_num = vm_data['lab_num']
    if 'template_override' in vm_data:
        template_override = vm_data['template_override']
        if 'elastic_enrolled' in template_override:
            elastic_enrolled = bool(template_override['elastic_enrolled'])

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
    if user_name != "":
        vm_name = vm_name + "-" + user_name_short
    random_letters = "".join(random.choice(
        string.ascii_lowercase) for i in range(5))
    claim_name = vm_name + "-claim" + random_letters

    elastic_enrolled = bool(templateData['elastic_enrolled'])
    if 'template_override' in vm_data:
        print("\nOverriding template settings")
        if 'elastic_enrolled' in vm_data['template_override'] and vm_data['template_override']['elastic_enrolled'] != "":
            print("Overriding elastic enrolled")
            elastic_enrolled = bool(vm_data['template_override']['elastic_enrolled'])
            print("Elastic enrolled: " + str(elastic_enrolled))
        if 'redeploy' in vm_data['template_override'] and vm_data['template_override']['redeploy'] != "":
            redeploy = bool(vm_data['template_override']['redeploy'])
            print("Redeploy: " + str(redeploy))
        else:
            redeploy = False
        if 'running' in vm_data['template_override'] and vm_data['template_override']['running'] != "":
            running = bool(vm_data['template_override']['running'])
            print("Running: " + str(running))
        else:
            running = True

    # Determine if VM should be enrolled in Elasticsearch or not
    if elastic_enrolled:
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

    # Data coming from frontend with customization looks like this:
    # {
    # "cpu_cores": "2",
    # "memory": "4",
    # "cloud_init_data": {
    #     "packages": [
    #         "neofetch",
    #         "python3-pip"
    #     ]
    # },
    # "running": "true"
    # }

    default_specs = {
        "cpu_cores": "2",
        "memory": "4",
        "cloud_init_data": cloud_init_data
    }

    # Get user's specs from template['template_data]
    # If user has not specified any specs, use default specs
    user_specs = json.loads(templateData['template_data'])

    if user_specs == {'': ''}:
        specs = default_specs
    else:
        # Merge user's specs with default specs and overwrite default specs with user's specs
        specs = {**default_specs, **user_specs}

    if 'template_override' in vm_data:
        if 'cpu_cores' in vm_data['template_override'] and vm_data['template_override']['cpu_cores'] != "":
            specs['cpu_cores'] = vm_data['template_override']['cpu_cores']
        if 'memory' in vm_data['template_override'] and vm_data['template_override']['memory'] != "":
            specs['memory'] = vm_data['template_override']['memory']

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
            "running": bool(running),
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
                            "cores": int(specs['cpu_cores']),
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
                                "memory": str(specs['memory']) + str("Gi"),
                                "cpu": int(specs['cpu_cores'])
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

    if not redeploy:
        # Add VM to the MySQL database
        print("Adding VM to the MySQL database...")
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

        # query = str("INSERT INTO virtual_machines (vm_name, harvester_vm_name, port_number, template_name) VALUES ('" + vm_name + "', '" + vm_name + "-harvester-name', '" + str(port) + "', '" + template_choice + "')")
        query = str("INSERT INTO virtual_machines (vm_name, harvester_vm_name, port_number, template_name) VALUES ('" +
                    vm_name + "', '" + vm_name + "', '" + str(port) + "', '" + template_choice + "')")
        print(query)
        ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

        # The SQL database also has many-to-many relationships between users and virtual machines
        # The keys are vm_name and user_name. The table is called virtual_machine_has_users
        # The query is:
        # INSERT INTO virtual_machine_has_users (vm_name, user_name) VALUES ('android-tharrison', 'tyler_harrison');
        if user_name != "":
            query = str("INSERT INTO virtual_machine_has_users (vm_name, user_name) VALUES ('" +
                        vm_name + "', '" + user_name + "')")
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)
        else:
            print("No user specified, skipping user insertion")

        # Many-to-many relationship between virtual machines and labs
        if lab_num != "":
            query = str("INSERT INTO virtual_machine_has_labs (vm_name, lab_num) VALUES ('" +
                        vm_name + "', '" + str(lab_num) + "')")
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)
        else:
            print("No lab specified, skipping lab insertion")

        # Many-to-many relationship between virtual machines and courses
        if course_id != "":
            query = str("INSERT INTO courses_has_virtual_machines (course_id, vm_name) VALUES ('" +
                        course_id + "', '" + vm_name + "')")
            ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)
        else:
            print("No course specified, skipping course insertion")

        print("VM Added to the MySQL database with port: " + str(port))
    else:
        print("Skipping SQL enrollment...")

    # Create VM with Harvester API
    print("Creating Harvester VM...")
    create_vm_url = harvester_url + \
        "/apis/kubevirt.io/v1/namespaces/default/virtualmachines/"
    postResponse = post_request(create_vm_url, jsonData, harvester_token)
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


def delete_vm(data):
    # Get VM name
    vm_name = data['vm_name']

    print("Deleting VM: " + vm_name +"...")

    # Remove VM from SQL database
    print("Removing VM from the MySQL database...")
    # Need to delete from these tables first: virtual_machine_has_users, virtual_machine_has_labs, courses_has_virtual_machines
    # Then delete from virtual_machines
    try:
        query = str("DELETE FROM virtual_machine_has_users WHERE vm_name = '" + vm_name + "'")
        ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)
        query = str("DELETE FROM virtual_machine_has_labs WHERE vm_name = '" + vm_name + "'")
        ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)
        query = str("DELETE FROM courses_has_virtual_machines WHERE vm_name = '" + vm_name + "'")
        ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)
        query = str("DELETE FROM virtual_machines WHERE vm_name = '" + vm_name + "'")
        ironsight_sql.query(query, sql_server, sql_user, sql_pass, sql_db)

        print("VM Removed from the MySQL database")
    except:
        print("Error removing VM from the MySQL database")

    # Delete VM with Harvester API
    print("Deleting Harvester VM...")
    try:
        delete_vm_url = harvester_url + \
            "/apis/kubevirt.io/v1/namespaces/default/virtualmachines/" + vm_name + "?removedDisks=disk-0&?removedDisks=disk-0&propagationPolicy=Foreground"
        deleteResponse = delete_request(delete_vm_url, harvester_token)
        print(deleteResponse.status_code)
        if deleteResponse.status_code == 200:
            print("VM Deleted Successfully")
        else:
            print("Error deleting VM")
            pprint(deleteResponse.text.strip())
            sys.exit(1)
    except:
        print("Error deleting VM")
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
    return json.dumps(getResponse.json()['data'])


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


def get_vm_cpu_usage(start_time, end_time, step):
    query_url = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=topk(10%2C%20(avg(rate(kubevirt_vmi_vcpu_seconds%5B5m%5D))%20by%20(domain%2C%20name)))%20&start={start_time}&end={end_time}&step={step}"
    getResponse = get_request(query_url, harvester_token)
    response = json.loads(getResponse.text)
    return(json.dumps(response))


def get_vm_memory_usage(start_time, end_time, step):
    query_url = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=topk(10%2C%20((kubevirt_vmi_memory_available_bytes%20-%20kubevirt_vmi_memory_unused_bytes)%20%2F%20kubevirt_vmi_memory_available_bytes))&start={start_time}&end={end_time}&step={step}"
    getResponse = get_request(query_url, harvester_token)
    response = json.loads(getResponse.text)
    return(json.dumps(response))


def get_vm_storage_read_usage(start_time, end_time, step):
    query_url = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=topk(10%2C%20(irate(kubevirt_vmi_storage_read_traffic_bytes_total%5B5m%5D)))%20&start={start_time}&end={end_time}&step={step}"
    getResponse = get_request(query_url, harvester_token)
    response = json.loads(getResponse.text)
    return(json.dumps(response))


def get_vm_storage_write_usage(start_time, end_time, step):
    query_url = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=topk(10%2C%20(irate(kubevirt_vmi_storage_write_traffic_bytes_total%5B5m%5D)))%20&start={start_time}&end={end_time}&step={step}"
    getResponse = get_request(query_url, harvester_token)
    response = json.loads(getResponse.text)
    return(json.dumps(response))


def get_vm_network_read_usage(start_time, end_time, step):
    query_url = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=topk(10%2C%20(irate(kubevirt_vmi_network_receive_bytes_total%5B5m%5D)*8))&start={start_time}&end={end_time}&step={step}"
    getResponse = get_request(query_url, harvester_token)
    response = json.loads(getResponse.text)
    return(json.dumps(response))


def get_vm_network_write_usage(start_time, end_time, step):
    query_url = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=topk(10%2C%20(irate(kubevirt_vmi_network_transmit_bytes_total%5B5m%5D)*8))&start={start_time}&end={end_time}&step={step}"
    getResponse = get_request(query_url, harvester_token)
    response = json.loads(getResponse.text)
    return(json.dumps(response))


def get_vm_network_packets_received(start_time, end_time, step):
    query_url = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=topk(10%2C%20(delta(kubevirt_vmi_network_receive_packets_total%5B5m%5D)))&start={start_time}&end={end_time}&step={step}"
    getResponse = get_request(query_url, harvester_token)
    response = json.loads(getResponse.text)
    return(json.dumps(response))


def get_vm_network_packets_sent(start_time, end_time, step):
    query_url = harvester_url + \
        f"/api/v1/namespaces/cattle-monitoring-system/services/http:rancher-monitoring-grafana:80/proxy/api/datasources/proxy/1/api/v1/query_range?query=topk(10%2C%20(delta(kubevirt_vmi_network_transmit_packets_total%5B5m%5D)))&start={start_time}&end={end_time}&step={step}"
    getResponse = get_request(query_url, harvester_token)
    response = json.loads(getResponse.text)
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


def power_toggle_vm(vm_name):
    # If the VM is running, stop it
    vms_list = json.loads(get_harvester_vms())
    for vm in vms_list:
        if vm['metadata']['name'] == vm_name:
            if vm['status']['printableStatus'] == "Running":
                power_off_vm(vm_name)
                return(json.dumps({"status": "success"}))
            else:
                power_on_vm(vm_name)
                return(json.dumps({"status": "success"}))
    return(json.dumps({"status": "error"}))


def handle_event(encoded_data):
    data = {}
    try:
        data = json.loads(base64.b64decode(encoded_data))
    except:
        print("Error: Could not decode base64 data")
        return

    if data['action'] == "create":
        if data['type'] == "user":
            create_user(data['data'])
        if data['type'] == "lab":
            create_lab(data['data'])
        if data['type'] == "course":
            create_course(data['data'])
        elif data['type'] == "vm":
            create_vm(data['data'])
    # TODO: Add update event handling
    # elif data['action'] == "update":
    #     if data['type'] == "user":
    #         update_user(data['data'])
    #     elif data['type'] == "vm":
    #         update_vm(data['data'])
    elif data['action'] == "delete":
        if data['type'] == "user":
            delete_user(data['data'])
        if data['type'] == "lab":
            delete_lab(data['data'])
        if data['type'] == "course":
            delete_course(data['data'])
        elif data['type'] == "vm":
            delete_vm(data['data'])


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
