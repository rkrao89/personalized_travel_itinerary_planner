import boto3
import time
from io import StringIO
#import pandas as pd
from configparser import ConfigParser
import json
import os
#import re

def get_data(user_id):
    config = ConfigParser()
    
#    config.read("/home/ec2-user/environment/core/data_feed_config.ini")
    config.read(os.path.join(os.path.dirname(__file__), 'data_feed_config.ini'))
    
    db_user = config["GLOBAL"]["db_user"]
    workgroup = config["GLOBAL"]["workgroup"]
    secarn = config["GLOBAL"]["secret_arn"]
    database = config["GLOBAL"]["database_name"]
    
    client = boto3.client('redshift-data', region_name = 'us-east-1')
    
    #print(f'{table_list}')
    tables = {}
    all_tables = ''
    
    #user_id = input("Enter User Id:")
    #user_id = "1028169"
    
    query = f"""
    select u.u_full_name as full_name, u.u_first_name as first_name, 
    u.u_age as age, u.u_city as home_city, u.u_country as home_country, u.u_interest as hobbies_interest, u.u_fav_food as favorite_food,
    b.b_city as travel_city, b.b_country as travel_country, b.b_checkin as from_date, b.b_checkout as to_date
    from travel.user_profile u
    join travel.booking_data b on b.b_user_id = u.u_user_id
    where u.u_user_id = {user_id}
    ORDER BY b.b_checkin;
    """
    
    execution_id = client.execute_statement(
        #ClusterIdentifier=cluster_id,
        Database=database,
        #DbUser=db_user,
        Sql=query,
        SecretArn=secarn,
        WorkgroupName=workgroup,
        )['Id']
    #print(f'Execution started with ID {execution_id}')
    
        # Wait for the query to be done
    status = client.describe_statement(Id=execution_id)['Status']
    while status not in ['FINISHED','ABORTED','FAILED']:
        time.sleep(10)
        status = client.describe_statement(Id=execution_id)['Status']
    #print(f'Schema Query Execution {execution_id} finished with status {status}')
    
    
    if status == 'FINISHED':
        columns = [c['label'] for c in client.get_statement_result(Id=execution_id)['ColumnMetadata']]
        records = client.get_statement_result(Id=execution_id)['Records']
        #print(f'Schema Query SUCCESS. Found {len(records)} records')
    else:
        print(f'Schema Query Failed with Error: {client.describe_statement(Id=execution_id)["Error"]}')
    
    # print(f'Columns: {columns}')
    # print(f'records: {records}')
    user_full_name = records[0][0]["stringValue"]
    user_first_name = records[0][1]["stringValue"]
    user_age = records[0][2]["longValue"]
    user_home_city = records[0][3]["stringValue"]
    user_home_country = records[0][4]["stringValue"]
    user_interests = records[0][5]["stringValue"]
    user_fav_food = records[0][6]["stringValue"]
    # print(f'full_name: {user_full_name}')
    # print(f'user_first_name: {user_first_name}')
    # print(f'user_age: {user_age}')
    # print(f'user_home_city: {user_home_city}')
    # print(f'user_home_country: {user_home_country}')
    # print(f'user_interests: {user_interests}')
    # print(f'user_fav_food: {user_fav_food}')
    
    travel_itinerary = ''
    
    for rec in records: 
        travel_city = rec[7]["stringValue"]
        travel_country = rec[8]["stringValue"]
        from_date = rec[9]["stringValue"]
        to_date = rec[10]["stringValue"]
        travel_string = travel_city + ", " + travel_country + " from " + from_date + " to " + to_date + " \\n"
        #print(f'{travel_string}')
        travel_itinerary = travel_itinerary + travel_string
    
    #print(f'{travel_itinerary}')
    
    prompt_initial_text = "You are a Personalized travel itinerary planner who can plan the itinerary by using the user\'s personal data like home city, age, hobbies, interests and favorite food. Date format is YYYY-MM-DD \\n"
    
    user_intro_text = str(user_full_name) + " who is of age " + str(user_age) + " , lives in " + str(user_home_city) + ", " + str(user_home_country) + " has hobbies or is interested in " + str(user_interests) +". " + str(user_first_name) + "\'s favorite food is " + str(user_fav_food) + ".\\n"
    
    travel_itinerary_text = "Below are the list of cities " + str(user_first_name) + " will travel to. \\n" + str(travel_itinerary)
    
    prompt_end_text = "Can you plan an itinerary with the above information? Please consider the hobbies, interests and favorite food listed above while planning this itinerary. \\n"
    addtl_instructions = "Start your response with Hello "+str(user_first_name) 
    
    prompt_text = prompt_initial_text+user_intro_text+travel_itinerary_text+prompt_end_text+addtl_instructions
    prompt_text = prompt_initial_text+user_intro_text+travel_itinerary_text+prompt_end_text +addtl_instructions
    
    prompt_text = prompt_text.replace('"', '\\"')
    
    #print(f'{prompt_text}')
    
    body = "{\"prompt\":\"Human: " + prompt_text + "\\n\\n\\nAssistant:\",\"max_tokens_to_sample\":300,\"temperature\":1,\"top_k\":250,\"top_p\":0.999,\"stop_sequences\":[\"\\n\\nHuman:\"],\"anthropic_version\":\"bedrock-2023-05-31\"}"
    
    #print(f'{body}')
    
    return body

def get_bedrock():
    
    bedrock = boto3.client(service_name='bedrock-runtime', region_name = 'us-east-1')

    return bedrock
    
def get_chat_response(input_text): #chat client function
    
    bedrock = get_bedrock()
    
    modelId = 'anthropic.claude-v2'
    accept = 'application/json'
    #accept  = "*/*"
    contentType = 'application/json'
    
    
    body = get_data(input_text)
    
    #print(body)
    
    model_response = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
    
    model_response_body = json.loads(model_response.get('body').read())
    
    
    chat_response = model_response_body.get("completion")
    
    return chat_response