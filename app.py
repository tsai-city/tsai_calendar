# ---------------------------------- Imports --------------------------------- #

import os
from datetime import datetime
from pprint import pprint  # debugging
from airtable import Airtable  # airtable API
from icalendar import Calendar, Event
from pytz import timezone  # timezone
from uuid import uuid1
from flask import Flask, escape, request, send_file, render_template  # web server

# ----------------------------------- Setup ---------------------------------- #

# create web server
app = Flask(__name__)

# create an airtable object with connnection to database
airtable = Airtable(
    base_key="appgB7xnfEEOctuUM", table_name="Events", api_key="keyuvixHmS5OHI7rO"
)

# ---------------------------------- Routes ---------------------------------- #


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/private")
def private_ics():
    return createCalendarFromFilter(isPrivate, "private")


@app.route("/public")
def public_ics():
    return createCalendarFromFilter(isPublic, "public")


# ------------------------ The brains of the operation ----------------------- #


def createCalendarFromFilter(filter_function, calendar_name):
    # get airtable rows
    all_events = airtable.get_all(view="Everything Next")

    # apply filter function
    filtered = list(filter(lambda event: filter_function(event), all_events))

    # transform to ics events
    transformed = [transformAirtableObjToICSEvent(i) for i in filtered]

    # prepare new calendar
    cal = createNewCalendar(calendar_name)
    for e in transformed:
        cal.add_component(e)

    # write to file
    writeToFile(cal, f"{calendar_name}.ics")
    return send_file(f"{calendar_name}.ics", as_attachment=True, cache_timeout=-1)


# ----------------------------- Filter functions ----------------------------- #


def isPublic(event):
    if "Calendar Code" in event["fields"]:
        return event["fields"]["Calendar Code"] == "Public"
    return False


def isPrivate(event):
    return not isPublic(event)


# ----------------------------- Helper functions ----------------------------- #


def writeToFile(calendar, name):
    # remove file if it already exists
    if os.path.exists(name):
        os.remove(name)
    # create a new file
    f = open(name, "wb")
    f.write(calendar.to_ical())
    f.close()


def createNewCalendar(name):
    cal = Calendar()
    cal.add("prodid", f"<{name}>")
    cal.add("version", "2.0")
    return cal


def getDatetime(daystamp, timestamp):
    # alter timestamp
    if not timestamp or timestamp == "TBD":
        timestamp = "12:00 AM"
    # make full timestamp
    fullTimestamp = daystamp + "-" + timestamp
    fullTimestamp = fullTimestamp.replace(" ", "")
    # parse and return
    d = datetime.strptime(fullTimestamp, "%Y-%m-%d-%I:%M%p")
    d = d.replace(tzinfo=timezone("EST"))
    return d


def getToday():
    d = datetime.now().replace(tzinfo=timezone("EST"))
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
