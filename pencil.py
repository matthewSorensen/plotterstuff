import burin.process
import burin.types
import burin.codegen
import numpy as np


class Pencil(burin.process.BaseProcess):

    def layers_to_units(self, layers):
        order = burin.process.cannonical_order(layers)
        return [{"name": "all", "subunits" : [(x,[x]) for x in order], "parameters" : ['x','y']}]

    def modify_geometry(self, unit_name, geo):
        para = self.parameters[unit_name[0]]
        x,y = float(para['x']), float(para['y'])
        transform = np.array([[1,0,x],[0,1,y]])

        for g in geo:
            g.transform(transform)

        return geo

    
    def generate_code(self, unit_name, segments):
        para = self.parameters[unit_name[0]]
        x,y = float(para['x']), float(para['y'])
        
        first, last = self.subunit_position(unit_name)

        cg = burin.codegen.GCodeGen()

        if first:
            yield from cg.start_plot()
            yield f'G0 X{x} Y{y} F{cg.speeds["travel"]}'
            yield from cg.prompt_pen_change()
            yield from cg.go_to_travel()

        for s in segments:
            yield from cg.generate_segment(s)
        
        if last:
            yield from cg.finish_plot()
            
