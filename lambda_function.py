import json, datetime

def lambda_handler(event, context):
    if event['queryStringParameters']['requestType'] == "returnLocations":
        return {
            "locations": return_locations()
        }
    elif event['queryStringParameters']['requestType'] == "returnTime":
        currenttime = ""
        if 'time' in event['queryStringParameters']: currenttime = event['queryStringParameters']['time']
        else: currenttime = get_current_time()

        dayofweek = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8))).weekday()
        if 'date' in event['queryStringParameters']:
            #convert the date in a string format "1/26/23" to a weekday
            dayofweek = datetime.datetime.strptime(event['queryStringParameters']['date'], '%m/%d/%y').weekday()

        return return_times(event['queryStringParameters']['Departure'], event['queryStringParameters']['Destination'], currenttime, dayofweek)

def import_json():
    #import the json file bus-times.json
    with open('bus-times.json') as json_file:
        data = json.load(json_file)
        return data

def get_route_times(departure, destination, daytocheck):
    data = import_json()
    day = daytocheck
    if day < 5: schedule = "weekdays"
    else: schedule = "weekends"
    for route in data:
        if route["Departure"] == departure and route["Destination"] == destination:
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
    locations = []
    for route in data:
        if not any(location["name"] == route["Departure"] for location in locations):
            locations.append({
                "name": route["Departure"],
                "destinations": [route["Destination"]]
            })
        else:
            for location in locations:
                if location["name"] == route["Departure"]:
                    location["destinations"].append(route["Destination"])
    return locations

def return_times(departure, destination, timetocheck, daytocheck):
    arrayoftimes = (get_route_times(departure, destination, daytocheck))
    if len(arrayoftimes) == 0: return {
        "response": "There are no buses running today"
    }

    index = get_index_of_nearest_time(arrayoftimes, timetocheck)
    if index == len(arrayoftimes) - 1:
        return {
            "response": "The next bus is at " + str(convert_to_twelve_hour_time(arrayoftimes[index]))
        }
    elif index == len(arrayoftimes):
        return {
            "response": "There are no more buses today"
        }
    else:
        return {
            "response": "The next bus is at " + str(convert_to_twelve_hour_time(arrayoftimes[index])) + " and the one after that is at " + str(convert_to_twelve_hour_time(arrayoftimes[index + 1]))
        }

if __name__ == "__main__":
    print(lambda_handler({
        "queryStringParameters": {
            "requestType": "returnTime",
            "Departure": "Jefferson",
            "Destination": "HSC",
            "time": "21:00",
            "date": "1/28/23"
        }
    }, None))