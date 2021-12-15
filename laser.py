import burin.process
import burin.types
import numpy as np
import os
import math

from pewpew.laser_events import laser_line

def arc_to_representation(arc,speed):

    
    # Complexify everything
    a,b  = arc.start - arc.center, arc.end - arc.center
    r = math.sqrt(a.dot(a))
    cos = math.acos(a.dot(b) / math.sqrt(a.dot(a) * b.dot(b)))
    det = a[0] * b[1] - a[1] * b[0]

    if det < 0:
        cos = 2 * math.pi - cos
    elif cos < 1e-18:
        cos = 2 * math.pi
    # Ok, that's if the angle is counterclockwise    
    if arc.clockwise:
        cos = 2 * math.pi - cos
        cos *= -1
        
    start = math.atan2(a[1],a[0])

    return f"circle {arc.center[0]} {arc.center[1]} {r} {start} {cos} {speed}"





class FiberLaser(burin.process.BaseProcess):

    def write_file(self, directory, unit, events):
        with open(os.path.join(directory, unit + ".txt"),'w') as f:
            for x in events:
                print(x)
    
    def layers_to_units(self, layers):        
        order = reversed(burin.process.cannonical_order(layers))
        return [{"name": "all", "subunits" : [(x,[x]) for x in order], "parameters" : ['engrave_power','engrave_speed','cut_power','cut_speed','cut_wobble','cut_passes']}]

    
    def generate_code(self, unit_name, segments):

        para = self.parameters[unit_name[0]]
        
        seek = 7000

        speed, passes = None, None

        if unit_name[1] == 'Cut':
            yield f"power {para['cut_power']}"
            yield f"wobble {float(para['cut_wobble'])/2} 2000.0"
            speed = para['cut_speed']
            passes = int(para['cut_passes'])
        else:
            yield f"power {para['engrave_power']}"
            yield f"wobble 0.0 0.0"
            speed = para['engrave_speed']
            passes = 1
            

        if passes > 1:
            segments = list(list(s) for s in segments)
            
        for _ in range(passes):
            
            prev = np.array([-1.0,-1.0])

            for segment in segments:

                start = segment[0].endpoints()[0]

                dist = max(1000,1e6 * math.sqrt((prev[0] - start[0])**2 + (prev[1] - start[1])**2) / seek)

                yield f"{start[0]} {start[1]} {dist} 0"

                for seg in segment:
                    if isinstance(seg, burin.types.Polyline) or isinstance(seg, burin.types.BSpline):
                        coords = seg.linearize_for_drawing() if isinstance(seg, burin.types.BSpline) else seg.coords
                        for i in range(1,coords.shape[0]):
                            yield f"line {coords[i-1,0]} {coords[i-1,1]} {coords[i,0]} {coords[i,1]} {speed}"

                    elif isinstance(seg, burin.types.Arc):

                        coords = np.array(list(seg.linearize_to(0.05)))
                        for i in range(1,len(coords)):
                            yield f"line {coords[i-1,0]} {coords[i-1,1]} {coords[i,0]} {coords[i,1]} {speed}"

                end = segment[-1].endpoints()[1]
                yield f"{end[0]} {end[1]} 1000 0"
                prev = end
            
        if False:
            yield
