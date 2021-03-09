
import burin.types


class GCodeGen:

    def __init__(self):
        
        self.speeds = {'v' : 4000, 'z' : 100, 'travel' : 10000, 'plot' : 2000}
        self.heights = {'z_clearance' : 15, 'v_clearance' : 1.0, # Z and V axis heights for moving around during setup
                        'z_travel' : 10,  'v_travel' : 4, # Z and V axis heights for rapiding around during plotting
                        'v_toolchange' : 5.0, # V height for changing tools. (v_down - v_toolchange) controls force using during plotting
                        'v_down' : 5.5} # V height for actually plotting

    def generate_segment(self, segment):
        """ V-axis pen plotting gcode for a continuous segment of objects. """ 

        plot = self.speeds['plot']
        
        start = segment[0].endpoints()[0]
        yield f"G0 X{start[0]} Y{start[1]} F{self.speeds['travel']}"
        yield f"G0 V{self.heights['v_down']} F{self.speeds['v']}"

        for i, seg in enumerate(segment):
            if isinstance(seg, burin.types.Polyline):
                n = 1 if i == 0 else 0
                for x,y in seg.coords[n:]:
                    yield f"G1 X{x} Y{y} F{plot}"

            elif isinstance(seg, burin.types.BSpline):
                
                n = 1 if i == 0 else 0
                for x,y in seg.linearize_for_drawing()[n:]:
                    yield f"G1 X{x} Y{y} F{plot}"
                          
            elif isinstance(seg, burin.types.Arc):
                start, end = seg.endpoints()
                I,J = seg.center - start
                if i != 0:
                    yield f"G1 X{start[0]} Y{start[1]} F{plot}"
                yield f"G{2 if seg.clockwise else 3} X{end[0]} Y{end[1]} I{I} J{J} F{plot}"               
            else:
                yield ";Point!"
            
        yield f"G0 V{self.heights['v_travel']} F{self.speeds['v']}"


    def go_to_clearance(self):
        yield f'G0 Z{self.heights["z_clearance"]} V{self.heights["v_clearance"]} F{self.speeds["z"]}'

    def go_to_travel(self):
        yield f'G0 Z{self.heights["z_travel"]} V{self.heights["v_travel"]} F{self.speeds["z"]}'


    
    def start_plot(self, tool = 3):

        yield ";Home the pen, go to the clearance plane, and pick up the tool"
        yield "G28 V0"
        yield from self.go_to_clearance()
        yield f"T{tool}"

    def finish_plot(self):

        yield ";Return to clearance state, and put the tool back"
        yield from self.go_to_clearance()
        yield f'T-1'

        
    def prompt_pen_change(self):
        """ Assumes machine is in some location at the clearance state
        1) Prompts user to remove the current tool
        2) Homes pen, and goes to the z travel height + toolchange v height.
        3) Prompts user to insert the new tool, in contact with work
        4) Returns to clearance state """


        yield ';Prompt user to remove the current tool from the plotter head'
        yield 'M291 P"Remove any pen present in tool" T-1'
        yield 'M226'
        yield ';Home the pen, and go to the toolchange state'
        yield 'G28 V0'
        yield f'G0 Z{self.heights["z_travel"]} V{self.heights["v_toolchange"]} F{self.speeds["z"]}'
        yield ";Prompt the user to insert and lock the new tool"
        yield 'M291 P"Touch pen to material surface and lock" T-1'
        yield 'M226'
        yield ";Return to clearance state"
        yield from self.go_to_clearance()
