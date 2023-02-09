import requests, datetime, openai, json
try:
    import boto3
    isLambda = True
except: 
    isLambda = False

if isLambda:
    s3 = boto3.client("s3")

    bucket_name = "usc-bus-data"
    object_key = "twitter-keys.json"

    obj = s3.get_object(Bucket=bucket_name, Key=object_key)
    json_file = obj["Body"].read().decode("utf-8")

    json_data = json.loads(json_file)
else:
    with open("twitter-keys.json") as f:
        json_data = json.load(f)

bearer_token = json_data['twitter-Bearer-Token']
openai.api_key = json_data['openAI-API-Key']


search_url = "https://api.twitter.com/2/tweets/search/recent"

#corrects UTC time to PST
start_datetime = datetime.datetime.now() - datetime.timedelta(hours = 8 )
start_datetime = start_datetime.replace(hour=1, minute=0, second=0, microsecond=0)
start_time = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

twitter_query_params = {'query': '(from:USCmoves -is:retweet) OR #USCmoves','tweet.fields': 'author_id', 'start_time': start_time}

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

def querry_openai(bus_announcements_string):
    response = openai.Edit.create(
        model="text-davinci-edit-001",
        input=bus_announcements_string,
        temperature=0.4,
        instruction="Compress this text by removing apologies, greetings, and farewells."
    )
    return response["choices"][0]["text"]

def main():
    if isLambda:
        try:
            #the file name is the date of the day and it is stored in the folder "twitter-announcements"
            obj = s3.get_object(Bucket=bucket_name, Key=f"twitter-announcements/{start_datetime.strftime('%Y-%m-%d')}.json")
            saved_announcements_json = json.loads(obj["Body"].read().decode("utf-8"))
            compare_old_announcements = True
        except:
            compare_old_announcements = False
    else:
        try:
            with open(f"{start_datetime.strftime('%Y-%m-%d')}.json", "r") as outfile:
                saved_announcements_json = json.load(outfile)
                compare_old_announcements = True
        except:
            compare_old_announcements = False
            
    
    twitter_json_response = connect_to_endpoint(search_url, twitter_query_params)
    if compare_old_announcements:
        if len(twitter_json_response['data']) == len(saved_announcements_json):
            print ("No new announcements")
            return
        else:
            if 'data' in twitter_json_response:
                #for the nth object in twitter_json_response, compare it to the nth object in saved_announcements_json
                for i in range(len(twitter_json_response['data'])):
                    if twitter_json_response['data'][i]['id'] == saved_announcements_json[i]['id']:
                        twitter_json_response['data'][i]['openai'] = saved_announcements_json[i]['openai']
                    else:
                        twitter_json_response['data'][i]['openai'] = querry_openai(twitter_json_response['data'][i]['text'])
    else:
        if 'data' in twitter_json_response:
            for i in twitter_json_response['data']:
                i['openai'] = querry_openai(i['text'])
    
    if isLambda:
        s3.put_object(Bucket=bucket_name, Key=f"twitter-announcements/{start_datetime.strftime('%Y-%m-%d')}.json", Body=json.dumps(twitter_json_response['data']))
    else:
        with open(f"{start_datetime.strftime('%Y-%m-%d')}.json", "w") as outfile:
            json.dump(twitter_json_response['data'], outfile)

if __name__ == "__main__":
    print(main())

def lambda_handler(event, context):
    main()
