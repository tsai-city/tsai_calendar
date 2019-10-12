import os
from datetime import datetime
from pprint import pprint  # debugging
from airtable import Airtable  # airtable API
from icalendar import Calendar, Event
from pytz import timezone  # timezone
from uuid import uuid1
from flask import Flask, escape, request, send_file, jsonify  # web server

# create web server
app = Flask(__name__)

# create an airtable object with connnection to database
airtable = Airtable(
    base_key="appgB7xnfEEOctuUM", table_name="Events", api_key="keyuvixHmS5OHI7rO"
)


@app.route("/")
def index():
    return f"Tsai CITY ICS feed generator. Navigate to either /public or /private"


def getDatetime(daystamp, timestamp):
    # alter timestamp
    if not timestamp or timestamp == "TBD":
        timestamp = "12:00 AM"
    # make full timestamp
    fullTimestamp = daystamp + "-" + timestamp
    fullTimestamp = fullTimestamp.replace(" ", "")
    # parse and return
    d = datetime.strptime(fullTimestamp, "%Y-%m-%d-%I:%M%p")
    # d = d.replace(tzinfo=timezone("EST"))
    return d


def getToday():
    d = datetime.now()
    # .replace(tzinfo=timezone("EST"))
    d = d.strftime("%Y-%m-%d")
    return d


def transformAirtableObjToICSEvent(airtableObj):
    fields = airtableObj["fields"]

    event = Event()
    event.add("summary", fields["Event Title"] if "Event Title" in fields else "")
    event.add("description", fields["Event Blurb"] if "Event Blurb" in fields else "")
    event.add(
        "dtstart",
        getDatetime(
            fields["Date"] if "Date" in fields else getToday(),
            fields["Start"] if "Start" in fields else "",
        ),
    )
    event.add(
        "dtend",
        getDatetime(
            fields["Date"] if "Date" in fields else getToday(),
            fields["End"] if "End" in fields else "",
        ),
    )
    event.add(
        "dtstamp",
        getDatetime(
            fields["Date"] if "Date" in fields else getToday(),
            fields["Start"] if "Start" in fields else "",
        ),
    )
    event["uid"] = str(uuid1())
    return event


# helper function to check if an airtable event is public
def isPublic(event):
    if "Calendar Code" in event["fields"]:
        return event["fields"]["Calendar Code"] == "Public"
    return False


@app.route("/private")
def private_ics():
    # get airtable rows
    all_events = airtable.get_all(view="Everything Next")
    filtered = list(filter(lambda event: not isPublic(event), all_events))
    transformed = [transformAirtableObjToICSEvent(i) for i in filtered]

    # prepare
    cal = Calendar()
    cal.add("prodid", "<tsai-cal-private>")
    cal.add("version", "2.0")

    # create events
    for e in transformed:
        cal.add_component(e)

    if os.path.exists("private.ics"):
        os.remove("private.ics")
    f = open("private.ics", "wb")
    f.write(cal.to_ical())
    f.close()
    return send_file("private.ics", as_attachment=True, cache_timeout=-1)


@app.route("/public")
def public_ics():
    # get airtable rows
    all_events = airtable.get_all(view="Everything Next")
    filtered = list(filter(lambda event: isPublic(event), all_events))
    transformed = [transformAirtableObjToICSEvent(i) for i in filtered]

    # prepare
    cal = Calendar()
    cal.add("prodid", "<tsai-cal-public>")
    cal.add("version", "2.0")

    # create events
    for e in transformed:
        cal.add_component(e)

    if os.path.exists("public.ics"):
        os.remove("public.ics")
    f = open("public.ics", "wb")
    f.write(cal.to_ical())
    f.close()
    return send_file("public.ics", as_attachment=True, cache_timeout=-1)
