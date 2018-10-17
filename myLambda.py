def query_handler(event, context): 

    query = event["messages"][0]["unstructured"]["text"]
    reply = ""
    if query == "Hello":
    	reply = "Hi there! How can I help?"
    else:
    	reply = "I don't understand that"

    return {
	  "messages": [
	    {
	      "type": "string",
	      "unstructured": {
	        "id": "1",
	        "text": reply,
	        "timestamp": "10/06"
	      }
	    }
	  ]
	}