import logging
import json
import datetime

import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    if req.params.get('requestType') == "returnLocations":
        return func.HttpResponse(json.dumps(return_locations()), mimetype="application/json")
    elif req.params.get('requestType') == "returnTime":
        currenttime = ""
        if 'time' in req.params:
            currenttime = req.params.get('time')
        else: currenttime = get_current_time()

        datetocheck = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8)))
        if 'date' in req.params:
            datetocheck = datetime.datetime.strptime(req.params.get('date'), '%m/%d/%y')

        if 'Stop' in req.params:
            return func.HttpResponse(json.dumps(return_stop_times(req.params.get('Route'), req.params.get('Stop'), currenttime, datetocheck)), mimetype="application/json")
        elif 'Subroute' in req.params:
            return func.HttpResponse(json.dumps(return_subroute_times(req.params.get('Route'), req.params.get('Subroute'), currenttime, datetocheck)), mimetype="application/json")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
    
# write an example http request to test this function. route is "Alhambra Shuttle", subroute is "HSC to Alhambra", time is "12:00", date is "2/14/23"
# https://usc-bus-api.azurewebsites.net/api/HttpTriggerPython?requestType=returnTime&Route=Alhambra%20Shuttle&Subroute=HSC%20to%20Alhambra&time=12:00&date=2/14/23


def return_stop_times(route, stop, timetocheck, datetocheck):
    data = import_json_from_local()

    arrayoftimes = []

    day = datetocheck.weekday()
    if day < 5: schedule = "weekdays"
    else: schedule = "weekends"

    for entry in data:
        if entry["Route"] == route and entry["Departure"] == stop:
            if not schedule in entry: arrayoftimes = []
            else: arrayoftimes = entry[schedule]["Times"]

    string_to_return = makeresponseString(arrayoftimes, timetocheck, datetocheck, [route, stop], routetype="stop")
    
    print("response: " + string_to_return)

    return {
        "response": string_to_return
    }

def return_subroute_times(route, subroute, timetocheck, datetocheck):
    data = import_json_from_local()

    arrayoftimes = []

    day = datetocheck.weekday()
    if day < 5: schedule = "weekdays"
    else: schedule = "weekends"

    departure = subroute.split(" to ")[0]
    destination = subroute.split(" to ")[1]

    for entry in data:
        if entry["Route"] == route and entry["Departure"] == departure and entry["Destination"] == destination:
            if not schedule in entry: arrayoftimes = []
            else: arrayoftimes = entry[schedule]["Times"]

    string_to_return = makeresponseString(arrayoftimes, timetocheck, datetocheck, [departure, destination], routetype="subroute")
    
    print("response: " + string_to_return)

    return {
        "response": string_to_return
    }

def import_json_from_s3():
    s3 = boto3.client("s3")

    bucket_name = "usc-bus-data"
    object_key = "bus-times.json"

    obj = s3.get_object(Bucket=bucket_name, Key=object_key)
    json_file = obj["Body"].read().decode("utf-8")

    json_data = json.loads(json_file)
    return json_data

def import_json_from_local():
    with open("bin/bus-times.json") as json_file:
        json_data = json.load(json_file)
        return json_data

def get_index_of_nearest_time(timesarray, currenttime):
    currenthour = int(currenttime.split(":")[0])
    currentminute = int(currenttime.split(":")[1])
    
    index = 0
    for arraytime in timesarray:
        arrayhour = int(arraytime.split(":")[0])
        arrayminute = int(arraytime.split(":")[1])

        if arrayhour == currenthour:
            if arrayminute >= currentminute: return index
        elif arrayhour > currenthour: return index
        index += 1
    return len(timesarray)

def get_current_time():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8))).strftime("%H:%M")

def convert_to_twelve_hour_time(timestr):
    return datetime.datetime.strptime(timestr, '%H:%M').strftime('%I:%M %p')

def return_locations():
    data = import_json_from_local()
    result = {}
    for entry in data:
        route = entry['Route']
        if route not in result:
            if 'Destination' in entry:
                result[route] = {'Subroutes': []}
            else:
                result[route] = {'Stops': []}
        if 'Destination' in entry:
            result[route]['Subroutes'].append(entry['Departure'] + " to " + entry['Destination'])
        else:
            result[route]['Stops'].append(entry['Departure'])
    return result

def makeresponseString(arrayoftimes, timetocheck, datetocheck, routearray, routetype):
    string_to_return = ""

    endingofResponseString = ""
    if routetype == "stop":
        endingofResponseString = " from the " + routearray[1] + " stop on the " + routearray[0]
    elif routetype == "subroute":
        endingofResponseString = " from " + routearray[0] + " to " + routearray[1]
        
    if datetocheck.strftime("%m/%d/%Y") != datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8))).strftime("%m/%d/%Y"):
        endingofResponseString += " on " + datetocheck.strftime("%A, %B %d") + "."
    else:
        endingofResponseString += " today."

    if len(arrayoftimes) == 0:
        return "There are no buses running" + endingofResponseString

    index = get_index_of_nearest_time(arrayoftimes, timetocheck)

    if index == len(arrayoftimes) - 1:
        string_to_return = "The next bus is at " + str(convert_to_twelve_hour_time(arrayoftimes[index]))
    elif index == len(arrayoftimes):
        string_to_return = "There are no more buses"
    else:
        string_to_return = "The next bus is at " + str(convert_to_twelve_hour_time(arrayoftimes[index])) + " and the one after that is at " + str(convert_to_twelve_hour_time(arrayoftimes[index + 1]))

    return string_to_return + endingofResponseString + get_tweets()

def get_tweets():
    try:
        s3 = boto3.client("s3")

        currentdate = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8)))

        bucket_name = "usc-bus-data"
        object_key = f"twitter-announcements/{currentdate.strftime('%Y-%m-%d')}.json"

        obj = s3.get_object(Bucket=bucket_name, Key=object_key)
        json_file = obj["Body"].read().decode("utf-8")
        json_data = json.loads(json_file)

        string_to_return = "\n\nUSC Bus Twitter Announcements: "
        for i in json_data:
            string_to_return +=  "\n-" + i["openai"]

        return string_to_return
    except:
        return ""