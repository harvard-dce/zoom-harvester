# zoom-harvester

A python script for fetching Zoom meeting metadata using the Zoom API and loading data into Elasticsearch.

## Helpful Links

[Zoom API Documentation](https://zoom.github.io/api/)

[Zoom API Playground](https://developer.zoom.us/playground/)

## Usage

    usage: meetings.py [-h] [--key KEY] [--secret SECRET] [--date DATE]
                       [--destination {index,stdout}] [--es_host ES_HOST]

    optional arguments:
      -h, --help            show this help message and exit
      --key KEY             zoom api key; defaults to $ZOOM_KEY
      --secret SECRET       zoom api secret; defaults to $ZOOM_SECRET
      --date DATE           fetch meetings from this date, e.g. YYYY-mm-dd; defaults to yesterday.
      --destination {index,stdout}
                            destination filename; defaults to 'index'
      --es_host ES_HOST     Elasticsearch host:port; defaults to $ES_HOST
      --log_level {info,warn,debug}
                            set logging level; defaults to 'info'

##### Example to retrieve & index all meeting & participant data from yesterday.

`./meetings.py --key [KEY] --secret [SECRET] --es_host localhost:9200`

##### Using the `.env` file

To avoid entering key, secret, etc, on the command line copy `example.env` to `.env` in the
project directory and fill in the values. The script will load them into the environment at
runtime and use as the command line arg defaults.

## Terms

**`meeting_uuid`, `series_id`**

The zoom api uses "meeting id" to refer to ids for both an individual instance of a meeting and a series of meetings. These are two distinct types of ids. The zoom-harvester differentiates between the two.

- `meeting_uuid` 24 numbers, letters, and symbols uniquely refering to a meeting instance
- `series_id` 9 or 10 digits refering to a series of meetings

**`'type': 2`**

When calling /metrics/meetings, you must specify meeting type: 1(live) or 2(past). Live meetings are meetings that are currently happening and do not have an end time or duration yet. All live meetings become past meetings so meetings.py only searches for past meetings.

_**More notes on meetings ids:**_

Within the series_id, there can be several types:
- Most Common:
    * 9-digit ids tied to a repeating or scheduled series of meeting, such as a class that meets every Wednesday.
- Less Common:
    * 10-digit ids for PMIs (Personal Meeting Rooms) is a series id that an individual user can associate with their account so that every meeting that they host can be accessed with the same link in the format https://zoom.us/j/0123456789
    * 9-digit meeting ids not associated with a series of meetings or a PMI, these are instant meetings which will show up when you search for all the meetings over a period of time (/metrics/meetings/) but will not show up if you try to look them up individual (/meetings/get/)


**`user_id`**

Since only hosts have accounts, most of the time user_id refers to a host. Participants do not log in to join meetings, but the zoom api generates a `user_id` for each session. This `user_id` is not unique, it is only unique within a meeting instance.


**Sessions / participant sessions**

Each individual instance of a meeting participant entering and exiting a meeting. Can occur many times during the same meeting if, for example, the participant has a bad connection. Number of sessions for a given meeting does not equal the number of participants.


## API Calls

meetings.py runs all these calls in order to generate meeting objects with topics and host ids and participant sessions documents

| Call                       | Requires          | Returns |
| -------------------------- |:-----------------:| :-------            |
| /report/getaccountreport/  | date(s)           |  Active host information, including host ids.   |
| /meeting/list/             | host ids          |  Meeting series data including topic and series id.  |
| /metrics/meetings/         | date(s)           |  Meeting instance data, including unique meeting ids but not participant data. |
| /metrics/meetingdetail/    | meeting uuids |  All information from /metrics/meetings/ plus detailed participant data. |

## Development

A local development environment will need at least an instance of elasticsearch into which the zoom data can be indexed and inspected.
The easiest way to get a test instance of Elasticsearch running is via docker & docker-compose. 

### Setup

1. Install docker via the instructions for you OS at https://docker.com
1. Install docker-compose via `pip install docker-compose`

The `docker-compose.yml` config file will initialize two services: elasticsearch & kibana. To bring up the services run `docker-compose up`. The two containers will be started with their stdout directed to the console. To quit use `Ctrl+c`.

### kopf plugin

Kibana should be sufficient for browsing and searching indexes, but the kopf plugin can also be useful for performing operations on the cluster and getting additional details. The steps to install are:

1. In a separate terminal get the container id for the elasticsearch service by running `docker ps`.
1. Install the plugin via `docker exec -t -i [container-id] bin/plugin install lmenezes/elasticsearch-kopf`

The plugin should persist even after quitting the `docker-compose` process and then re-running `docker-compose up`. Should you remove the actual containers (e.g. `docker-compose down`) you will need to reinstall kopf.

Try indexing a document to make sure things are working

    curl -XPUT "http://localhost:9200/movies/movie/1" -d'
    {
        "title": "The Godfather",
        "director": "Francis Ford Coppola",
        "year": 1972
    }'
    
Go to [http://localhost:9200/_plugin/kopf]() to confirm that the `movies` index was created with 1 doc

Stop the container and start it again (remember to reinstall kopf), and check that the `movies` index is still there.

To delete the test `movies` index run `curl -XDELETE "http://localhost:9200/movies"`

### index templates

Index templates define the settings for newly created indexes that match a particular name pattern. They need to be created prior to any document indexing. Similar to ES plugins, they need to be recreated if/when the elasticsearch service container is ever removed.

To create the two index templates for the zoom data:

    curl -XPUT "http://localhost:9200/_template/sessions" -d @index_templates/sessions.json
    curl -XPUT "http://localhost:9200/_template/meetings" -d @index_templates/meetings.json
