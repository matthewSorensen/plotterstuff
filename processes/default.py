# things we'd like to support:
# * single tool pen plotting (active, passive)
# * multi-pen single tool plotting
# * repeated, fiducial-driven workflows

def axes_dict(d):
    return ' '.join((v + str(x) for v,x in d.items()))

class DefaultProcess:
    
    @classmethod
    def layers_to_units(_,layers):
        return {'all' : layers}

    @classmethod
    def geometry_parameters(_, unit_name):
        return {'tolerance' : 0.1, 'link': True, 'reverse' : True, 'deduplicate' : True, 'merge' : True, 'reduce' : None}
    
    @classmethod
    def speeds(cls,unit_name):
        return {'travel' : 10000, 'plot' : 5000, 'clearance' : 100}
    
    @classmethod
    def heights(cls,unit_name):
        return {'clearance' : {'Z' : 15}, 'travel' : {'V' : 4, 'Z' : 10}, 'plot' : {'V' : 5.5}}

    @classmethod
    def generate_code(cls, unit_name, segments):
        speeds = cls.speeds(unit_name)
        plot, travel = speeds['plot'], speeds['travel']
        i = -1
        for i,seg in enumerate(segments):
            if i == 0:
                yield from cls.prelude(unit_name, seg[0])
            else:
                x,y = seg[0]
                yield f"G0 X{x} Y{y} F{travel}"
            
            yield from cls.start_drawing(unit_name)
            for x,y in seg[1:]:
                yield f"G1 X{x} Y{y} F{plot}"

            yield from cls.stop_drawing(unit_name)

        if i != -1:
            yield from cls.postlude(unit_name)
        
    @classmethod
    def prelude(cls,unit_name, starting_position):
        speeds = cls.speeds(unit_name)
        heights = cls.heights(unit_name)
        
        yield "; Retract to a safe clearance plane, pick up the tool, and rapid to the start"
        yield f"G0 {axes_dict(heights['clearance'])} F{speeds['clearance']}"
        yield "G28 V0"
        yield "T3"
        yield f"G0 X{starting_position[0]} Y{starting_position[1]} F{speeds['travel']}"
        yield f"G0 {axes_dict(heights['travel'])} F{speeds['clearance']}"
        yield "; Begin plotting!"
    
    @classmethod
    def postlude(cls,unit_name):
        speeds = cls.speeds(unit_name)
        heights = cls.heights(unit_name)
     
        yield "; Retract to a safe clearance plane, home the pen, and drop the tool off"
        yield f"G0 {axes_dict(heights['clearance'])} F{speeds['clearance']}"
        yield "G28 V0"
        yield "T-1"

    @classmethod
    def start_drawing(cls,unit_name):
        height = cls.heights(unit_name)['plot']['V']
        yield f"G0 V{height} F4000"
        
    
    @classmethod
    def stop_drawing(cls,unit_name):
        height = cls.heights(unit_name)['travel']['V']
        yield f"G0 V{height} F4000"

