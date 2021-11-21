import burin.process
import burin.types
import burin.codegen
import numpy as np


class Pencil(burin.process.BaseProcess):

    def layers_to_units(self, layers):
        order = burin.process.cannonical_order(layers)
        return [{"name": "all", "subunits" : [(x,[x]) for x in order], "parameters" : ['x','y']}]

    
    def generate_code(self, unit_name, segments):
        para = self.parameters[unit_name[0]]
        x,y = float(para['x']), float(para['y'])
        
        first, last = self.subunit_position(unit_name)

        cg = burin.codegen.GCodeGen()

        cg.heights['v_down'] = 5.25

        if first:
            yield from cg.start_plot()
            yield f'G0 X{x} Y{y} F{cg.speeds["travel"]}'
            yield from cg.prompt_pen_change()
            yield from cg.go_to_travel()

        for s in segments:
            yield from cg.generate_segment(s)
        
        if last:
            yield from cg.finish_plot()


class Watercolor(burin.process.BaseProcess):

    def layers_to_units(self, layers):
        order = burin.process.cannonical_order(layers)
        return [{"name": "all", "subunits" : [(x,[x]) for x in order], "parameters" : ['paint_x','paint_y']}]

    
    def generate_code(self, unit_name, segments):
        para = self.parameters[unit_name[0]]
        x,y = float(para['paint_x']), float(para['paint_y'])
        
        first, last = self.subunit_position(unit_name)

        cg = burin.codegen.GCodeGen()
        
        cg.heights['v_travel'] = 2.0
    
        cg.heights['v_down'] = 6.0
    
        if first:
            yield from cg.start_plot()
            yield from cg.go_to_travel()

        for s in segments:
            
            yield f"G1 X{x} Y{y} F{cg.speeds['travel']}"
            yield f"G0 V{cg.heights['v_down']} F{cg.speeds['v']}"
            yield f"G1 X{x+10} Y{y} F{cg.speeds['travel']}"
            yield f"G0 V{cg.heights['v_travel']} F{cg.speeds['v']}"
            
            
            yield from cg.generate_segment(s)


              
        if last:
            yield from cg.finish_plot()
        else:
            # Give the last layer a little time to soak
            yield 'M226'


            
