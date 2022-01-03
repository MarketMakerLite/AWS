# -----------------------------
# MML AutoEC2 configuration file
# -----------------------------

# This file consists of lines of the form:
#   name = value

# (The "=" is optional.)  Whitespace may be used.  Comments are introduced with
# "#" anywhere on a line.  The complete list of parameter names and allowed
# values can be found in the MML AutoEC2 documentation.

# A list of software and the corresponding choice numbers is listed below:
# [1: 'Postgres', 2: 'MongoDB', 3: 'MySQL', 4: 'sqlite3', 5: 'Redis', 6: 'Docker',
# 7: 'Git', 8: 'Nginx', 9: 'Caddy', 10: 'Apache', 11: 'NodeJS', 12: 'Airflow']

# You can add custom userdata in the following format:
# custom_userdata = '''#
# apt -y update
# apt -y upgrade
# #
# #Install pip
# apt install python3-pip
# '''

################################################################################
# GENERAL / CONNECTIONS
################################################################################
dry_run = False                                                 # Set to True for testing, False for production.
access_key_id = 'BRLO5fXXXXXRZV843HJ9'                          # Replace with your Access Key ID
secret_access_key = 'K3FH68epXXXXXlLT7hYtMfr4nXFWsB5zKSipLZWy'  # Replace with your Secret Access Key
create_readme = True
###############################################################################
# INSTANCE SETTINGS
###############################################################################
use_default_region = True
selected_region = 'us-east-2'
instance_type = 't2.micro'
subnet_zone = 'b'                                               # Choices: a-c
use_elastic_ip = False
###############################################################################
# VOLUME SETTINGS
###############################################################################
volume_type = 'gp3'                                             # Options: 'gp3', 'gp2', 'io2', io1'
volume_size = '8 GB'                                            # Range: 8 GB - 16 TB
volume_iops = 3000                                              # Values: 'gp3': [3000, 16000], 'io1': [100, 5000], 'io2': [100, 100000] where ['min, 'max']
volume_throughput = 125
delete_volume_on_termination = True
encrypt_volume = False
###############################################################################
# SOFTWARE SETTINGS
###############################################################################
software_selections = '1, 5, 7, 9'                              # Enter choices in comma separated list string, or 'all' to install all options
custom_userdata = None
###############################################################################
# SECURITY GROUP SETTINGS
###############################################################################
use_existing_security_group = False
existing_security_group_name = 'sg_name'
strict_or_relaxed = 'strict'                                    # "relaxed": Allows all connections (0.0.0.0), "strict": Allows connections only from your IP
add_trading_view_ips = True
add_more_rules = False
custom_rule_list = [['0.0.0.0', 80], ['0.0.0.0', 443]]          # Structure: List of Lists. IP Format: 0.0.0.0. Port Format: ##.
###############################################################################
# KEYPAIR SETTINGS
###############################################################################
create_keypair = False
existing_key_name = 'keypair'                                   # Don't include .pem, just type the name here
