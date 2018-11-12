import json
import boto3
import logging
from urllib.request import urlopen


# Initialize logger and set log level
logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.resource('sqs', region_name='us-east-1')
queue = sqs.get_queue_by_name(QueueName='dining_orders')

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('dining_suggestions')

# Initialize SNS client for Virginia region
session = boto3.Session(region_name="us-east-1")
sns_client = session.client('sns')


def lambda_handler(event, context):
    
    response = queue.receive_messages(MaxNumberOfMessages=10)
    logger.info("Triggered !!")
    
    for message in response:
        # Print out the body
        print('Message body : {}'.format(message.body))
        
        params = message.body.split(";")
        location = params[0]
        cuisine = params[1]
        phone_number = "+1" + params[2]
        #Call Google API
        contents = urlopen("https://maps.googleapis.com/maps/api/place/textsearch/json?query="+cuisine+"+restaurants+in+"
                    +location+"&key=AIzaSyB3npaZaiPppP_bb8H5UXRqc-d9xcU8jqE").read()
        jsonList = json.loads(contents)
        
        #Store in Dynamo DB
        suggestions = ""
        ctr = 1
        for restaurant in jsonList['results']:
            name = restaurant['name']
            addr = restaurant['formatted_address'].split(",")[0]
            response = table.put_item(
            Item={
                'user_id' : message.message_id+"-"+str(ctr),
                'restaurant_name' : name,
                'address' : addr,
                'rating' : round(restaurant['rating']),
                'cuisine' : cuisine
                }
            )
            suggestions += str(ctr)+". "+name+" at "+addr+" "
            ctr += 1
            if ctr == 3:
                break
        
        # Send message
        msg = "Hello! Here are my "+ cuisine+" restaurant suggestions for you. " + suggestions
        response = sns_client.publish(
            PhoneNumber=phone_number,
            Message=msg,
            MessageAttributes={
                'AWS.SNS.SMS.SenderID': {
                    'DataType': 'String',
                    'StringValue': 'DineOut'
                },
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Promotional'
                }
            }
        )
        
        #delete message from queue
        message.delete()
    
    
    
            
    