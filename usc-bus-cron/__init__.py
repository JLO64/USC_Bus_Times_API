import requests, datetime, openai, json, os, tempfile, logging
import snscrape.modules.twitter as sntwitter
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import azure.functions as func
from dotenv import load_dotenv

def querry_openai(bus_announcements_string):
	#print("not querrying openai")
	#return "test"
	print("querrying openai")
	bus_announcements_instructions = "Compress this text by removing apologies, greetings, and farewells. If the text is less than 20 characters, DO NOT modify."
	#test_instructions = "Compress this text. If the text is less than 20 characters, DO NOT modify."

	response = openai.Edit.create(
		model="text-davinci-edit-001",
		input=bus_announcements_string,
		temperature=0.3,
		instruction=bus_announcements_instructions,
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

def main(mytimer: func.TimerRequest) -> None:
	#set the environment variable ENVIRONMENT to "development" if you want to run this locally
	try:
		if ( os.environ['ENVIRONMENT'] == 'development'):
			#this is for PST (on local machine)
			currenttime = datetime.datetime.now()
		else:
			#this is for UTC-PST (on azure)
			currenttime = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8)))
	except:
		#this is for UTC-PST (on azure)
		currenttime = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8)))

	twitter_account_to_scrape = "uscmoves"

	#import keys.json
	with open("bin/keys.json", "r") as file:
		keys = json.loads(file.read())
	openai.api_key = keys["openai_key"]

	twitter_json_response = get_tweets(currenttime, twitter_account_to_scrape)
	todays_twitter_json_filename = f"{currenttime.strftime('%Y-%m-%d')}" + "_" + twitter_account_to_scrape + ".json"
	todays_twitter_json_filepath = tempfile.gettempdir() + "/" + todays_twitter_json_filename

	azure_blob_service_client = BlobServiceClient(account_url="https://{}.blob.core.windows.net".format(keys["azure_account_name"]), credential=keys["azure_account_key"])
	blob_client = azure_blob_service_client.get_blob_client(container=keys["azure_container_name"], blob=todays_twitter_json_filename)

	try:
		# download the json file from azure
		with open(todays_twitter_json_filepath, "wb") as my_blob:
			blob_data = blob_client.download_blob()
			blob_data.readinto(my_blob)
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

	#upload the json file to azure
	with open(todays_twitter_json_filepath, "rb") as data:
		blob_client.upload_blob(data, overwrite=True)

if __name__ == "__main__":
	main()

#cron expression for azure function timer trigger: everyday, every 30 minutes, bwtween 5am and 10pm
#0 */30 5-22 * * *
#(above is for PST, below is for UTC)
#0 */30 13-06 * * *
#0 */30 0-6,13-23 * * *