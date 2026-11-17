"""Fetch the live Dutch bus delay feed and keep only Bravo West-Brabant stop delays.
Writes delays.json: {"updated": ..., "d": [[line, stop name, scheduled minute of day, delay seconds], ...]}"""
import datetime, json, os, urllib.request
from zoneinfo import ZoneInfo
from google.transit import gtfs_realtime_pb2 as g

URL = "https://gtfs.ovapi.nl/nl/tripUpdates.pb"
tz = ZoneInfo("Europe/Amsterdam")
lk = json.load(open("lookup.json", encoding="utf-8"))

if os.environ.get("FEED_FILE"):          # for local testing
    data = open(os.environ["FEED_FILE"], "rb").read()
else:
    req = urllib.request.Request(URL, headers={"User-Agent": "bravo-west-tracker"})
    data = urllib.request.urlopen(req, timeout=60).read()

feed = g.FeedMessage()
feed.ParseFromString(data)
cutoff = feed.header.timestamp - 3600    # ignore stops older than an hour
out = []
for e in feed.entity:
    tu = e.trip_update
    line = lk["routes"].get(tu.trip.route_id)
    if not line:
        continue
    for s in tu.stop_time_update:
        ev = s.departure if (s.HasField("departure") and s.departure.HasField("time")) else s.arrival
        if not (ev.HasField("time") and ev.HasField("delay")) or ev.time < cutoff:
            continue
        name = lk["stops"].get(s.stop_id)
        if not name:
            continue
        t = datetime.datetime.fromtimestamp(ev.time - ev.delay, tz)
        out.append([line, name, t.hour * 60 + t.minute, ev.delay])

with open("delays.json", "w", encoding="utf-8") as f:
    json.dump({"updated": datetime.datetime.now(tz).isoformat(timespec="seconds"),
               "feed": feed.header.timestamp, "d": out}, f, separators=(",", ":"), ensure_ascii=False)
print("wrote", len(out), "stop delays")
