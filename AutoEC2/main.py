"""--------------------------------------------------------------------------------------------------------------------
Copyright 2021 Market Maker Lite, LLC (MML)
Licensed under the Apache License, Version 2.0
THIS CODE IS PROVIDED AS IS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND
This file is part of the MML Open Source Library (www.github.com/MarketMakerLite)
--------------------------------------------------------------------------------------------------------------------"""
import boto3
from halo import Halo
import time
import sys
import os
from datetime import datetime
import secrets
import urllib.request

######################################################################################################################
#                                                       Functions                                                    #
######################################################################################################################
def start_spinner(busy_text='Loading', t=1):
    spin = Halo(text=f'{busy_text}', color='cyan', spinner='dots')
    spin.start()
    time.sleep(t)
    return spin


def stop_spinner(spin, done_text='Complete'):
    spin.stop_and_persist(symbol='✔'.encode('utf-8'), text=f'{done_text}')
    return None


def delay_print_fast(s):
    for c in s:
        sys.stdout.write(c)
        sys.stdout.flush()
    return None


def delay_print_slow(s):
    for c in s:
        sys.stdout.write(c)
        sys.stdout.flush()
        time.sleep(0.2)
    return None


# def get_running_instances():
#     ec2_client = boto3.client("ec2", region_name="us-west-2")
#     reservations = ec2_client.describe_instances(Filters=[
#         {
#             "Name": "instance-state-name",
#             "Values": ["running"],
#         }
#     ]).get("Reservations")
#     for reservation in reservations:
#         for instance in reservation["Instances"]:
#             instance_id = instance["InstanceId"]
#             instance_type = instance["InstanceType"]
#             public_ip = instance["PublicIpAddress"]
#             private_ip = instance["PrivateIpAddress"]
#             print(f"{instance_id}, {instance_type}, {public_ip}, {private_ip}")
#     return None


def load_regions():
    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    region_count = [i for i in range(1, len(regions) + 1)]
    region_dict = {i: j for i, j in zip(region_count, regions)}
    return regions, region_count, region_dict


def ec2_instance_types(ec2_client):
    """Yield all available EC2 instance types in region <region_name>"""
    describe_args = {}
    while True:
        describe_result = ec2_client.describe_instance_types(**describe_args)
        yield from [i['InstanceType'] for i in describe_result['InstanceTypes']]
        if 'NextToken' not in describe_result:
            break
        describe_args['NextToken'] = describe_result['NextToken']
    return None


def print_instance_types(ec2_client):
    result = [ec2_type for ec2_type in ec2_instance_types(ec2_client)]
    result.sort()
    for ec2_type in result:
        print(ec2_type)
    return None


def get_external_ip():
    spin = start_spinner(busy_text='Getting your external IP address...')
    external_ip = urllib.request.urlopen('http://ident.me').read().decode('utf8')
    spin.stop()
    return external_ip


def custom_sg_rule(port, custom_ip):
    custom_rule = {
        'IpProtocol': 'tcp',
        'FromPort': port,
        'ToPort': port,
        'IpRanges': [{'CidrIp': f'{custom_ip}/0'}]
    }
    return custom_rule


def customtv_sg_rule(port, custom_ip):
    custom_rule = {
        'IpProtocol': 'tcp',
        'FromPort': port,
        'ToPort': port,
        'IpRanges': [{'CidrIp': f'{custom_ip}/32'}]
    }
    return custom_rule


######################################################################################################################
#                                                    Initialize                                                      #
######################################################################################################################
start_time = time.time()
started = datetime.now().strftime("%Y-%m-%d %I:%M:%S")
yes_list = ['yes', 'Yes', 'y', 'ye', 'Ye']
no_list = ['no', 'No', 'n', 'exit', 'Exit', 'new', 'New']
image_id = 'ami-0fb653ca2d3203ac1'  # Ubuntu 20.04 LTS
dry_run = False
delay_print_fast("Welcome to the MML Auto-EC2 Generator")
delay_print_slow("... ")
delay_print_fast("Make an instance you deserve")
print("")
time.sleep(1)
print('You will need an AWS account to continue, if you do not currently have an account, please create one here: '
      'https://portal.aws.amazon.com/billing/signup?#/start')
time.sleep(1)
input(f"Press any key to continue")

######################################################################################################################
#                                                       Login                                                        #
######################################################################################################################
"""Login or Configure AWS"""
while True:
    try:
        sts = boto3.client('sts')
        cid = sts.get_caller_identity()
        ec2_client = boto3.client('ec2')
        default_region = ec2_client.meta.region_name
        print(f"Credentials are valid. Logged in as {cid['UserId']}. Your default region is {default_region}.")
        break

    except Exception:
        print("AWS-CLI configuration not found. Please login to continue. You will need your AWS Access Key ID and AWS Secret Access Key. "
              "If you do not have access to your credentials, please create a new access key here:"
              "https://console.aws.amazon.com/iam/home?#/security_credentials")

        while True:
            aws_access_key_id = input("Please enter your AWS Access Key ID (e.g. BRLO5fZMGMLRZV843HX9): ")
            aws_access_key_id = aws_access_key_id.replace(" ", "").replace("-", "").replace(",", "").replace(".", "")
            key_check = input(f"You've entered '{aws_access_key_id}', is this correct (y/n): ")
            if key_check in yes_list:
                break
            print("Please try again")
        while True:
            aws_secret_access_key = input(
                "Please enter your AWS Secret Access Key (e.g. K3FH68epJG0LglLT7hYtMfr4nXFWsB5zKSipLZWm): ")
            aws_secret_access_key = aws_secret_access_key.replace(" ", "").replace("-", "").replace(",", "").replace(".",
                                                                                                                     "")
            key_check = input(f"You've entered '{aws_secret_access_key}', is this correct (y/n): ")
            if key_check in yes_list:
                break
            print("Please try again")
        while True:
            print("Next, we will choose a default region, to review a list of all available regions please visit this link: "
                  "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html#concepts-available-regions")
            time.sleep(1)
            account_region = input("Please enter your default region (e.g. us-east-2): ")
            account_region = account_region.replace(" ", "").replace(",", "").replace(".", "")
            key_check = input(f"You've entered '{account_region}', is this correct (y/n): ")
            if key_check in yes_list:
                break
            print("Please try again")

        """Creating Files"""
        print("We will now create your AWS credential files")
        """Check if .aws folder exists"""
        aws_path = os.path.join(os.path.expanduser('~'), '.aws')
        dir_exists = os.path.isdir(aws_path)
        """Create folder if it doesn't exist"""
        if not dir_exists:
            os.makedirs(aws_path)

        """Set paths"""
        aws_path = os.path.join(os.path.expanduser('~'), '.aws')
        config_path = os.path.join(os.path.join(os.path.expanduser('~'), '.aws'), 'config')
        credentials_path = os.path.join(os.path.join(os.path.expanduser('~'), '.aws'), 'credentials')

        spin = start_spinner(busy_text=f'Creating config & credentials file in {aws_path}...')
        with open(config_path, "w") as config_file:
            config_file.write("[default]\n")
            config_file.write(f"region = {account_region}\n")

        with open(credentials_path, "w") as credentials_file:
            credentials_file.write("[default]\n")
            credentials_file.write(f"aws_access_key_id = {aws_access_key_id}\n")
            credentials_file.write(f"aws_secret_access_key = {aws_secret_access_key}\n")

        time.sleep(2)
        spin.stop()
        continue

time.sleep(1)
######################################################################################################################
#                                                       Regions                                                      #
######################################################################################################################
while True:
    try:
        spin = start_spinner(busy_text='Loading Regions...')
        ec2_client = boto3.client('ec2')
        regions, region_count, region_dict = load_regions()
        spin.stop()

        print("Next, we will choose your desired region for your EC2 instance. To learn about AWS regions, please visit this "
              "link: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html")
        time.sleep(1)

        default_region = ec2_client.meta.region_name
        default_region_number = [key for key, value in region_dict.items() if value == default_region][0]
        sel = default_region
        sel2 = 'n'
        selected_region = default_region

        """Get Desired Region"""
        confirm_default_region = input(f"Would you like to use your default region ({default_region})? (y/n) ")
        if confirm_default_region in yes_list:
            print(f"********************************************************************************************\n"
                  f"You've confirmed your region as: {default_region}"
                  f"\n********************************************************************************************")
            selected_region = default_region
        else:
            sel0 = input(f"Would you like to review a list of regions? (y/n) ")
            while sel2 not in yes_list:
                if sel0 in no_list:
                    sel = input(f"Please enter a region, your default region is {default_region} (#{default_region_number}): ")
                    if sel not in regions:
                        print("This is not a valid region, please try again")
                    else:
                        sel2 = input(f"You've selected {sel}, is this correct? (y/n): ")
                        if sel2 not in yes_list:
                            print("Please choose again")
                        else:
                            print(f"********************************************************************************************\n"
                                  f"You've confirmed your region as: {sel}"
                                  f"\n********************************************************************************************")
                            selected_region = sel
                else:
                    for key, value in region_dict.items():
                        print(f"{key}. {value}")
                    time.sleep(.5)
                    print("Please review the available regions from the list above, the default region is us-east-2 (#15): ")
                    time.sleep(0.5)
                    while sel2 not in yes_list:
                        try:
                            sel = int(input(f"Please select a region (1-{len(region_dict)}): "))
                            if len(regions) <= sel <= 0:
                                print("This is not a valid region, please try again")
                            else:
                                sel2 = input(f"You've selected {region_dict[sel]}, is this correct? (y/n): ")
                                if sel2 not in yes_list:
                                    print("Please choose again")
                        except Exception:
                            print("This is not a valid region, please try again")
                    print(f"********************************************************************************************\n"
                          f"You've confirmed your region as: {region_dict[sel]}"
                          f"\n********************************************************************************************")
                    selected_region = region_dict[sel]

        ec2_client = boto3.client('ec2', region_name=selected_region)
    except Exception:
        continue
    break

time.sleep(1)
######################################################################################################################
#                                                Instance Types                                                      #
######################################################################################################################
while True:
    try:
        spin = start_spinner(busy_text='Loading Instance Types...')
        """Reset Client with Region Selected"""
        instance_type_list = [ec2_type for ec2_type in ec2_instance_types(ec2_client)]
        spin.stop()

        print("Now, we will choose your desired instance type, to review instance specs, please visit this link: "
              "https://aws.amazon.com/ec2/instance-types/")
        time.sleep(1)

        sel3 = input(f"Would you like to review a list of instance types available in your region? (y/n): ")
        if sel3 in yes_list:
            print_instance_types(ec2_client)

        default_instance = 't2.micro'
        sel4 = 't2.micro'
        """Get Desired Instance Type"""
        while True:
            try:
                sel4 = input(f"Please enter your desired instance type, the default type is {default_instance}: ")
                if sel4 in instance_type_list:
                    sel2 = input(f"You've selected {sel4}, is this correct? (y/n) ")
                    if sel2 not in yes_list:
                        print("Please choose again")
                        continue
                    break
                else:
                    print("This is not a valid instance, please try again")
            except Exception:
                print("This is not a valid instance, please try again")
                continue
        print(f"********************************************************************************************\n"
              f"You've confirmed your instance type as: {sel4}"
              f"\n********************************************************************************************")
        selected_type = sel4
    except Exception:
        continue
    break

time.sleep(1)
######################################################################################################################
#                                                       Subnet                                                      #
######################################################################################################################
while True:
    try:
        spin = start_spinner(busy_text='Loading Subnets...')
        sn_all = ec2_client.describe_subnets()
        sn_all = {key: value for key, value in sorted(sn_all.items())}
        spin.stop()

        print("Now, we will choose your desired subnet, to learn more about subnets, please visit this link: "
              "https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Subnets.html#subnet-basics")
        time.sleep(1)

        """Choose Subnet"""
        subnet_dict = {}
        for i in range(0, len(sn_all['Subnets'])):
            subnet = sn_all['Subnets'][i]
            print(f"{i+1}. {subnet['AvailabilityZone']}")
            subnet_dict[subnet['AvailabilityZone']] = subnet['SubnetId']
            time.sleep(.25)

        subnet_list = [*subnet_dict]
        default_subnet = subnet_list[0]
        sel5 = subnet_list[0]
        """Get Desired Subnet"""
        while True:
            try:
                sel5 = input(f"Please enter your desired subnet (1-3), the default type is {default_subnet}: ")
                sel5 = subnet_list[int(sel5)-1]
                sel6 = input(f"You've selected {sel5}, is this correct? (y/n) ")
                if sel6 not in yes_list:
                    print("Please choose again")
                    continue
                break
            except Exception:
                print("This is not a valid subnet, please try again")
                continue
        print(f"********************************************************************************************\n"
              f"You've confirmed your subnet as: {sel5}"
              f"\n********************************************************************************************")

        selected_subnet = sel5
        selected_subnetid = subnet_dict[sel5]
    except Exception:
        continue
    break

time.sleep(1)
#####################################################################################################################
#                                                   Storage                                                         #
#####################################################################################################################
while True:
    try:
        print("Now, we will choose your desired storage options, to learn more about EBS specs, please visit this link: "
              "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volume-types.html?")
        time.sleep(1)

        """Select Storage"""
        """Select Volume Type"""
        print(f"Please review the instance types below: ")
        volume_type_dict = {1: 'gp3', 2: 'gp2', 3: 'io2', 4: 'io1'}
        volume_type = 'gp3'
        volume_type_confirm = 'no'
        while volume_type_confirm not in yes_list:
            try:
                for key, value in volume_type_dict.items():
                    print(f"{key}. {value}")
                volume_type_sel = int(input(f"Please select a volume type (1-{len(volume_type_dict)}), the default is 1. gp3: "))
                if len(volume_type_dict) <= volume_type_sel < 0:
                    print("This is not a valid volume type, please try again")
                else:
                    volume_type_confirm = input(f"You've selected {volume_type_dict[volume_type_sel]}, is this correct? (y/n): ")
                    if volume_type_confirm not in yes_list:
                        print("Please choose again")
                    volume_type = volume_type_dict[volume_type_sel]
            except Exception:
                print("This is not a valid volume type, please try again")

        while True:
            volume_size = input(f"Please enter the desired size of the root volume (between 8GB and 16TB): ").lower()
            if "tb" in volume_size:
                volume_size = volume_size.replace("tb", "").replace(" ", "").replace("-", "").replace(",", "")
                volume_size = int(float(volume_size) * 1000 + 0.5)
            elif "tib" in volume_size:
                volume_size = volume_size.replace("tib", "").replace(" ", "").replace("-", "").replace(
                    ",", "")
                volume_size = int(float(volume_size) * 1024 + 0.5)
            elif "gb" in volume_size:
                volume_size = volume_size.replace("gb", "").replace(" ", "").replace("-", "").replace(",", "")
                volume_size = int(float(volume_size) + 0.5)
            elif "gib" in volume_size:
                volume_size = volume_size.replace("gib", "").replace(" ", "").replace("-", "").replace(",", "")
                volume_size = int(float(volume_size) * 1.07 + 0.5)
            else:
                volume_size = volume_size.replace(" ", "").replace("-", "").replace(",", "")
                volume_size = int(float(volume_size) + 0.5)

            if volume_size < 8 or volume_size > 16000:
                print("This is not a valid volume size, please a value between 8 GB and 16,000 GB")
                continue

            volume_confirm = input(f"You've chosen {volume_size:,} GB. Is this correct? (y/n): ")
            if volume_confirm not in yes_list:
                print("Please choose again")
                continue
            else:
                break

        """IOPS/THROUGHPUT/ENCRYPTION/DELETION"""
        """
        Options by Type:
        GP2 only has a size, encryption, and AZ option
        GP3 has size, iops(3000 IOPS, Max: 16000 IOPS), throughput, AZ, encryption
        io1 has size, iops(100 IOPS, Max: 5000 IOPS), AZ, encryption
        io2 has size, iops(100 IOPS, Max: 100000 IOPS), AZ, encryption
        """

        if volume_type in ['gp3', 'io1', 'io2']:
            """[GP3, io1, io2 ONLY] Select IOPS"""
            iops_options_dict = {'gp3': [3000, 16000], 'io1': [100, 5000], 'io2': [100, 100000]}
            selected_iops = iops_options_dict[volume_type][0]
            iops = iops_options_dict[volume_type][0]
            iops_confirm = 'no'
            min_iops = iops_options_dict[volume_type][0]
            max_iops = iops_options_dict[volume_type][1]
            while iops_confirm not in yes_list:
                try:
                    selected_iops = (input(f"Please select number of IOPS between {min_iops:,} and {max_iops:,}, the default is {selected_iops:,}: "))
                    selected_iops = int(selected_iops.replace(" ", "").replace("-", "").replace(",", ""))
                    if selected_iops not in range(min_iops, max_iops+1):
                        print("This is not a valid number of IOPS, please try again")
                    else:
                        iops_confirm = input(f"You've selected {selected_iops:,}, is this correct? (y/n): ")
                        if iops_confirm not in yes_list:
                            print("Please choose again")
                        iops = selected_iops
                except Exception:
                    print("This is not a valid number of IOPS, please try again")

        """[GP3 ONLY] Select Throughput"""
        if volume_type == 'gp3':
            selected_throughput = 125
            throughput = 125
            throughput_confirm = 'no'
            while throughput_confirm not in yes_list:
                try:
                    selected_throughput = int(input(f"Please select a throughput value between 125 and 1000, the default is 125: "))
                    if selected_throughput not in range(125, 1001):
                        print("This is not a valid throughput value, please try again")
                    else:
                        throughput_confirm = input(f"You've selected {selected_throughput}, is this correct? (y/n): ")
                        if throughput_confirm not in yes_list:
                            print("Please choose again")
                        throughput = selected_throughput
                except Exception:
                    print("This is not a valid throughput value, please try again")

        """Encryption"""
        selected_encryption = False
        sel_encrypt = input(f"Would you like to encrypt this volume? The default is no. (y/n): ")
        while True:
            if sel_encrypt not in yes_list:
                selected_encryption = False
            elif sel_encrypt in yes_list:
                selected_encryption = True
            else:
                print("Not a valid choice, please choose again")
                continue
            break

        """Delete Volume on Termination"""
        delete_on_term = True
        delete_on_term_input = input(f"Would you like to delete this volume when the instance is deleted? The default is yes. (y/n): ")
        while True:
            if delete_on_term_input not in yes_list:
                delete_on_term = False
            elif delete_on_term_input in yes_list:
                delete_on_term = True
            else:
                print("Not a valid choice, please choose again")
                continue
            break

        """Set Block Device Mappings for EC2 Launch Template"""
        if volume_type == 'gp3':
            block_device_mappings = [{
            'DeviceName': '/dev/sda1',
            'Ebs': {
                'Throughput': throughput,
                'Iops': iops,
                'Encrypted': selected_encryption,
                'DeleteOnTermination': delete_on_term,
                'VolumeSize': volume_size,
                'VolumeType': volume_type
                    },
                },
            ],

        elif volume_type in ['io1', 'io2']:
            block_device_mappings = [{
            'DeviceName': '/dev/sda1',
            'Ebs': {
                'Iops': iops,
                'Encrypted': selected_encryption,
                'DeleteOnTermination': delete_on_term,
                'VolumeSize': volume_size,
                'VolumeType': volume_type
                    },
                },
            ],
            throughput = 'n/a'

        else:
            block_device_mappings = [{
            'DeviceName': '/dev/sda1',
            'Ebs': {
                'Encrypted': selected_encryption,
                'DeleteOnTermination': delete_on_term,
                'VolumeSize': volume_size,
                'VolumeType': volume_type
                    },
                },
            ],
            throughput = 'n/a'
            iops = 'n/a'

        confirm_volume = 'n'
        while confirm_volume in no_list:
            print(f"********************************************************************************************\n"
                  f"You've selected the following volume settings:\n"
                  f"Volume type: {volume_type}\n"
                  f"Volume size: {volume_size} GB\n"
                  f"Throughput: {throughput}\n"
                  f"IOPS: {iops}\n"
                  f"Volume encryption: {selected_encryption}\n"
                  f"Delete Volume with Instance: {delete_on_term}\n"
                  f"********************************************************************************************")
            confirm_volume = input(f"Does this look correct? (y/n): ")
            if confirm_volume not in yes_list:
                print("Please choose your settings again")
                break
        if confirm_volume in yes_list:
            break
        continue
    except Exception:
        continue

time.sleep(1)
#####################################################################################################################
#                                               Software Configurations                                             #
#####################################################################################################################
while True:
    try:
        base_user_data = '''
        #!/bin/bash
        #
        #Apply updates
        apt -y update
        apt -y upgrade
        #
        #Install pip
        apt install python3-pip
        #
        #Install virtual-environments
        apt install python3.8-venv
        pip3 install virtualenv
        #
        #Install pigz
        apt install pigz
        #
        #Install aws-cli
        apt install awscli
        '''
        ud_postgres = '''#
        #Install Postgres
        apt update && apt upgrade
        sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
        wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
        apt -y update
        apt -y install postgresql-14
        systemctl start postgres
        '''
        ud_redis = '''#
        #Install Redis
        apt install redis-server
        systemctl start redis-server
        '''
        ud_caddy = '''#
        #Install Caddy
        apt install -y debian-keyring debian-archive-keyring apt-transport-https
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | tee /etc/apt/trusted.gpg.d/caddy-stable.asc
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
        apt -y update
        apt install caddy
        systemctl start caddy
        '''
        ud_nginx = '''#
        #Install Nginx
        apt install nginx
        systemctl start nginx
        '''
        ud_git = '''#
        #Install git
        apt install git-all
        '''
        ud_mongodb = '''#
        #Install Mongodb
        apt install gnupg
        wget -qO - https://www.mongodb.org/static/pgp/server-5.0.asc | apt-key add -
        echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/5.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-5.0.list
        apt -y update
        apt -y install mongodb-org
        systemctl start mongod
        '''
        ud_apache = '''#
        #Install Apache
        apt install apache2
        systemctl start apache2
        '''
        ud_docker = '''#
        #Install Docker
        apt remove docker docker-engine docker.io containerd runc
        apt install ca-certificates curl gnupg lsb-release
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu  (lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt update
        apt install docker-ce docker-ce-cli containerd.io
        systemctl start docker
        '''
        ud_node = '''#
        #Install NodeJS
        apt install nodejs
        apt install npm
        '''
        ud_airflow = '''#
        #Install Airflow
        apt-get install libmysqlclient-dev
        apt-get install libssl-dev
        apt-get install libkrb5-dev
        virtualenv airflow_idroot
        cd airflow_idroot/
        source activate
        export AIRFLOW_HOME=~/airflow
        install apache-airflow
        pip3 install typing_extensions
        airflow db init
        airflow webserver -p 8080
        '''
        ud_mysql = '''#
        #Install MySQL
        apt install mysql-server
        systemctl start mysqld
        '''
        ud_sqlite3 = '''#
        #Install sqlite3
        apt install sqlite3
        '''
        end_user_data = '''#
        #Restart
        shutdown -r now
        '''
        user_data = base_user_data
        confirmed_software = []

        toppings = {"Postgres": [1, ud_postgres], "MongoDB": [2, ud_mongodb], "MySQL": [3, ud_mysql], "sqlite3": [4, ud_sqlite3], "Redis": [5, ud_redis],
                    "Docker": [6, ud_docker], "Git": [7, ud_git], "Nginx": [8, ud_nginx], "Caddy": [9, ud_caddy], "Apache": [10, ud_apache], "NodeJS": [11, ud_node],
                    "Airflow": [12, ud_airflow]
                    }
        software_choice = {1: 'Plain (No software)', 2: 'Basics (PostgreSQL, Redis)', 3: 'Nosql (MongoDB, Redis)',
                           4: 'Extras (PostgreSQL, Redis, Git, Docker, Caddy)', 5: 'Custom (Choose software from list)'}
        software_selection = {1: 'user_data_plain', 2: 'user_data_basic', 3: 'user_data_premium', 4: 'user_data_advanced'}

        software_specifics = {1: 'Postgres', 2: 'MongoDB', 3: 'MySQL', 4: 'sqlite3', 5: 'Redis', 6: 'Docker', 7: 'Git',
                              8: 'Nginx', 9: 'Caddy', 10: 'Apache', 11: 'NodeJS', 12: 'Airflow'}

        print("Now we will choose your desired software options, this allows you to pre-install commonly used programs")
        time.sleep(1)
        for i in software_choice:
            print(f'{i}. {software_choice[i]}')
            time.sleep(.25)

        print(f"Please review the software packages above, the default is Basic (#2)")
        software_sel = 2
        toppings_list = [1, 5]
        software_conf = 'no'
        while software_conf not in yes_list:
            try:
                software_sel = int(input(f"Please select a software package (1-{len(software_choice)}): "))
                if len(software_choice) <= software_sel <= 0:
                    print("This is not a valid selection, please try again")
                else:
                    software_conf = input(f"You've selected {software_choice[software_sel]}, is this correct? (y/n): ")
                    if software_conf not in yes_list:
                        print("Please choose again")
                        continue
                    break
            except Exception:
                print("This is not a valid selection, please try again")

        if software_sel == 'all':
            toppings_list = lst = list(range(1, len(toppings)+1))
            print(toppings_list)

        elif software_sel == 5:
            print(f"Please review the available software packages:")
            for i in toppings.keys():
                print(f'{toppings[i][0]}. {i}')
                time.sleep(0.25)
            toppings_selection = input(f"Please enter your desired software packages in a comma separated list (e.g. 1,2,3) or enter 'all' to install all packages: ")
            if toppings_selection == 'all':
                toppings_list = lst = list(range(1, len(toppings) + 1))
            else:
                toppings_selection = toppings_selection.replace(" ", "").replace("-", "").replace(",", "")
                toppings_list = list(toppings_selection)
                toppings_list = list(map(int, toppings_list))

        elif software_sel == 4:
            toppings_list = [1, 5, 6, 7, 9]
        elif software_sel == 3:
            toppings_list = [2, 5]
        elif software_sel == 2:
            toppings_list = [1, 5]
        elif software_sel == 1:
            toppings_list = None

        """Create Software Configurations"""
        """Add userdata based on software selection"""
        for i in toppings_list:
            user_data = user_data+toppings[software_specifics[i]][1]
            confirmed_software.append(software_specifics[i])

        """Add end_user_data to restart instance after installing software"""
        user_data = user_data+end_user_data

        print(f"********************************************************************************************\n"
              f"You've confirmed your software as: {confirmed_software}"
              f"\n********************************************************************************************")

    except Exception:
        continue
    break

time.sleep(1)
######################################################################################################################
#                                                  Create Security Group                                             #
######################################################################################################################
while True:
    try:
        print("Now, we will setup the Secruity Group for your EC2 instance, to learn more about AWS Security Groups, please visit this link:"
              "https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html")
        time.sleep(1)
        """Get Existing Security Groups"""
        spin = start_spinner(busy_text='Loading Security Group Settings...')
        existing_security_groups = ec2_client.describe_security_groups()
        existing_vpcs = ec2_client.describe_vpcs().get('Vpcs', [{}])[0]['VpcId']
        spin.stop()

        sg_view_existing = 'y'
        sg_existing_list = []
        while sg_view_existing in yes_list:
            sg_view_existing = input(f'Would you like to use an existing Security Group? (y/n): ')
            if sg_view_existing in yes_list:
                for i in existing_security_groups['SecurityGroups']:
                    sg_existing_list.append(i['GroupName'])
                sg_existing_dict = dict(enumerate(sg_existing_list, start=1))
                sg_confirm = 'n'
                while sg_confirm not in yes_list:
                    try:
                        for i in range(1, len(sg_existing_dict)):
                            print(f"{i}. {sg_existing_dict[i]}")
                        sg_selection = input(f'Please enter a Security Group to use (1-{len(sg_existing_dict)}), or \'new\' to exit and create a new group: ')
                        if sg_selection in no_list:
                            sg_view_existing = 'no'
                            break
                        sg_selection = int(sg_selection)
                        if sg_selection not in range(1, len(sg_existing_dict)):
                            print("This is not a valid selection, please try again")
                            continue
                        selected_sg = sg_existing_dict[sg_selection]
                        sg_confirm = input(f"You've selected {selected_sg}, is this correct? (y/n): ")
                        if sg_confirm in no_list:
                            print("Please try again")
                            continue
                        security_group_id = existing_security_groups['SecurityGroups'][sg_selection]['GroupId']
                        print(f"********************************************************************************************\n"
                              f"You've confirmed your Security Group as: {selected_sg} ({security_group_id})"
                              f"\n********************************************************************************************")
                        break
                    except Exception:
                        print("This is not a valid selection, please try again")
                        print(Exception)
                    break
                break
            break

        while sg_view_existing in no_list:
            print(f"We will now create a new Security Group: ")
            """Create New Security Group"""
            ip_confirm = 'no'
            while ip_confirm not in yes_list:
                external_ip = get_external_ip()
                ip_confirm = input(f'Your external IP address is {external_ip}, does this look correct? (y/n): ')
                if ip_confirm not in yes_list:
                    external_ip = input("Please manually enter your IP address in the format of 0.0.0.0: ")
                    external_ip_check = list(
                        external_ip.replace(" ", "").replace(".", "").replace("/", "").replace(":", ""))
                    if len(external_ip_check) != 4:
                        print(f"You've entered an incorrect IP address '{external_ip}', please try again")
                        continue

            """Name Security Group"""
            security_group_name = f'mml_sg-0{secrets.token_hex(8)}'
            selected_sg = security_group_name
            """Create Rules"""
            security_group_rules = []
            relaxed = {
                'IpProtocol': '-1',
                'FromPort': -1,
                'ToPort': -1,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }

            strict = {
                'IpProtocol': '-1',
                'FromPort': -1,
                'ToPort': -1,
                'IpRanges': [{'CidrIp': f'{external_ip}/0'}]
            }

            psql_rule = {
                'IpProtocol': 'tcp',
                'FromPort': 5432,
                'ToPort': 5432,
                'IpRanges': [{'CidrIp': '0.0.0.0/32'}]
            }
            mysql_rule = {
                'IpProtocol': 'tcp',
                'FromPort': 3306,
                'ToPort': 3306,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
            mongodb_rule = {
                'IpProtocol': 'tcp',
                'FromPort': 27017,
                'ToPort': 27017,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
            rules = {1: ["Relaxed", relaxed, 'Allows all connections (0.0.0.0)'],
                     2: ["Strict", strict, f'Allows connections only from your IP ({external_ip})']}
            software_rules = {'Postgres': psql_rule, 'MongoDB': mongodb_rule, 'MySQL': mysql_rule}

            print("First, we'll choose a base set of rules for this Security Group (we'll add custom ones next):")
            for i in rules:
                print(f'{i}. {rules[i][0]} - {rules[i][2]}')

            base_confirm = 'no'
            while base_confirm not in yes_list:
                try:
                    choose_base_rules = int(input("Please select the desired set of base rules (1 or 2): "))
                    if choose_base_rules not in range(1, len(rules)+1):
                        print("This is not a valid selection, please try again")
                        continue
                    base_confirm = input(f"You've selected '{rules[choose_base_rules][0]}', is this correct? (y/n): ")
                    security_group_rules.append(rules[choose_base_rules][1])
                except Exception:
                    print("This is not a valid selection, please try again")
                    continue
                break

            spin = start_spinner(busy_text="Adding rules to allow database access...")
            for i in confirmed_software:
                try:
                    security_group_rules.append(software_rules[i])
                except Exception:
                    security_group_rules = security_group_rules
            spin.stop()

            add_another_rule = 'yes'
            while add_another_rule not in no_list:
                add_another_rule = input(f'Would you like to manually add another rule? (y/n): ')
                if add_another_rule in yes_list:
                    custom_ip = input("Please manually enter the IP address in the format of 0.0.0.0: ")
                    add_ip_check = list(custom_ip.replace(" ", "").replace(".", "").replace("/", "").replace(":", ""))
                    if len(add_ip_check) != 4:
                        print(add_ip_check)
                        print(f"You've entered an incorrect IP address '{custom_ip}', please try again")
                        continue
                    try:
                        port = int(input("Please manually enter the port number:"))
                    except Exception:
                        print("That's not a valid port, please start over")
                        continue
                    security_group_rules.append(custom_sg_rule(port, custom_ip))
                    print(f"Successfully added IP address {custom_ip} / Port {port}")
                if add_another_rule in no_list:
                    add_tv = 'yes'
                    while add_tv not in no_list:
                        print("We can automatically allow TradingView Webhooks to connect to your instance. "
                              "Learn more about TradingView Webhooks here: "
                              "https://www.tradingview.com/support/solutions/43000529348-about-webhooks/")
                        add_tv = input(f'Would you like to permission TradingView IPs to allow Webhooks? (y/n): ')
                        if add_tv in yes_list:
                            tv_ips = ['52.89.214.238', '34.212.75.30', '54.218.53.128', '52.32.178.7']
                            ports = [80, 443]
                            for port in ports:
                                for ip in tv_ips:
                                    security_group_rules.append(customtv_sg_rule(port, ip))
                            break
                    break

            """Create Security Group"""
            spin = start_spinner(busy_text='Creating Security Group...')
            description = f'{security_group_name} created by the MML Auto-EC2 generator on {datetime.now()}'
            response = ec2_client.describe_vpcs()
            vpc_id = response.get('Vpcs', [{}])[0]['VpcId']
            try:
                """Create Security Group"""
                response = ec2_client.create_security_group(GroupName=security_group_name,
                                                            Description=description,
                                                            VpcId=vpc_id,
                                                            DryRun=dry_run)
                security_group_id = response['GroupId']
                print(f'Created Security Group {security_group_id} in vpc {vpc_id}.')

                """Set Ingress Rules"""
                data = ec2_client.authorize_security_group_ingress(
                    GroupId=security_group_id,
                    IpPermissions=security_group_rules,
                    DryRun=dry_run
                )

            except Exception as e:
                print(e)

            stop_spinner(spin, done_text=f'Security Group Created: {security_group_name}')
            break

        time.sleep(1)

        """Create Key Pair"""
        key_pair_location = 'keypair.pem'
        confirm_key = 'n'
        while confirm_key not in yes_list:
            create_key = input(f"Do you need a new keypair.pem? If this is your first instance choose 'yes' (y/n): ")
            if create_key in yes_list:
                confirm_key = input(f"You've selected to create a new keypair, is this correct? (y/n): ")
                if confirm_key in yes_list:
                    spin = start_spinner(busy_text='Creating Key Pair')
                    key_name = f'keypair_{secrets.token_hex(2)}'
                    key = ec2_client.create_key_pair(KeyName=key_name, KeyType='rsa')
                    with open(f'{key_name}.pem', 'w') as file:
                        file.write(key['KeyMaterial'])

                    key_pair_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), f'{key_name}.pem')
                    """Check if path has spaces, if there are spaces - add quotes, if not - keep unquoted"""
                    if " " in key_pair_location:
                        key_pair_location = f"'{key_pair_location}'"
                    else:
                        key_pair_location = key_pair_location

                    spin.stop()

            if create_key in no_list:
                confirm_key = input(f"You've selected to not create a new keypair, is this correct? (y/n): ")
                if confirm_key in yes_list:
                    break
                else:
                    continue
    except Exception:
        continue
    break

time.sleep(1)
######################################################################################################################
#                                               Create Instance                                                      #
######################################################################################################################
print(f"We will now create your instance")
input(f"Press any key to continue")

time.sleep(1)
"""Create EC2 Instance"""
spin = start_spinner(busy_text='Creating instance...')
response = ec2_client.run_instances(
    BlockDeviceMappings=block_device_mappings[0],
    ImageId=image_id,
    InstanceType=selected_type,
    KeyName=key_name,
    SubnetId=selected_subnetid,
    UserData=user_data,
    MaxCount=1,
    MinCount=1,
    Monitoring={
        'Enabled': False
    },
    Placement={
        'AvailabilityZone': selected_subnet
    },
    SecurityGroupIds=[
        f'{security_group_id}',
    ],
    DryRun=dry_run
    )
instance_id = response["Instances"][0]['InstanceId']
stop_spinner(spin, done_text=f'Instance created, ID: {instance_id} ')

######################################################################################################################
#                                                     Elastic IP                                                     #
######################################################################################################################
"""Create Elastic IP"""
spin = start_spinner(busy_text='Creating Elastic IP address...')

allocate_elip = ec2_client.allocate_address(
    # Domain='vpc' or 'standard',
    Domain='vpc',
    # Address='string',
    # PublicIpv4Pool='string',
    # NetworkBorderGroup='string',
    # CustomerOwnedIpv4Pool='string',
    DryRun=dry_run,
)
public_ip = allocate_elip['PublicIp']
stop_spinner(spin, done_text=f'Elastic IP created, IP: {public_ip}')

"""Associate Elastic IP"""
spin = start_spinner(busy_text=f'Associating Elastic IP with instance {instance_id}')
time.sleep(30)
associate_elip = ec2_client.associate_address(
    InstanceId=instance_id,
    PublicIp=public_ip,
    # AllocationId=None,
    # NetworkInterfaceId=None,
    # PrivateIpAddress=None,
    AllowReassociation=False,
    DryRun=dry_run
)
spin.stop()
stop_spinner(spin, done_text=f'Elastic IP {public_ip} associated with instance {instance_id}')

######################################################################################################################
#                                                 Create ReadMe File                                                 #
######################################################################################################################
run_time = "{:.2f}".format((time.time() - start_time)/60)
spin = start_spinner(busy_text='Creating documentation...')
"""Create #ReadMe file for end user"""
save_date = datetime.now().strftime("%m%d%y_%I%M")
file_name = f'Auto-EC2_Summary_{save_date}.txt'
with open(f"{file_name}", "w") as readme_file:
    readme_file.write(f"Your MML Auto-EC2 Generator Summary \n"
       f"------------------------------------ \n"
       f"Instance URL: https://us-east-2.console.aws.amazon.com/ec2/v2/home?region={selected_region}#InstanceDetails:instanceId={instance_id} \n"
       f"Connect to your instance with the following command: ssh -i '{key_pair_location}' ubuntu@{public_ip} \n"
       f"Start time: {started}, total run time: {run_time} minutes \n"
       f"Image name: {image_id}, image ID: {image_id} \n"
       f"Region: {selected_region} \n"
       f"Instance type: {selected_type} \n"
       f"Subnet: {selected_subnet} \n"
       f"Root volume details: {block_device_mappings} \n"
       f"Elastic IP address: {public_ip} \n"
       f"------------------------------------ \n"
       f"Thank you for using the MML Auto-EC2 Generator! We hope you liked this MML open source offering, if you "
       f"have any questions or just want to chat - join us on discord: https://discord.gg/jjDcZcqXWy! \n"
       f"To support our development, please consider subscribing at https://marketmakerlite.com/subscribe \n"
       )

readme_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name)
stop_spinner(spin, done_text="Documentation created")

######################################################################################################################
#                                                 Exit Message                                                       #
######################################################################################################################
print("Success! Your instance has been created successfully!")
time.sleep(1)
print(f"You can view the summary of this MML Auto-EC2 Generator session here: {readme_location}")
time.sleep(1)
print(f"You can view your instance online here: https://us-east-2.console.aws.amazon.com/ec2/v2/home?region={selected_region}#InstanceDetails:instanceId={instance_id}")
time.sleep(1)
print(f"You can connect to your instance via SSH with the following command: ssh -i '{key_pair_location}' ubuntu@{public_ip}")
time.sleep(1)
print("Thank you for using the MML Auto-EC2 Generator! We hope you liked this MML open source offering, "
      "if you have any questions or just want to chat - join us on discord: https://discord.gg/jjDcZcqXWy!")
time.sleep(1)
print("To support our development, please consider subscribing at https://marketmakerlite.com/subscribe")
