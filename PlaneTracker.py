import numpy as np
from opensky_api import OpenSkyApi
import time
import math
from machine_interface import MachineConnection




lat,long = 47.6062, -122.3321
dl = 1.5
bbox = (lat-dl, lat+dl, long-dl, long+dl)


def state_stream(bbox):
    api = OpenSkyApi()
    while True:
        yield api.get_states(bbox= bbox)

def rate_limiter(gen, minimum_time = 1):
    last_time = None
    for x in gen:
        if last_time:
            elapsed = time.time() - last_time
            if elapsed < minimum_time:
                time.sleep(minimum_time - elapsed)
        if x:
            yield x
        last_time = time.time()


def states_to_events(states):
    active_planes = dict()
    for state in states:
        for s in state.states:
            if s.on_ground or not s.callsign:
                continue
            record = s.callsign, s.latitude, s.longitude, s.heading
            if s.callsign not in active_planes:
                yield 'new', record
                active_planes[s.callsign] = record
            else:
                yield 'update', record
                active_planes[s.callsign] = record

"""def events_to_draw_calls(bbox_map, bbox_plotter, events):
    
    def lerp(a,b,c,d,x):
        s = (x - a) / (b - a)
        return (1 - s) * c + s * d
    
    def record_to_xy(record):
        x = lerp(bbox_map[0],bbox_map[1],bbox_plotter[0],bbox_plotter[1], float(record[1]))
        y = lerp(bbox_map[2],bbox_map[3],bbox_plotter[2],bbox_plotter[3], float(record[2]))
        return x,y
    
    for kind, record in events:
        x,y = record_to_xy(record)
        if kind == 'new':
            yield [x-1,x+1],[y,y]
            yield [x,x],[y-1,y+1]
        else:
            theta = math.pi * float(record[3])  / 180
            dx, dy = math.cos(theta), math.sin(theta)
            yield [x - dx, x + dx], [y - dy, y + dy]"""

def events_to_draw_calls(bbox_map, bbox_plotter, events, threshold = 3):
    
    def lerp(a,b,c,d,x):
        s = (x - a) / (b - a)
        return (1 - s) * c + s * d
    
    def record_to_xy(record):
        x = lerp(bbox_map[0],bbox_map[1],bbox_plotter[0],bbox_plotter[1], float(record[1]))
        y = lerp(bbox_map[2],bbox_map[3],bbox_plotter[2],bbox_plotter[3], float(record[2]))
        return x,y

    last_positions = dict()

    for kind, record in events:
        x,y = record_to_xy(record)
        if kind == 'new':
            last_positions[record[0]] = x,y
            #yield [x-1,x+1],[y,y]
            #yield [x,x],[y-1,y+1]
        else:
            px,py = last_positions[record[0]]
            if math.sqrt((x - px)**2 + (y - py)**2) > threshold:
                last_positions[record[0]] = x,y
                yield [px,x], [py, y]

        
x = 75
xmax = 260
pbox = (x,xmax,20,20 + xmax - x)
    

def draw_calls_to_gcode(events, zfeed = 100, xyfeed = 10000, draw_feed = 5000, z_draw = 16.5, z_clear = 17.5):
    
    for x,y in events:
        chunk = []
        chunk.append(f"""G0 X{x[0]} Y{y[0]} Z{z_clear} F{xyfeed}""")
        chunk.append(f"""G0 Z{z_draw} F{zfeed}""")
        for i,xc in enumerate(x):
            if i == 0:
                continue
            chunk.append(f"""G0 X{xc} Y{y[i]} F{draw_feed}""")
        chunk.append(f"""G0 Z{z_clear} F{zfeed}""")

        yield chunk



print("Initializing machine connection")
with MachineConnection('/var/run/dsf/dcs.sock') as m:


    events = states_to_events(rate_limiter(state_stream(bbox), minimum_time = 20))
    for x in draw_calls_to_gcode(events_to_draw_calls(bbox, pbox, events)):
        m.gcode(x)




