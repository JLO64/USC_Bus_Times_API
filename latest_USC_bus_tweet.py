import requests
import datetime

# To set your environment variables in your terminal run the following line:
# export 'BEARER_TOKEN'='<your_bearer_token>'
bearer_token = "AAAAAAAAAAAAAAAAAAAAAEd7lgEAAAAAaUg1ia1kOiJPP64jm%2BAikra2WeE%3DiziOG9NqyRIfcB4x5791cY8catB13ukZfH2ddiU2ixjk9axEZT"

search_url = "https://api.twitter.com/2/tweets/search/recent"

# Optional params: start_time,end_time,since_id,until_id,max_results,next_token,
# expansions,tweet.fields,media.fields,poll.fields,place.fields,user.fields

start_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8))).replace(hour=1, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

query_params = {'query': '(from:USCmoves -is:retweet) OR #USCmoves','tweet.fields': 'author_id', 'start_time': start_time}


def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """

    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2RecentSearchPython"
    return r

def connect_to_endpoint(url, params):
    response = requests.get(url, auth=bearer_oauth, params=params)
    print(response.status_code)
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()


def get_tweets():
    usc_bus_announcements = []
    bus_announcements_string = ""

    json_response = connect_to_endpoint(search_url, query_params)
    for i in json_response['data']:
        usc_bus_announcements.append("\n-" + i['text'])

    if len(usc_bus_announcements) > 0:
        bus_announcements_string = "\n\nToday's USC Bus Announcements:" + " ".join(usc_bus_announcements)
    else:
        bus_announcements_string = ""

    return(bus_announcements_string)

if __name__ == "__main__":
    print(get_tweets())
