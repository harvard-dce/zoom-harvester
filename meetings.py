import argparse
import json
import requests
import time
from datetime import datetime
from datetime import timedelta
from os import getenv
from os.path import dirname, join

from dotenv import load_dotenv
load_dotenv(join(dirname(__file__), '.env'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", help="destination filename")
    args = parser.parse_args()

    KEY = getenv('ZOOM_KEY')
    SECRET = getenv('ZOOM_SECRET')
    FILENAME = args.destination
    MEETINGS = "https://api.zoom.us/v1/metrics/meetings"

    defaults = {
        'api_key': KEY,
        'api_secret': SECRET,
        'type': "2",
        'page_number': 1,
        'page_size': "300",
    }

    meeting_types = {
        'live': 1,
        'past': 2
    }

    destination = open(FILENAME, "w")

    def get_meetings_from(date, type):
        params = defaults.copy()
        params['from'] = date
        params['to'] = date
        params['type'] = meeting_types[type]

        while True:
            r = requests.post(url=MEETINGS, data=params)

            if r.status_code != requests.codes.ok:
                print("Failed with status code:", r.status_code, "reason:", r.reason)
                return

            response = json.loads(r.text)

            if 'error' in response.keys():
                print(response)
                return

            for meeting in response['meetings']:
                meeting['type'] = response['type']
                destination.write(str(meeting))

            print("total", type, "meetings:", response['total_records'])

            remaining_pages = response['page_count'] - response['page_number']

            if remaining_pages > 0:
                print("wait", remaining_pages, "more minute(s)")
                params['page_number'] += 1
                # only 1 zoom api metrics request allowed per minute
                time.sleep(60)
            else:
                break

    yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    get_meetings_from(yesterday, 'live')
    get_meetings_from(yesterday, 'past')

    destination.close()

if __name__ == '__main__':
    main()


