
import math
import dateutil.parser
import datetime
import time
import os
import logging
import boto3


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Get the service resource
sqs = boto3.resource('sqs', region_name='us-east-1')
queue = sqs.get_queue_by_name(QueueName='dining_orders')

def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

""" --- Helper Functions --- """

def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')
        
def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def validate_dining(location, cuisine, date, time, people, phone_no):   

    location_list = ['new york', 'manhattan', 'california', 'texas']
    if location is not None and location.lower() not in location_list:
        return build_validation_result(False,
                                    'Location',
                                    "We've just got started. Our service is limited to just a few places like Manhattan, California and Texas")
        
    cuisine_list = ['indian','chinese','italian', 'mexican', 'japanese', 'thai', 'french', 'asian', 'spanish']
    if cuisine is not None and cuisine.lower() not in cuisine_list:
        return build_validation_result(False,
                                    'Cuisine',
                                    'We do not support {}, would you like to try another cuisine? '
                                    'My personal favourite is Chinese'.format(cuisine))
                                    
    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(False, 'Date', 'I did not understand that, what date would you like to dine out?')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'Date', 'I wish I could go back in time. For now, pick another date')
    
    if time is not None:
        if len(time) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'Time', None)

        hour, minute = time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'Time', "I did not understand that, what time?")
        
        if hour < 10 or hour > 22:
            # Outside of business hours
            return build_validation_result(False, 'Time', 'Most business hours are from 10 AM to 10 PM. Can you specify a time during this range?')
            
        if datetime.datetime.strptime(date, '%Y-%m-%d').date() == datetime.date.today():
            now = datetime.datetime.now()
            if hour < now.hour:
                return build_validation_result(False, 'Time', 'I wish I could go back in time. For now, pick another time')
            if hour == now.hour and minute < now.minute:
                return build_validation_result(False, 'Time', 'I wish I could go back in time. For now, pick another time')
                
        
    
    if people is not None:
        if parse_int(people) <=0:
            return build_validation_result(False,
                                            'People',
                                            "Take some real friends with you!")
    
    if phone_no is not None:
        if len(phone_no) != 10:
            return build_validation_result(False,
                                            'Phone_No',
                                            'That aint no US number')
    
    return build_validation_result(True,None,None)


def dining_suggestion(intent_request):
    location = get_slots(intent_request)["Location"]
    cuisine = get_slots(intent_request)["Cuisine"]
    date = get_slots(intent_request)["Date"]
    time = get_slots(intent_request)["Time"]
    people = get_slots(intent_request)["People"]
    phone_no = get_slots(intent_request)["Phone_No"]
    source = intent_request['invocationSource']
    
    
    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_dining(location, cuisine, date, time, people, phone_no)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])
    
    
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        return delegate(output_session_attributes, get_slots(intent_request))
    
    # Create a message
    body = location + ";" + cuisine + ";" + phone_no
    response = queue.send_message(MessageBody=body)
    
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': "You’re all set. Expect my recommendations shortly!"})
    

def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'DiningSuggestionsIntent':
        return dining_suggestion(intent_request)
    
    raise Exception('Intent with name ' + intent_name + ' not supported')

""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
