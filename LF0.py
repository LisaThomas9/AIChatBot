import datetime as dt
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('lex-runtime')

def lambda_handler(event, context):

    query = event["messages"][0]["unstructured"]["text"]
    reply = ""
    query = query.lower()
    
    logger.info("event {}".format(context))
    now = dt.datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    response = client.post_text(
                botName='MyChatBot',
                botAlias='v_one',
                userId='u007',
                inputText=query
                )
    #print(response['message'])
    reply = response['message']
    
    return {
	  "messages": [
	    {
	      "type": "string",
	      "unstructured": {
	        "id": "1",
	        "text": reply,
	        "timestamp": ts
	      }
	    }
	  ]
	}
	