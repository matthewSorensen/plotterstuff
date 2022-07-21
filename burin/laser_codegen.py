import burin.types
import pewpew.laser_events as l

from dataclasses import dataclass
import itertools
import numpy as np

@dataclass
class PassParameters:
    preview : bool
    speed : float = 0.0 # Processing speed, in mm/s
    power : float = 0.0 # Processing power, in watts
    wobble : (float, float, float) = None # Wobble radius (mm) and speed (Hz)
    repetition : float = None # Repetition rate (kHz)
    passes : int = 1 # How many times should we repeat this geometry?
    point_time : float = None # How long does a point get abalated?
    

@dataclass
class MachineParameters:

    power_range : (float, float)
    repetition_range : (float, float)
    field_size : float
    travel_speed : float


def generate_unit(pass_parameters, machine_parameters, geometry):

    size = machine_parameters.field_size
    
    if not pass_parameters.preview:
        # Set the repetition rate if a non-default one is specified 
        if pass_parameters.repetition is not None:
            lo,hi = machine_parameters.repetition_range
            rep = max(lo,min(hi,pass_parameters.repetition))
            yield l.arm(rep)
        # Normalize and clamp the power settings relative to the machine
        power = pass_parameters.power
        lo,hi = machine_parameters.power_range
        if power < lo:
            power = 0.0
        if power > hi:
            power = hi
        yield l.power(power / hi)
        # Set the wobble to something (scaling radius to the field size), or turn it off
        if pass_parameters.wobble:
            radius, frequency, phase = pass_parameters.wobble
            yield l.wobble_on(radius / size, frequency, phase)
        else:
            yield l.wobble_off()
    else:
        # No need to wobble for preview passes...
        yield l.wobble_off()

    events = []
    
    for segments in geometry:
        for segment in segments:

            if isinstance(segment, burin.types.Polyline) or isinstance(segment, burin.types.BSpline):
                coords = segment.linearize_for_drawing() if isinstance(segment, burin.types.BSpline) else segment.coords
                
                for i in range(1, coords.shape[0]):
                    events.append(l.line(coords[i-1] / size, coords[i] / size, speed = pass_parameters.speed / size))
                    
            elif isinstance(segment, burin.types.Arc):
                coords = np.array(list(segment.linearize_to(0.1)))
                for i in range(1, coords.shape[0]):
                    events.append(l.line(coords[i-1] / size, coords[i] / size, speed = pass_parameters.speed / size))
                    
    yield from l.adjust_delays(itertools.chain(*(pass_parameters.passes * [events])), machine_parameters.travel_speed)

