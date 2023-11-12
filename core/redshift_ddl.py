import boto3
import time
from io import StringIO
#import pandas as pd
from configparser import ConfigParser
import json
import os

config = ConfigParser()
    
#config.read("/home/ec2-user/environment/core/data_feed_config.ini")
config.read(os.path.join(os.path.dirname(__file__), 'data_feed_config.ini'))
cluster_id = config["GLOBAL"]["cluster_id"]
db_user = config["GLOBAL"]["db_user"]
#workgroup = config["GLOBAL"]["workgroup"]
workgroup = "redshift-genai-wg-5eff2d70"
#secarn = config["GLOBAL"]["secret_arn"]
secarn = "arn:aws:secretsmanager:us-east-2:610113859777:secret:RedshiftServerlessSecret-Qev4NH"
database = config["GLOBAL"]["database_name"]
schema_name = config["GLOBAL"]["schema_name"]
table_list = config["GLOBAL"]["tables_to_be_fed_to_llm"].split(',')
client = boto3.client('redshift-data', region_name = 'us-east-2')

query = f"""
CREATE external SCHEMA ext_spectrum
FROM data catalog DATABASE 'hotelbookingdb'
IAM_ROLE default
CREATE external DATABASE if not exists
"""

execution_id = client.execute_statement(
        #ClusterIdentifier=cluster_id,
        Database=database,
        #DbUser=db_user,
        Sql=query,
        SecretArn=secarn,
        WorkgroupName=workgroup,
        )['Id']
print(f'Execution started with ID {execution_id}')

# Wait for the query to be done
status = client.describe_statement(Id=execution_id)['Status']
while status not in ['FINISHED','ABORTED','FAILED']:
    time.sleep(10)
    status = client.describe_statement(Id=execution_id)['Status']
print(f'Schema Query Execution {execution_id} finished with status {status}')