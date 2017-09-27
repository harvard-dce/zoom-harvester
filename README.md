# zoom-harvester

A python script for fetching Zoom meeting metadata using the Zoom API and loading data into Elasticsearch.

#### Helpful Links
[Zoom API Documentation](https://zoom.github.io/api/)
[Zoom API Playground](https://developer.zoom.us/playground/)

#### API Terms

**meeting id**

To Zoom, meeting means both an individual instance of a meeting and a series of meetings. There are unique ids for each meeting instance, and series ids that can remain static for a series of reoccuring meetings. The Zoom API docmentation refers to both types of ids as "meeting id". We will refer to those as _meeting_uuid/unique_meeting_id_, and _series_id_.

Within the series_id, there can be several types:
- Most Common:
    * 9-digit ids tied to a repeating or scheduled series of meeting, such as a class that meets every Wednesday.
- Less Common:
    * 10-digit ids for PMIs (Personal Meeting Rooms) is a series id that an individual user can associate with their account so that every meeting that they host can be accessed with the same link in the format https://zoom.us/j/0123456789
    * 9-digit meeting ids not associated with a series of meetings or a PMI, these are instant meetings which will show up when you search for all the meetings over a period of time (/metrics/meetings/) but will not show up if you try to look them up individual (/meetings/get/)

**user_id**

Since only hosts have accounts, most of the time user_id refers to a host. Participants are not required to have accounts and do not log in when they join a meeting but are generated temporary non-unique "user_ids."


#### API Calls

| Call                       | Requires          | Returns |
| -------------------------- |:-----------------:| :-------:            |
| /report/getaccountreport/  | key/secret, dates | Active host information, including host ids.   |
| /meeting/list/      | host ids      |  Meeting series data including topic and series id.  |
| /metrics/meetings/ |       |  Meeting instance data, including unique meeting ids but not participant data. |
| /metrics/meetingdetail/ | unique meeting ids |  All information from /metrics/meetings/ plus detailed participant data. |
