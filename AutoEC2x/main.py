import boto3
from botocore import exceptions as bc
import time
import os
from datetime import datetime
import secrets
import urllib.request
import config
import traceback
import json
######################################################################################################################
#                                                       Functions                                                    #
######################################################################################################################


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


def create_userdata(toppings_selection, custom_userdata):
    base_user_data = '''#!/bin/bash
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
    #
    '''
    user_data = base_user_data
    confirmed_software = []

    toppings = {"Postgres": [1, ud_postgres], "MongoDB": [2, ud_mongodb], "MySQL": [3, ud_mysql],
                "sqlite3": [4, ud_sqlite3], "Redis": [5, ud_redis],
                "Docker": [6, ud_docker], "Git": [7, ud_git], "Nginx": [8, ud_nginx], "Caddy": [9, ud_caddy],
                "Apache": [10, ud_apache], "NodeJS": [11, ud_node],
                "Airflow": [12, ud_airflow]
                }

    software_specifics = {1: 'Postgres', 2: 'MongoDB', 3: 'MySQL', 4: 'sqlite3', 5: 'Redis', 6: 'Docker',
                          7: 'Git',
                          8: 'Nginx', 9: 'Caddy', 10: 'Apache', 11: 'NodeJS', 12: 'Airflow'}

    if toppings_selection == 'all':
        toppings_list = lst = list(range(1, len(toppings) + 1))
    else:
        toppings_selection = toppings_selection.replace(" ", "").replace("-", "").replace(",", "")
        toppings_list = list(toppings_selection)
        toppings_list = list(map(int, toppings_list))

    """Create Software Configurations"""
    """Add userdata based on software selection"""
    for i in toppings_list:
        user_data = user_data + toppings[software_specifics[i]][1]
        confirmed_software.append(software_specifics[i])

    """Add custom userdata"""
    if custom_userdata is not None:
        user_data = user_data + custom_userdata

    """Add end_user_data to restart instance after installing software"""
    user_data = user_data + end_user_data

    return user_data, confirmed_software


def get_external_ip():
    external_ip = urllib.request.urlopen('http://ident.me').read().decode('utf8')
    return external_ip


def custom_sg_rule(port, custom_ip):
    custom_rule = {
        'IpProtocol': 'tcp',
        'FromPort': port,
        'ToPort': port,
        'IpRanges': [{'CidrIp': f'{custom_ip}/32'}]
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
dry_run = config.dry_run
######################################################################################################################
#                                                       Login                                                        #
######################################################################################################################
"""Login or Configure AWS"""
try:
    sts = boto3.client('sts')
    cid = sts.get_caller_identity()
    account = cid['UserId']
    ec2_client = boto3.client('ec2')
    default_region = ec2_client.meta.region_name
except bc.NoCredentialsError:
    aws_access_key_id = config.access_key_id
    aws_secret_access_key = config.secret_access_key

    """Check if .aws folder exists"""
    aws_path = os.path.join(os.path.expanduser('~'), '.aws')
    dir_exists = os.path.isdir(aws_path)

    """Create folder if it doesn't exist"""
    if not dir_exists:
        os.makedirs(aws_path)

    """Set paths"""
    config_path = os.path.join(aws_path, 'config')
    credentials_path = os.path.join(aws_path, 'credentials')

    with open(config_path, "w") as config_file:
        config_file.write("[default]\n")
        config_file.write(f"region = {config.selected_region}\n")

    with open(credentials_path, "w") as credentials_file:
        credentials_file.write("[default]\n")
        credentials_file.write(f"aws_access_key_id = {aws_access_key_id}\n")
        credentials_file.write(f"aws_secret_access_key = {aws_secret_access_key}\n")
    sts = boto3.client('sts')
    cid = sts.get_caller_identity()
    account = cid['UserId']
    ec2_client = boto3.client('ec2', region_name=config.selected_region)
    default_region = ec2_client.meta.region_name
######################################################################################################################
#                                                       Regions                                                      #
######################################################################################################################
regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]

use_default_region = config.use_default_region

if use_default_region:
    default_region = ec2_client.meta.region_name
    selected_region = default_region
else:
    selected_region = config.selected_region
    if selected_region not in regions:
        raise ValueError("Invalid Region")

ec2_client = boto3.client('ec2', region_name=selected_region)
######################################################################################################################
#                                                Instance Types                                                      #
######################################################################################################################
instance_type_list = [ec2_type for ec2_type in ec2_instance_types(ec2_client)]

selected_type = config.instance_type
if selected_type not in instance_type_list:
    raise ValueError("Invalid Instance Type")
######################################################################################################################
#                                                       Subnet                                                      #
######################################################################################################################
sn_all = ec2_client.describe_subnets()
sn_all = {key: value for key, value in sorted(sn_all.items())}
subnet_dict = {}
for i in range(0, len(sn_all['Subnets'])):
    subnet_dict[sn_all['Subnets'][i]['AvailabilityZone']] = sn_all['Subnets'][i]['SubnetId']
selected_subnet = selected_region+config.subnet_zone
selected_subnetid = subnet_dict[selected_subnet]
#####################################################################################################################
#                                                   Storage                                                         #
#####################################################################################################################
volume_type = config.volume_type
volume_size = config.volume_size.lower()

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
    raise ValueError("This is not a valid volume size, please a value between 8 GB and 16TB")

if volume_type in ['gp3', 'io1', 'io2']:
    """[GP3, io1, io2 ONLY] Select IOPS"""
    iops_options_dict = {'gp3': [3000, 16000], 'io1': [100, 5000], 'io2': [100, 100000]}
    min_iops = iops_options_dict[volume_type][0]
    max_iops = iops_options_dict[volume_type][1]

    selected_iops = config.volume_iops

    if selected_iops not in range(min_iops, max_iops+1):
        raise ValueError("Not a valid IOPS value")
    else:
        iops = selected_iops

"""[GP3 ONLY] Select Throughput"""
if volume_type == 'gp3':
    selected_throughput = config.volume_throughput
    if selected_throughput not in range(125, 1001):
        raise ValueError("Not a valid throughput")
    throughput = selected_throughput

"""Encryption"""
selected_encryption = config.encrypt_volume

"""Delete Volume on Termination"""
delete_on_term = config.delete_volume_on_termination

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
elif volume_type == 'gp2':
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
else:
    raise ValueError("Not a valid Volume Type")
#####################################################################################################################
#                                               Software Configurations                                             #
#####################################################################################################################
user_data, confirmed_software = create_userdata(toppings_selection=config.software_selections, custom_userdata=config.custom_userdata)
######################################################################################################################
#                                                  Create Security Group                                             #
######################################################################################################################
"""Get Existing Security Groups"""
existing_security_groups = ec2_client.describe_security_groups()
existing_vpcs = ec2_client.describe_vpcs().get('Vpcs', [{}])[0]['VpcId']
sg_existing_list = []

if config.use_existing_security_group:
    for i in existing_security_groups['SecurityGroups']:
        sg_existing_list.append(i['GroupName'])
    existing_sg = config.existing_security_group_name
    sg_selection = sg_existing_list.index(existing_sg)
    security_group_id = existing_security_groups['SecurityGroups'][sg_selection]['GroupId']

elif not config.use_existing_security_group:
    external_ip = get_external_ip()
    """Name Security Group"""
    security_group_name = f'mml-sg-0{secrets.token_hex(4)}'
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
        'IpRanges': [{'CidrIp': f'{external_ip}/32'}]
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

    try:
        choose_base_rules = config.strict_or_relaxed.lower()
        if choose_base_rules == 'relaxed':
            security_group_rules.append(rules[1][1])
        elif choose_base_rules == 'strict':
            security_group_rules.append(rules[2][1])
        else:
            raise ValueError('Not a valid base rule selection')
    except Exception:
        raise ValueError('Not a valid base rule selection')

    for i in confirmed_software:
        try:
            security_group_rules.append(software_rules[i])
        except Exception:
            security_group_rules = security_group_rules

    if config.add_more_rules:
        try:
            for i in config.custom_rule_list:
                custom_ip = i[0]
                port = i[1]
                security_group_rules.append(custom_sg_rule(port, custom_ip))
        except Exception:
            print(traceback.format_exc())
            raise ValueError("Invalid Custom Security Group Rules")

    if config.add_trading_view_ips:
        tv_ips = ['52.89.214.238', '34.212.75.30', '54.218.53.128', '52.32.178.7']
        ports = [80, 443]
        for port in ports:
            for ip in tv_ips:
                security_group_rules.append(customtv_sg_rule(port, ip))

    # Create Security Group
    description = f'{security_group_name} created by the MML Auto-EC2x on {datetime.now()}'
    response = ec2_client.describe_vpcs()
    vpc_id = response.get('Vpcs', [{}])[0]['VpcId']
    try:
        # Create Security Group
        response = ec2_client.create_security_group(GroupName=security_group_name,
                                                    Description=description,
                                                    VpcId=vpc_id,
                                                    DryRun=dry_run)
        security_group_id = response['GroupId']

        # Add self to security group rules
        add_self = {
            'IpProtocol': '-1',
            'FromPort': -1,
            'ToPort': -1,
            'UserIdGroupPairs': [{
                'GroupId': security_group_id
            }]
        }
        security_group_rules.append(add_self)

        # Set Ingress Rules
        data = ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=security_group_rules,
            DryRun=dry_run
        )

    except Exception:
        print(traceback.format_exc())
        raise RuntimeError("Error creating Security Group, check configs")
        pass
######################################################################################################################
#                                               Create KeyPair                                                       #
######################################################################################################################
"""Create Key Pair"""
if config.create_keypair:
    key_name = f'keypair_{secrets.token_hex(2)}'
    key = ec2_client.create_key_pair(KeyName=key_name, KeyType='rsa')
    with open(f'{key_name}.pem', 'w') as file:
        file.write(key['KeyMaterial'])
    key_pair_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), f'{key_name}.pem')
    """Check if path has spaces, if there are spaces - add quotes, if not - keep unquoted"""
    if " " in key_pair_location:
        key_pair_location = key_pair_location.replace("'", "")
        key_pair_location = f'"{key_pair_location}"'
    else:
        key_pair_location = key_pair_location
else:
    key_name = config.existing_key_name
    key_pair_location = key_name+'.pem'
######################################################################################################################
#                                               Create Instance                                                      #
######################################################################################################################
"""Create EC2 Instance"""
try:
    create_ec2_response = ec2_client.run_instances(
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

    # Get Instance ID
    instance_id = create_ec2_response["Instances"][0]['InstanceId']

    # Wait for Instance to Start
    ec2_resources = boto3.resource('ec2', region_name=selected_region)
    instance = ec2_resources.Instance(id=instance_id)
    instance.wait_until_running()

    # Reload Instance Details
    instance.reload()
    
except Exception:
    print(traceback.format_exc())
    raise RuntimeError("Error creating Instance, check configs")
######################################################################################################################
#                                                     Elastic IP                                                     #
######################################################################################################################
if config.use_elastic_ip:
    """Create Elastic IP"""
    try:
        allocate_elip = ec2_client.allocate_address(
        # Domain='vpc' or 'standard',
        Domain='vpc',
        # Address='string',
        # PublicIpv4Pool='string',
        # NetworkBorderGroup='string',
        # CustomerOwnedIpv4Pool='string',
        DryRun=dry_run,
        )
    except Exception:
        print(traceback.format_exc())
        raise RuntimeError("Error creating Elastic IP, check configs")
    public_ip = allocate_elip['PublicIp']

    """Associate Elastic IP"""
    while True:
        try:
            associate_elip = ec2_client.associate_address(
            InstanceId=instance_id,
            PublicIp=public_ip,
            # AllocationId=None,
            # NetworkInterfaceId=None,
            # PrivateIpAddress=None,
            AllowReassociation=False,
            DryRun=dry_run
            )
            break
        except Exception:
            print(traceback.format_exc())
            raise RuntimeError("Error associating Elastic IP, check configs")
else:
    public_ip = instance.public_dns_name
######################################################################################################################
#                                                 Create JSON Response                                               #
######################################################################################################################
run_time = "{:.2f}".format((time.time() - start_time)/60)
save_date = datetime.now().strftime("%m%d%y_%I%M")

if config.create_readme:
    file_name = f'Auto-EC2x_Summary_{save_date}.txt'
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
        f"IPv4 address: {public_ip} \n"
        f"------------------------------------ \n"
        f"Thank you for using the MML Auto-EC2 Generator! We hope you liked this MML open source offering, if you "
        f"have any questions or just want to chat - join us on discord: https://discord.gg/jjDcZcqXWy! \n"
        f"To support our development, please consider subscribing at https://marketmakerlite.com/subscribe \n"
        )
    readme_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name)
######################################################################################################################
#                                                 Exit Message                                                       #
######################################################################################################################
# Wait for userdata script to finish
time.sleep(15)

# Get number of software installs to approximate runtime of userdata scripts
if config.software_selections is not None:
    wait_multiplier = config.software_selections.replace(', ', '')
    wait_multiplier = len(list(wait_multiplier))
else:
    wait_multiplier = 1
# Adjust wait time
if wait_multiplier < 1:
    wait_multiplier = 1
if wait_multiplier > 8:
    wait_multiplier = 8
# Wait
time.sleep(30*wait_multiplier)

# Wait for restart
time.sleep(15)

# Print Response to indicate success
response = {
    "instance_url": f'https://{selected_region}.console.aws.amazon.com/ec2/v2/home?region={selected_region}#InstanceDetails:instanceId={instance_id}',
    "ssh": f'ssh -i {key_pair_location} ubuntu@{public_ip}',
    "Region": selected_region,
    "Instance type": selected_type,
    "Subnet": selected_subnet,
    "Root volume details": block_device_mappings,
    "ip_address": public_ip,
    "runtime": run_time,
    "time completed": save_date
}
response = json.loads(json.dumps(response))
print(response)
