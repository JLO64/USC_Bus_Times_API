import json, datetime

def lambda_handler(event, context):
    if 'requestContext' in event:
        userinfo = event["requestContext"]["http"]
        print("userAgent: {}".format(userinfo["userAgent"]))
        print("sourceIp: {}".format(userinfo["sourceIp"]))

    if event['queryStringParameters']['requestType'] == "returnLocations":
        return return_locations()

    elif event['queryStringParameters']['requestType'] == "returnTime":
        currenttime = ""
        if 'time' in event['queryStringParameters']: currenttime = event['queryStringParameters']['time']
        else: currenttime = get_current_time()

        datetocheck = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8)))
        if 'date' in event['queryStringParameters']:
            datetocheck = datetime.datetime.strptime(event['queryStringParameters']['date'], '%m/%d/%y')
        
        if 'Stop' in event['queryStringParameters']:
            return return_stop_times(event['queryStringParameters']['Route'], event['queryStringParameters']['Stop'], currenttime, datetocheck)
        elif 'Subroute' in event['queryStringParameters']:
            return return_subroute_times(event['queryStringParameters']['Route'], event['queryStringParameters']['Subroute'], currenttime, datetocheck)

#        return return_times(event['queryStringParameters']['Departure'], event['queryStringParameters']['Destination'], currenttime, datetocheck)

    else:
        return {
            "statusCode": 200,
            "body": json.dumps("Please enter a valid requestType")
        }

def return_stop_times(route, stop, timetocheck, datetocheck):
#stop is the departure
    data = import_json()

    arrayoftimes = []

    day = datetocheck.weekday()
    if day < 5: schedule = "weekdays"
    else: schedule = "weekends"

    for entry in data:
        if entry["Route"] == route and entry["Departure"] == stop:
            if not schedule in entry: arrayoftimes = []
            else: arrayoftimes = entry[schedule]["Times"]

    string_to_return = makeresponseString(arrayoftimes, timetocheck, datetocheck, stop, route, routetype="stop")
    
    print("response: " + string_to_return)

    return {
        "response": string_to_return
    }

def return_subroute_times(route, subroute, timetocheck, datetocheck):
    return True

def return_times(departure, destination, timetocheck, datetocheck):
    arrayoftimes = (get_route_times(departure, destination, datetocheck.weekday()))

    string_to_return = makeresponseString(arrayoftimes, timetocheck, datetocheck, departure, destination)

    print("response: " + string_to_return)

    return {
        "response": string_to_return
    }

def import_json():
    #import the json file bus-times.json
    with open('bus-times.json') as json_file:
        data = json.load(json_file)
        return data

def get_route_times(daytocheck, Route, Departure, Destination=None):
    data = import_json()
    day = daytocheck
    if day < 5: schedule = "weekdays"
    else: schedule = "weekends"
    for route in data:
        if route["Departure"] == Departure and route["Destination"] == Destination:
            if not schedule in route: return []
            else: return route[schedule]["Times"]

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
    data = import_json()
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

def makeresponseString(arrayoftimes,timetocheck, datetocheck, departure, destination, routetype):
    string_to_return = ""

    endingofResponseString = " from " + departure + " to " + destination + " today."
    if datetocheck.weekday() != datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8))).weekday():
        endingofResponseString = " from " + departure + " to " + destination + " on " + datetocheck.strftime("%A, %B %d") + "."
    

    if len(arrayoftimes) == 0:
        return "There are no buses running" + endingofResponseString

    index = get_index_of_nearest_time(arrayoftimes, timetocheck)

    if index == len(arrayoftimes) - 1:
        string_to_return = "The next bus is at " + str(convert_to_twelve_hour_time(arrayoftimes[index]))
    elif index == len(arrayoftimes):
        string_to_return = "There are no more buses"
    else:
        string_to_return = "The next bus is at " + str(convert_to_twelve_hour_time(arrayoftimes[index])) + " and the one after that is at " + str(convert_to_twelve_hour_time(arrayoftimes[index + 1]))

    return string_to_return + endingofResponseString

if __name__ == "__main__":
    print(return_locations())
    #print(lambda_handler({
    #    "queryStringParameters": {
    #        "requestType": "returnTime",
    #        "Departure": "Jefferson",
    #        "Destination": "HSC",
    #        "time": "11:30",
    #        "date": "1/27/23"
    #    }
    #}, None))

## TODO: Add twitter notifications
## TODO: Add multi language support
## TODO: Redo the shortcuts interface
## TODO: Create an alarm when using date and time