#!/usr/bin/python3
# vim: ts=4 sw=4 expandtab
from argparse import Namespace as NS
import datetime
import json
import math
import os
import pathlib
import subprocess
import time
script_dir = pathlib.Path(os.path.dirname(__file__))
pathlib.Path(script_dir / 'cache').mkdir(parents=True, exist_ok=True)

tz = datetime.timezone(datetime.timedelta(hours=2))

def isoformat_to_date(iso_str):
    iso_str = iso_str.replace('Z', '+00:00')
    return datetime.datetime.fromisoformat(iso_str)

subprocess.run(script_dir / "helper" / "get_flotilla.sh", capture_output=True)
with open(script_dir / 'cache' / 'latest_flotilla.json', 'r') as f:
    try:
        data = json.load(f)
    except Exception as e:
        data = {}
        f.seek(0)
        print(f"error fetching fresh data from source 1: {e} <<<{f.read()}>>>")

subprocess.run(script_dir / "helper" / "get_flotilla_source_2.sh", capture_output=True)
with open(script_dir / 'cache' / 'latest_flotilla_source_2.json', 'r') as f:
    try:
        data_2 = json.load(f)
    except Exception as e:
        data_2 = {}
        f.seek(0)
        print(f"error fetching fresh data from source 2: {e} <<<{f.read()}>>>")

archive_file = script_dir / 'cache' / 'flotilla_all_points.json'
if archive_file.exists():
    with open(archive_file, 'r') as f:
        archive = json.load(f)
else:
    archive = {}


def back_compat(archive):
    for ts, points in archive.items():
        for point in points:
            if '__source__' not in point:
                point['__source__'] = 'source_1'
back_compat(archive)
def iter_source_1(data):
    if data:
        for idd, content in data['vessels'].items():
            pos = content['positions']
            for p in pos:
                epoch = p['last_position_epoch']
                if epoch > 10**(int(math.log10(now)) + 1):
                    epoch //= 1000
                yield p, epoch, 'source_1'

def iter_source_2(data):
    for p in data['data']['trackPointsBySessionId']['trackPoints']:
        date = isoformat_to_date(p['dateTime'])
        epoch = int(date.timestamp())
        yield p, epoch, 'source_2'

now = time.time()
for iterator, data_fetched in (iter_source_1, data), (iter_source_2, data_2):
    for p, epoch, source in iterator(data_fetched):
        p['__epoch__'] = epoch
        p['__source__'] = source
        epoch = str(epoch)

        if epoch not in archive:
            archive[epoch] = []
        sames = [
            other
            for other in archive[epoch]
            if p == {k:v for k,v in other.items() if k != '__injested__' and k != '__last_seen__'}
        ]
        p['__injested__'] = now
        #p['__last_seen__' ] = now
        if not sames:
            archive[epoch].append(p)
        else:
            for other in sames:
                pass
                #other['__last_seen__'] = now
    
with open(archive_file, 'w') as f:
    json.dump(archive, f, indent=4, sort_keys=True)

def latlondist(lat1, lon1, lat2, lon2):
    # https://www.movable-type.co.uk/scripts/latlong.html
    R = 6371e3 # metres
    φ1 = lat1 * math.pi/180 # φ, λ in radians
    φ2 = lat2 * math.pi/180
    Δφ = (lat2-lat1) * math.pi/180
    Δλ = (lon2-lon1) * math.pi/180

    a = (
        math.sin(Δφ/2) * math.sin(Δφ/2) +
        math.cos(φ1) * math.cos(φ2) *
        math.sin(Δλ/2) * math.sin(Δλ/2)
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    d = R * c # in metres
    return d

start = NS()
end = NS()
end.lat = 31 + 26 / 60 + 42.8 / 3600
end.lon = 34 + 21 / 60 + 57.9 / 3600
start.lat = 37.517448
start.lon = 15.111498
def pos_to_ns(pos):
    # 31°26'42.8"N 34°21'57.9"E
    # lat = 31°26'42.8"N
    # lon = 34°21'57.9"E

    if pos['__source__'] == 'source_1':
        try:
            ns = NS()
            ns.lat = pos['lat']
            ns.lon = pos['lon']
            #ns.s = pos['speed']
            #ns.course = pos['course']
            #ns.epoch = pos['last_position_epoch']/1000 # s
            ns.epoch = pos['__epoch__']
            #ns.utc = pos['last_position_UTC']
            ns.date = datetime.datetime.fromtimestamp(ns.epoch, tz)
            ns.d_end = latlondist(ns.lat, ns.lon, end.lat, end.lon)/1000 # km
            ns.d_start = latlondist(ns.lat, ns.lon, start.lat, start.lon)/1000 # km
        except Exception as e:
            print(e)
            print(pos)
            ns = None
        return ns

    elif pos['__source__'] == 'source_2':
        try:
            ns = NS()
            ns.lat = pos['position']['lat']
            ns.lon = pos['position']['lon']
            ns.epoch = pos['__epoch__']
            ns.date = datetime.datetime.fromtimestamp(ns.epoch, tz)
            ns.d_end = latlondist(ns.lat, ns.lon, end.lat, end.lon)/1000 # km
            ns.d_start = latlondist(ns.lat, ns.lon, start.lat, start.lon)/1000 # km
        except Exception as e:
            print(e)
            print(pos)
            ns = None
        return ns
    print('no source', pos)
    return None


ps = [pos_to_ns(v[0]) for _, v in sorted(archive.items())]
ps = [p for p in ps if p is not None]
print(f"time since last point: {datetime.datetime.now(tz) - ps[-1].date}")
for prev,a in reversed(list(zip(ps, ps[1:]))):
    t = a.date-prev.date
    d = latlondist(a.lat, a.lon, prev.lat, prev.lon)/1000
    h = t.total_seconds() / 3600
    print(f"{a.date}: Δt {t}, {d:6.3f}km, {d/h:6.3f}km/h, goal:{a.d_end:6.3f} (Δg {a.d_end-prev.d_end:7.3f}) ({a.d_start / (a.d_start + a.d_end):5.1%})")


# for idd, content in data['vessels'].items():
#     pos = content['positions']
#     ps = [pos_to_ns(p) for p in pos]
#     ps = [p for p in ps if p is not None]
#     for a,prev in reversed(list(zip(ps, ps[1:]))):
#         t = a.date-prev.date
#         d = latlondist(a.lat, a.lon, prev.lat, prev.lon)/1000
#         h = t.total_seconds() / 3600
#         print(f"{a.date}: Δt {t}, {d:6.3f}km, {d/h:6.3f}km/h, goal:{a.d_end:6.3f} (Δg {a.d_end-prev.d_end:7.3f}) ({a.d_start / (a.d_start + a.d_end):5.1%})")
#     print(f"time since last point: {datetime.datetime.now(tz) - ps[0].date}")


