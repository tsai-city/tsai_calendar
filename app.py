import os
import arrow  # timestamps
from airtable import Airtable  # airtable API
from pprint import pprint  # debugging
from ics import Calendar, Event  # ICS API
from flask import Flask, escape, request, send_file  # web server

# create web server
app = Flask(__name__)

# create an airtable object with connnection to database
airtable = Airtable(
    base_key="appgB7xnfEEOctuUM", table_name="Events", api_key="keyuvixHmS5OHI7rO"
)

# helper function to check if an airtable event is public
def isPublic(event):
    if "Calendar Code" in event["fields"]:
        return event["fields"]["Calendar Code"] == "Public"
    return False


# helper function to turn 12hr string to 24hr string
def timeParser(time_str):
    lower = time_str.lower()

    is_am = None
    # figure out twelve hour time
    if "am" in lower:
        is_am = True
    elif "pm" in lower:
        is_pm = True
    else:  # for TBD events
        return "00:00"

    split = lower.split(":")
    # parse hours and minutes
    hours = split[0]
    minutes = split[1]
    hours = "".join(i for i in hours if i.isdigit())
    minutes = "".join(i for i in minutes if i.isdigit())

    # return HH:mm
    if is_am:
        if len(hours) < 2:
            hours = "0" + hours
        return f"{hours}:{minutes}"
    else:
        if int(hours) + 12 < 24:
            hours = str(int(hours) + 12)
        return f"{hours}:{minutes}"


# helper function to convert an airtable event to an ICS event
def transformToICSEvent(airtableObj):
    fields = airtableObj["fields"]
    e = Event()

    # event name
    if "Event Title" in fields:
        e.name = fields["Event Title"]

    # event begin time
    if "Date" in fields and "Start" in fields:
        begin_time = timeParser(fields["Start"])
        begin_timestamp = fields["Date"] + " " + begin_time
        e.begin = arrow.get(begin_timestamp)

    # event end time
    if "Date" in fields and "End" in fields:
        end_time = timeParser(fields["End"])
        end_timestamp = fields["Date"] + " " + end_time
        e.end = arrow.get(end_timestamp)

    return e


def calendarFromICSEvents(icsEvents):
    c = Calendar()
    for e in icsEvents:
        c.events.add(e)
    return c


@app.route("/")
def index():
    return f"Tsai CITY ICS feed generator. Navigate to either /public or /private"


@app.route("/public")
def public():
    # The Everything Next table shows everything after 3 days ago
    all_events = airtable.get_all(view="Everything Next")

    # filter all events by public
    public = list(filter(lambda event: isPublic(event), all_events))

    # create list of ICS events
    public_events = []
    for i in public:
        public_events.append(transformToICSEvent(i))

    # create an ICS feed
    public_feed = calendarFromICSEvents(public_events)

    # return response as a new file
    if os.path.exists("tsai-public.ics"):
        os.remove("tsai-public.ics")
    open("tsai-public.ics", "w").writelines(public_feed)
    return send_file("tsai-public.ics", as_attachment=True)


@app.route("/private")
def private():
    # The Everything Next table shows everything after 3 days ago
    all_events = airtable.get_all(view="Everything Next")

    # Not Public or Untagged
    private = list(filter(lambda event: not isPublic(event), all_events))

    # create list of ICS events
    private_events = [transformToICSEvent(i) for i in private]

    # create an ICS feed
    private_feed = calendarFromICSEvents(private_events)

    # return response as a new file
    if os.path.exists("tsai-private.ics"):
        os.remove("tsai-private.ics")
    open("tsai-private.ics", "w").writelines(private_feed)
    return send_file("tsai-private.ics", as_attachment=True)

