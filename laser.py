import burin.process
import burin.types
import numpy as np
import os
import math
import copy
from pewpew.definitions import Segment

from pewpew.job_file import write_file
import burin.laser_codegen as cg

machine_parameters = cg.MachineParameters(power_range = (3.0,30.0), repetition_range = (40.0,60.0), field_size = 50.0, travel_speed = 20.0)

class DefaultLaser(burin.process.BaseProcess):

    PARAMETERS = cg.PassParameters(preview = False,
                                   speed = 200.0,
                                   power = 10.0,
                                   wobble = None,
                                   passes = 1,
                                   point_time = 0.005)
        
    def write_file(self, directory, unit, events):
        filepath = os.path.join(directory, unit + ".laser")
        write_file(filepath, list(events), name = unit, preview = unit == 'Preview')
    
    def layers_to_units(self, layers):

        units = []

        for layer in burin.process.cannonical_order(layers):
            units.append({"name": layer,"subunits" : [(layer,[layer])],"parameters" : []})

        return units

    def geometry_parameters(self, unit_name):
        """ How should we process each layer - specifies a line segment length for conversion from
        dxf geometry, and all of the parameters to the linker/optimizer/cleaner. """
        return {'link': True, 'reverse' : True, 'deduplicate' : True, 'merge' : 0.01}
    
    def generate_code(self, unit_name, segments):
        parameters = type(self).PARAMETERS if (unit_name[0] != 'Preview') else cg.PassParameters(preview = True, speed = 200.0)
        yield from cg.generate_unit(parameters, machine_parameters, segments)


class StainlessStencil(DefaultLaser):
    """ Now you can just subclass this for particular parameters..."""
    PARAMETERS = cg.PassParameters(preview = False,
                                   speed = 100.0,
                                   power = 20.0,
                                   wobble = (0.015, 3000.0,0),
                                   passes = 25,
                                   point_time = 0.005)
