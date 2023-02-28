# USC_Bus_Times_API

## Description

This v2 of the code for an API that provides the bus times for the University of Southern California. It checks the USC transportation twitter account (uscmoves) periodically and updates the bus times accordingly using OpenAI's Davinci model. The API is written in Python and is meant to be hosted on Azure Functions. However, it can be hosted on any server/serverless platform that supports Python.

## iOS Shortcuts

### Links to Download Shortcuts

### How to Use

If you want to use these shortcuts, all you have to do is download them from the links above. Then you can activate them either through the shortcuts app, the shortcuts widget or through Siri.

Both shortcuts will ask you for departure and destination bus stops. However the "On this date when is the next USC bus?" shortcut will also ask you to specify a time and date.

### Example Screenshot

## Azure Function API

### API URL

The API is hosted on AWS Lambda and can be accessed at the following URL:

```https://usc-bus-api.azurewebsites.net```

### How to Use the API

#### Getting Locations

#### Getting Bus Times

## Contributing to the List of Busses

Feel free to add to the list of busses in the ```bin/bus-list.json``` file. [This is the website that I'm sourcing the times from.](https://transnet.usc.edu/index.php/bus-map-schedules/) The format is as follows:

```json
{
        "Departure":"Union Station",
        "Destination":"HSC",
        "weekdays": {
            "Times":["6:08","6:23"..."21:40"]
        },
        "weekends": {
            "Times":["8:45","10:10"..."16:10"]
        }
    }
```

In the future I plan to automate this process with a web scraper/openai model.