import sys
import argparse
import json
import requests
import time
import contextlib
from datetime import datetime
from datetime import timedelta
from os import getenv
from os.path import dirname, join

from dotenv import load_dotenv
load_dotenv(join(dirname(__file__), '.env'))

KEY = getenv('ZOOM_KEY')
SECRET = getenv('ZOOM_SECRET')
API_BASE_URL = "https://api.zoom.us/v1"
MEETING_TYPES = {"live": 1, "past": 2}

class ZoomApiException(Exception):
    pass

def get_meetings_from(date, type, key, secret):

    params = {
        'from': date,
        'to': date,
        'type': MEETING_TYPES[type],
        'api_key': key,
        'api_secret': secret,
        'page_size': 100,
        'page_number': 1
    }

    meetings = []
    while True:

        r = requests.post(url=API_BASE_URL + "/metrics/meetings", data=params)
        r.raise_for_status()
        response = r.json()

        if 'error' in response.keys():
            raise ZoomApiException(response['error'])

        for meeting in response['meetings']:
            meeting['type'] = response['type']
            meetings.append(meeting)

        print("total", type, "meetings:", response['total_records'])

        remaining_pages = response['page_count'] - response['page_number']

        if remaining_pages > 0:
            print("wait", remaining_pages, "more minute(s)")
            params['page_number'] += 1
            # only 1 zoom api metrics request allowed per minute
            time.sleep(60)
        else:
            break

    return meetings

@contextlib.contextmanager
def open_destination(destination=None):
    if destination == "-":
        fh = sys.stdout
    else:
        fh = open(destination, "w")
    try:
        yield fh
    finally:
        if fh is not sys.stdout:
            fh.close()

def main(args):

    try:
        with open_destination(args.destination) as fh:
            meetings = get_meetings_from(args.date, args.meeting_type, args.key, args.secret)
            json.dump(meetings, fh, indent=2)
    except OSError as e:
        print("Destination error: %s" % str(e))
    except requests.HTTPError as e:
        print("Error making API request: %s" % str(e))
    except ZoomApiException as e:
        print("The API returned an error response: %s", str(e))
    except KeyboardInterrupt:
        print("Quitting")

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--key", help="zoom api key", default=KEY)
    parser.add_argument("--secret", help="zoom api secret", default=SECRET)
    parser.add_argument("--date", help="fetch meetings from this date")
    parser.add_argument("--destination", help="destination filename", default="-")
    parser.add_argument("--meeting-type", help="get live or past meetings", default="past")
    args = parser.parse_args()

    if args.date is None:
        args.date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    main(args)


