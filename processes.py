import numpy as np

def axes_dict(d):
    return ' '.join((v + str(x) for v,x in d.items()))

class DefaultProcess:

    def __init__(self):
        pass

    def layers_to_units(self,layers):
        return [{"name" : "all",
                 "subunits" : [("all",layers)],
                 "runtime" : []}]

    def modify_geometry(self, geometry, unit_name, parameters):
        return geometry

    def geometry_parameters(self, unit_name, parameters):
        return {'tolerance' : 0.1, 'link': True, 'reverse' : True, 'deduplicate' : True, 'merge' : True, 'reduce' : None}
    
    def generate_code(self, unit_name, segments, parameters):
        speeds = self.speeds(unit_name)
        plot, travel = speeds['plot'], speeds['travel']
        i = -1
        for i,seg in enumerate(segments):
            if i == 0:
                yield from self.prelude(unit_name, seg[0])
                yield '; starting drawing'
            else:
                x,y = seg[0]
                yield f"G0 X{x} Y{y} F{travel}"
            
            yield from self.start_drawing(unit_name)
            for x,y in seg[1:]:
                yield f"G1 X{x} Y{y} F{plot}"

            yield from self.stop_drawing(unit_name)

        yield from self.stop_drawing(unit_name)
        yield '; done drawing'
        
        if i != -1:
            yield from self.postlude(unit_name)


            
    
    def speeds(self,unit_name):
        return {'travel' : 10000, 'plot' : 5000, 'clearance' : 100}
    
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

    def start_drawing(self,unit_name):
        height = self.heights(unit_name)['plot']['V']
        yield f"G0 V{height} F4000"
        
    def stop_drawing(self,unit_name):
        height = self.heights(unit_name)['travel']['V']
        yield f"G0 V{height} F4000"



        
class Multipen(DefaultProcess):
    
    def layers_to_units(self,layers):
        # Set a cannonical stored order, always processing the Default layer first...
        self.layers = ['Default'] + list(x for x in layers if x != 'Default')
        n = len(layers)
        self.numbers = {'Default' : 0}
        acc = [{'name' : 'Default', 'subunits' : [('drawing',['Default'])], 'runtime' : ['x','y', 'cal_x', 'cal_y']}]

        if n > 1:
            sub = acc[-1]['subunits']
            sub.append(('cal-reference',[]))
            sub.append(('cal',[]))

        for i, l in enumerate(self.layers[1:]):
            name = ''.join(l.split())
            record = {'name' : name, 'subunits' : [('drawing',[l])], 'runtime' : ['x','y']}
            if i != n - 2:
                record['subunits'].append(('cal', []))
            self.numbers[name] = i + 1
            acc.append(record)
        self.units = acc
        return acc

    def vernier_reference(self,parameters):
        n = len(self.layers) - 1
        
        base = np.array([float(parameters['Default']['cal_x']),float(parameters['Default']['cal_y'])])
            
        for i in range(n):
            offset = base + i * np.array([3,3])
            for j in range(21):
                length = -1
                if j == 10:
                    length = -2
                yield np.array([[0,j],[length,j]]) + offset
                yield np.array([[j,0],[j,length]]) + offset

    def vernier_sample(self, unit, parameters):

        base = np.array([float(parameters['Default']['cal_x']),float(parameters['Default']['cal_y'])])
        base += self.numbers[unit] * np.array([3,3])

        for j in range(21):
            x = 1.1*float(j - 10) + 10            
            yield np.array([[0,x],[1,x]]) + base
            yield np.array([[x,0],[x,1]]) + base

    
    def modify_geometry(self, geometry, unit_name, parameters):
        """ Replace the blank geometry for calibration subunits with real geometry """

        unit,subunit = unit_name
        if subunit == 'cal-reference':
            return list(self.vernier_reference(parameters))
        elif subunit == 'cal':
            return list(self.vernier_sample(unit,parameters))

        
        base = np.array([float(parameters['Default']['x']),float(parameters['Default']['y'])])
        if unit != 'Default':
            base -= np.array([float(parameters[unit]['x']),float(parameters[unit]['y'])])
        # otherwise apply offsets
        return list(x + base for x in geometry)
    
    def prompt_toolchange(self,unit_name):
        heights = self.heights(unit_name)
        yield f"G1 V{heights['plot']['V'] - 0.5} F4000"
        yield 'M291 P"Touch pen to material surface and lock" T-1'
        yield 'M226'
        yield from self.stop_drawing(unit_name)
        
    def prelude(self,unit_name,start):
        speeds = self.speeds(unit_name)
        unit,subunit = unit_name
        
        if self.numbers[unit] == 0 and subunit == 'drawing':
            yield from super().prelude(unit_name, start)
            yield from self.prompt_toolchange(unit_name)
            yield from self.stop_drawing(unit_name)

        elif subunit == 'cal':
            yield from self.stop_drawing(unit_name)
            yield f"G0 X{start[0]} Y{start[1]} F{speeds['travel']}"
            yield from self.prompt_toolchange(unit_name)

        else:
            yield from self.stop_drawing(unit_name)
            yield f"G0 X{start[0]} Y{start[1]} F{speeds['travel']}"


    def postlude(self, unit_name):
        unit, subunit = unit_name
        if self.numbers[unit] == len(self.numbers) - 1:
            print("Final termination")
            yield from super().postlude(unit_name)
        else:
            yield from self.stop_drawing(unit_name)
        