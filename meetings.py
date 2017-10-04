#!/usr/bin/env python

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
from elasticsearch import Elasticsearch

from dotenv import load_dotenv
load_dotenv(join(dirname(__file__), '.env'))

KEY = getenv('ZOOM_KEY')
SECRET = getenv('ZOOM_SECRET')
API_BASE_URL = "https://api.zoom.us/v1"
ES_HOST = getenv('ES_HOST')


class ZoomApiException(Exception):
    pass


def fetch_records(report_url, params, listkey, wait=1):
    params = params.copy()
    records = []
    print("get", report_url)

    while True:
        print("params", params)

        r = requests.post(url=API_BASE_URL + report_url, data=params)
        r.raise_for_status()
        response = r.json()

        if 'error' in response.keys():
            raise ZoomApiException(response['error'])

        [records.append(record) for record in response[listkey]]

        if 'total_records' in response.keys():
            if len(records) >= response['total_records']:
                break
        elif 'participants_count' in response.keys():
            if len(records) >= response['participants_count']:
                break

        time.sleep(wait)

        if response['page_number'] >= response['page_count']:
            break

        params['page_number'] += 1

    return records


def get_active_hosts(date):
    params = {
        'from': date,
        'to': date,
        'api_key': KEY,
        'api_secret': SECRET,
        'page_size': 300,  # max page size
        'page_number': 1
    }

    hosts = fetch_records("/report/getaccountreport", params, 'users')

    active_host_ids = [host['user_id'] for host in hosts]

    return active_host_ids


def get_series_info(host_ids):
    series_info = {}  # series ids mapped to topic and host id

    params = {
        'api_key': KEY,
        'api_secret': SECRET,
        'page_size': 300,  # max page size
        'page_number': 1
    }

    for host_id in host_ids:

        params['host_id'] = host_id

        series = fetch_records("/meeting/list", params, 'meetings')

        for meeting in series:
            key = meeting['id']
            series_info[key] = {'host_id': meeting['host_id'],
                                'topic': meeting['topic']}

        time.sleep(1)

    return series_info


def get_meetings(date, key, secret):
    es = Elasticsearch([ES_HOST])
    host_ids = get_active_hosts(date)
    series_info = get_series_info(host_ids)

    params = {
        'from': date,
        'to': date,
        'type': 2,  # completed meetings
        'api_key': key,
        'api_secret': secret,
        'page_size': 100,  # max page size
        'page_number': 1
    }

    meetings = fetch_records("/metrics/meetings", params, 'meetings', wait=60)  # 1 min rate limit

    for meeting in meetings:

        topic = ""
        host_id = ""

        series_id = meeting['id']
        if series_id in series_info.keys():
            topic = series_info[series_id]['topic']
            host_id = series_info[series_id]['host_id']

        meeting_doc = create_meeting_document(meeting, topic, host_id)

        es.index(
            index="meetings",
            doc_type="meeting",
            id=meeting['uuid'],  # unique meeting occurrence id
            body=meeting_doc
        )

    return meetings


def get_sessions_from(date, key, secret):
    es = Elasticsearch([ES_HOST])
    url = "/metrics/meetingdetail"
    participant_sessions = []

    params = {
        'api_key': key,
        'api_secret': secret,
        'type': 2,  # completed meetings
        'page_size': 100,  # max page size
        'page_number': 1
    }

    meetings = get_meetings(date, key, secret)

    for meeting in meetings:
        uuid = meeting['uuid']
        params['meeting_id'] = uuid
        sessions = fetch_records(url, params, 'participants')

        for session in sessions:
            document = create_sessions_document(session, uuid)
            participant_sessions.append(document)
            unique_session_id = uuid + session['user_id']
            es.index(
                index="sessions",
                doc_type="session",
                id=unique_session_id,
                body=document
            )

        time.sleep(1)
    
    return meetings, participant_sessions


def create_meeting_document(meeting, topic, host_id):

    doc = {
        "meeting_series_id": meeting['id'],
        "topic": topic,
        "host": {
            "host_id": host_id,
            "name": meeting['host'],
            "email": meeting['email'],
            "user_type": meeting['user_type']
        },
        "start_time": meeting['start_time'],
        "end_time": meeting['end_time'],
        "duration": to_seconds(meeting['duration']),
        "participant_sessions": meeting['participants'],  # not unique participants
        "has_pstn": meeting['has_pstn'],
        "has_voip": meeting['has_voip'],
        "has_3rd_party_audio": meeting['has_3rd_party_audio'],
        "has_video": meeting['has_video'],
        "has_screen_share": meeting['has_screen_share'],
        "recording": meeting['recording'],
    }

    return doc


def create_sessions_document(session, meeting_uuid):

    doc = {
        "meeting": meeting_uuid,
        "id": session['id'],
        "user_id": session['user_id'],
        "user_name": session['user_name'],
        "device": session['device'],
        "ip_address": session['ip_address'],
        "country": session['cn'],
        "city": session['city'],
        "network_type": session['network_type'],
        "join_time": session['join_time'],
        "leave_time": session['leave_time'],
        "share_application": session['share_application'],  # bool
        "share_desktop": session['share_desktop'],  # bool
        "share_whiteboard": session['share_whiteboard'],  # bool
        "recording": session['recording']  # bool
    }

    return doc


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


# convert duration from MM:SS or HH:MM:SS to seconds
def to_seconds(duration):
    try:
        dt = datetime.strptime(duration, "%H:%M:%S")
    except ValueError:
        dt = datetime.strptime(duration, "%M:%S")
    delta = timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second)

    return int(delta.total_seconds())


def main(args):

    try:
        with open_destination(args.destination) as fh:
            meetings = get_sessions_from(args.date, args.key, args.secret)
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
    parser.add_argument("--es_host", help="Elasticsearch host:port", default=ES_HOST)
    args = parser.parse_args()

    if args.date is None:
        args.date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    main(args)
