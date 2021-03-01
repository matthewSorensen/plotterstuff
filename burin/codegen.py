
import burin.types


def speeds():
    return {'v' : 4000, 'z' : 100, 'travel' : 10000, 'plot' : 2000}

def heights():
    return {'z_clearance' : 15, 'v_clearance' : 1.0, # Z and V axis heights for moving around during setup
            'z_travel' : 10,  'v_travel' : 4, # Z and V axis heights for rapiding around during plotting
            'v_toolchange' : 5.0, # V height for changing tools. (v_down - v_toolchange) controls force using during plotting
            'v_down' : 5.5} # V height for actually plotting

    
def generate_segment(segment, heights, feeds):
    """ V-axis pen plotting gcode for a continuous segment of objects. """ 

    plot = feeds['plot']
    
    start = segment[0].endpoints()[0]
    yield f"G0 X{start[0]} Y{start[1]} F{feeds['travel']}"
    yield f"G0 V{heights['v_down']} F{feeds['v']}"

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
            
    yield f"G0 V{heights['v_travel']} F{feeds['v']}"


def prompt_pen_change(heights, feeds):
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
    yield f'G0 Z{heights["z_travel"]} V{heights["v_toolchange"]} F{feeds["z"]}'
    yield ";Prompt the user to insert and lock the new tool"
    yield 'M291 P"Touch pen to material surface and lock" T-1'
    yield 'M226'
    yield ";Return to clearance state"
    yield f'G0 Z{heights["z_clearance"]} V{heights["v_clearance"]} F{feeds["z"]}'

def go_to_clearance(heights, feeds):
    yield f'G0 Z{heights["z_clearance"]} V{heights["v_clearance"]} F{feeds["z"]}'

def go_to_travel(heights, feeds):
    yield f'G0 Z{heights["z_travel"]} V{heights["v_travel"]} F{feeds["z"]}'


    
def start_plot(heights, feeds, tool = 3):

    yield ";Home the pen, go to the clearance plane, and pick up the tool"
    yield "G28 V0"
    yield f'G0 Z{heights["z_clearance"]} V{heights["v_clearance"]} F{feeds["z"]}'
    yield f"T{tool}"

def finish_plot(heights, feeds):

    yield ";Return to clearance state, and put the tool back"
    yield f'G0 Z{heights["z_clearance"]} V{heights["v_clearance"]} F{feeds["z"]}'
    yield f'T-1'

    
