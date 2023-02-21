import requests, datetime, openai, json, os, tempfile
import snscrape.modules.twitter as sntwitter
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import azure.functions as func
from dotenv import load_dotenv

def import_openai_key():
    try:
        with open("bin/openai_key.txt", "r") as file:
            openai.api_key = file.read()
        print("openai key imported")
    except:
        print("no openai key file found")

def querry_openai(bus_announcements_string):
    #print("not querrying openai")
    #return "test"
    print("querrying openai")
    bus_announcements_instructions = "Compress this text by removing apologies, greetings, and farewells. If the text is less than 20 characters, DO NOT modify."
    test_instructions = "Compress this text. If the text is less than 20 characters, DO NOT modify."

    response = openai.Edit.create(
        model="text-davinci-edit-001",
        input=bus_announcements_instructions,
        temperature=0.4,
        instruction=test_instructions,
    )
    return response["choices"][0]["text"]

def get_tweets(current_day, account_name):
    print("getting tweets")
    today_tweets = []

    #if the following for loop takes langer than 10 seconds, end it and return the tweets that have been read

    # Scrape latest tweets from account_name posted since current_day with a delta of 1 day
    for i,tweet in enumerate(sntwitter.TwitterUserScraper(account_name).get_items()):
        if i>5:
            break
        #convert tweet.date which is in the format 2023-02-17 14:05:25+00:00 to datetime object
        tweet_date = datetime.datetime.strptime(tweet.date.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
        #convert tweet_date to PST
        pst_tweet_date = tweet_date - datetime.timedelta(hours = 8 )
        if pst_tweet_date.strftime("%m-%d-%Y") == current_day.strftime("%m-%d-%Y"):
            today_tweets.append({
                "text": tweet.rawContent,
                "date": str(pst_tweet_date),
                "id": tweet.id
            })

    return today_tweets

def upload_to_azure(filepath, blob_service_client):
    container_name = "twitter-announcements"
    #the file is stored in the temp directory of the machine
    filename = filepath.split("/")[-1]

    # check if there is a file within the container with the name of the file we are trying to upload
    # if there is, delete it
    #try:
    #    blob_client = blob_service_client.get_blob_client(container=container_name, blob=filename)
    #    blob_client.delete_blob()
    #    print("file deleted on azure container")
    #except:
    #    print("no file to delete")

    # upload the file to azure, but do not upload the folder structure
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=filename)
    with open(filepath, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    
    print("uploaded {} to azure".format(filename))

def get_azure_blob_service_client():
    account_name = "uscbusdata"

    # Acquire a credential object
    token_credential = DefaultAzureCredential()

    blob_service_client = BlobServiceClient(
        account_url="https://{}.blob.core.windows.net".format(account_name),
        credential=token_credential)

    return blob_service_client

def download_todays_json_from_azure(filename, blob_service_client):
    container_name = "twitter-announcements"

    # download the json file from azure
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=filename)
    with open(filename, "wb") as my_blob:
        blob_data = blob_client.download_blob()
        blob_data.readinto(my_blob)

def main(req: func.HttpRequest) -> func.HttpResponse:
    #set the environment variable ENVIRONMENT to "development" if you want to run this locally
    try:
        if ( os.environ['ENVIRONMENT'] == 'development'):
            #make sure that you have a .env file in the root directory of the project
            print("Loading environment variables from .env file")
            load_dotenv(".env")
            #this is for PST (on local machine)
            currenttime = datetime.datetime.now()
        else:
            #this is for UTC-PST (on azure)
            currenttime = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8)))
    except:
        #this is for UTC-PST (on azure)
        currenttime = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8)))

    if 'twitter_account' in req.params:
        twitter_account_to_scrape = req.params.get('twitter_account')
    else:
        twitter_account_to_scrape = "uscmoves"
        
    twitter_json_response = get_tweets(currenttime, twitter_account_to_scrape)
    import_openai_key()
    todays_twitter_json_filename = f"{currenttime.strftime('%Y-%m-%d')}" + "_" + twitter_account_to_scrape + ".json"
    todays_twitter_json_filepath = tempfile.gettempdir() + "/" + todays_twitter_json_filename
    azure_blob_service_client = get_azure_blob_service_client()

    try:
        download_todays_json_from_azure(todays_twitter_json_filepath, azure_blob_service_client)
        with open(f"{currenttime.strftime('%Y-%m-%d')}.json", "r") as outfile:
            saved_announcements_json = json.load(outfile)
        compare_old_announcements = True
    except:
        compare_old_announcements = False

    if compare_old_announcements:
        if len(twitter_json_response) == len(saved_announcements_json):
            print ("No new announcements")
            return func.HttpResponse("no new announcements from {}".format(twitter_account_to_scrape))
        else:
            if len(twitter_json_response) > 0:
                #for the nth object in twitter_json_response, compare it to the nth object in saved_announcements_json
                for i in range(len(twitter_json_response)):
                    if i in range(len(saved_announcements_json)):
                        if twitter_json_response[i]['id'] == saved_announcements_json[i]['id']:
                            twitter_json_response[i]['openai'] = saved_announcements_json[i]['openai']
                            #print("match")
                    else:
                        twitter_json_response[i]['openai'] = querry_openai(twitter_json_response[i]['text'])
                        #print("openai")          
    else:
        if len(twitter_json_response) > 0:
            for i in twitter_json_response:
                i['openai'] = querry_openai(i['text'])
        else:
            return func.HttpResponse("no announcements today from {}".format(twitter_account_to_scrape))
    
    with open(todays_twitter_json_filepath, "w") as outfile:
        json.dump(twitter_json_response, outfile)
    
    upload_to_azure(todays_twitter_json_filepath, azure_blob_service_client)

    #return the data in twitter_json_response
    return func.HttpResponse(json.dumps(twitter_json_response))

if __name__ == "__main__":
    main()