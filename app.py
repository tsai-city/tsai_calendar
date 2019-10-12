import os
import pandas as pd
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

# helper function to check if an airtable event is public
def isPublic(event):
    if "Calendar Code" in event["fields"]:
        return event["fields"]["Calendar Code"] == "Public"
    return False


def calendarFromICSEvents(icsEvents):
    c = Calendar()
    for e in icsEvents:
        c.add_component(e)
    return c


@app.route("/")
def index():
    return (
        f"Tsai CITY ICS feed generator. Navigate to either /public-csv or /private-csv"
    )


####### NEW


def getToday():
    d = datetime.now().replace(tzinfo=timezone("EST"))
    d = d.strftime("%m/%d/%Y")
    return d


def transformAirtableObjToDict(airtableObj):
    fields = airtableObj["fields"]
    row = {
        "Subject": fields["Event Title"] if "Event Title" in fields else "",
        "Start Date": fields["Date"] if "Date" in fields else getToday(),
        "Start Time": fields["Start"] if "Start" in fields else "",
        "End Date": fields["Date"] if "Date" in fields else getToday(),
        "End Time": fields["End"] if "End" in fields else "",
        "Description": fields["Event Blurb"] if "Event Blurb" in fields else "",
    }
    return row


def getRows(rows_type="public"):
    # pull all events
    all_events = airtable.get_all(view="Everything Next")
    # filter by private or public
    if rows_type == "private":
        filtered = list(filter(lambda event: not isPublic(event), all_events))
    else:
        filtered = list(filter(lambda event: isPublic(event), all_events))
    # transform filtered
    transformed = [transformAirtableObjToDict(i) for i in filtered]
    return transformed


######


def getDatetime(daystamp, timestamp):
    # make full timestamp
    daystamp = daystamp.replace("-", "/")
    if "AM" not in timestamp or "PM" not in timestamp:
        timestamp = "12:00AM"
    fullTimestamp = daystamp + "-" + timestamp
    # remove whitespace
    fullTimestamp = fullTimestamp.replace(" ", "")
    # parse and returns
    d = datetime.strptime(fullTimestamp, "%Y/%m/%d-%I:%M%p")
    d = d.replace(tzinfo=timezone("EST"))
    return d


def transformDictRowToICSEvent(row):
    event = Event()
    event.add("summary", row["Subject"])
    event.add("description", row["Description"])
    event.add("dtstart", getDatetime(row["Start Date"], row["Start Time"]))
    event.add("dtend", getDatetime(row["End Date"], row["End Time"]))
    event.add("dtstamp", getDatetime(row["Start Date"], row["Start Time"]))
    event["uid"] = str(uuid1())
    return event


@app.route("/private")
def private_ics():
    # prepare
    cal = Calendar()
    cal.add("prodid", "<tsai-cal>")
    cal.add("version", "2.0")
    rows = getRows("private")

    # create events
    events = [transformDictRowToICSEvent(r) for r in rows]
    for e in events:
        cal.add_component(e)

    if os.path.exists("private.ics"):
        os.remove("private.ics")
    f = open("private.ics", "wb")
    f.write(cal.to_ical())
    f.close()
    return send_file("private.ics", as_attachment=True, cache_timeout=-1)
