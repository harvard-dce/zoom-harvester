# zoom-harvester

A python script for fetching Zoom meeting metadata using the Zoom API and loading data into Elasticsearch.

## Helpful Links

[Zoom API Documentation](https://zoom.github.io/api/)

[Zoom API Playground](https://developer.zoom.us/playground/)

## Terms

**`meeting_uuid`, `series_id`**

The zoom api uses "meeting id" to refer to ids for both an individual instance of a meeting and a series of meetings. These are two distinct type of ids. The zoom-harvester differentiates between the two.

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
