import burin.process
import burin.types
import numpy as np


def axes_dict(d):
    return ' '.join((v + str(x) for v,x in d.items()))

class SimpleProcess(burin.process.BaseProcess):
    """ Combines all layers into one step, and plots them unchanged """

    def modify_geometry(self,_,geo):
        return geo
    
    def speeds(self,unit_name):
        return {'travel' : 10000, 'plot' : 2000, 'clearance' : 100}
    
    def heights(self,unit_name):
        return {'clearance' : {'Z' : 15}, 'travel' : {'V' : 4, 'Z' : 10}, 'plot' : {'V' : 5.5}}
    
    def prelude(self,unit_name, starting_position):
        speeds = self.speeds(unit_name)
        heights = self.heights(unit_name)
        
        yield "; Retract to a safe clearance plane, pick up the tool, and rapid to the start"
        yield f"G0 {axes_dict(heights['clearance'])} F{speeds['clearance']}"
        yield "G28 V0"
        yield "T3"
        yield f"G0 X{starting_position[0]} Y{starting_position[1]} F{speeds['travel']}"
        yield f"G0 {axes_dict(heights['travel'])} F{speeds['clearance']}"
        yield "; Begin plotting!"
    
    def postlude(self,unit_name):
        speeds = self.speeds(unit_name)
        heights = self.heights(unit_name)
     
        yield "; Retract to a safe clearance plane, home the pen, and drop the tool off"
        yield f"G0 {axes_dict(heights['clearance'])} F{speeds['clearance']}"
        yield "G28 V0"
        yield "T-1"
    
    def generate_code(self, unit_name, segments):
        
        speeds = self.speeds(unit_name)
        up_height, down_height = self.heights(unit_name)['travel']['V'], self.heights(unit_name)['plot']['V']
        plot, travel = speeds['plot'], speeds['travel']

        if len(segments) == 0:
            return

        yield from self.prelude(unit_name, segments[0][0].endpoints()[0])
        for segment in segments:
            start = segment[0].endpoints()[0]
            yield f"G0 X{start[0]} Y{start[1]} F{travel}"
            yield f"G0 V{down_height} F4000"

            for i, seg in enumerate(segment):
                if isinstance(seg, burin.types.Polyline):
                    n = 1 if i == 0 else 0
                    for x,y in seg.coords[n:]:
                        yield f"G1 X{x} Y{y} F{plot}"
                
                elif isinstance(seg, burin.types.Arc):
                    start, end = seg.endpoints()
                    I,J = seg.center - start
                    if i != 0:
                        yield f"G1 X{start[0]} Y{start[1]} F{plot}"
                    yield f"G{2 if seg.clockwise else 3} X{end[0]} Y{end[1]} I{I} J{J} F{plot}"
                    
                else:
                    yield ";Point!"
            yield f"G0 V{up_height} F4000"
        
        yield from self.postlude(unit_name)

