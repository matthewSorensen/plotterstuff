import burin.process
import burin.types
import numpy as np
import math

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



class Multilayer(SimpleProcess):

    def conversion_parameters(self):
        ret = super().conversion_parameters()
        ret['resolution'] = 0.1
        return ret
    
    def get_transform(self, unit):
        sub = self.parameters[unit]
        ct,st = 1,0
        if 'theta' in sub:
            theta = float(sub['theta'])
            ct,st = math.cos(theta), math.sin(theta)
        x,y = float(sub['x']),float(sub['y'])

        return np.array([[ct,0 - st,x],[st,ct,y]])
        

    def layers_to_units(self, layers):
        """ Shuffle things around - create a unit for every layer, add the fiducial layer to the first unit,
        and add all of the parameters required for cross-layer alignment. """
        if 'Fiducials' not in layers:
            print("No layer for fiducial markers")
            return None

        layers = list(x for x in reversed(layers) if x != 'Fiducials')
        acc = [{"name": layers[0], "subunits" : [("fiducials", ['Fiducials']),('_', [layers[0]])], "parameters" : ['x','y']}]

        for i, l in enumerate(layers[1:]):
            record = {"name": l, "subunits" : [('_', [l])], "parameters" : ['x','y','theta']}
            if i == 0:
                record['parameters'] += ['delta_x','delta_y']
            acc.append(record)

        return acc

    def draw_fiducial_at(self, origin, scale = 0.5):
        i,j = np.array([1,0]), np.array([0,1])

        long_stroke = burin.types.Polyline(np.array([origin - (1 + 0.5 * scale) * i,
                                                     origin - 0.5 * scale * i,
                                                     origin + 0.5 * scale * i]))
        
        short_stroke = burin.types.Polyline(np.array([origin + (1 + 0.5 * scale) * i,
                                                     origin + 0.5 * scale * j,
                                                     origin]))
        
        long_stroke.backlash = True
        short_stroke.backlash = True
        
        return [long_stroke, short_stroke]
    
    def modify_geometry(self, name, geo):

        unit, subunit = name
        
        if subunit == 'fiducials':
            if len(geo) != 3 or any(not isinstance(x, burin.types.Point) for x in geo):
                print("Fiducial layer must consist of exactly three points")
                exit()
            ret, points = [],[]

            for p in geo:
                points.append(p.coords.tolist())
                ret += self.draw_fiducial_at(p.coords)
                
            self.parameters[unit]['fiducial_coords'] = points
            geo = ret

        t = self.get_transform(unit)
        for g in geo:
            g.transform(t)
            
        return geo


    def geometry_parameters(self, unit_name):
        unit,sub = unit_name
        p = super().geometry_parameters(unit_name)
        if sub == 'fiducials':
            # We don't want to merge small line segments, and because of the backlash
            # compensation, we can't reverse them either
            p['merge'] = False
            p['reverse'] = False
        return p

    
    def generate_code(self, unit_name, segments):
        
        speeds = self.speeds(unit_name)
        up_height, down_height = self.heights(unit_name)['travel']['V'], self.heights(unit_name)['plot']['V']
        plot, travel = speeds['plot'], speeds['travel']

        if len(segments) == 0:
            return

        first, last = self.subunit_position(unit_name)

        if first:
            yield from self.prelude(unit_name, segments[0][0].endpoints()[0])
      
        yield f"; Starting subunit {unit_name[1]}"


        for segment in segments:

            start = segment[0].endpoints()[0]
            yield f"G0 X{start[0]} Y{start[1]} F{travel}"

            for i, seg in enumerate(segment):
                if isinstance(seg, burin.types.Polyline):
                    if 'backlash' in seg.__dict__ and seg.backlash:
                        yield f"G0 V{up_height} F4000" # Regardless of previous state...
                        first, second = seg.coords[0], seg.coords[1]
                        yield f"G1 X{first[0]} Y{first[1]} F{travel}"
                        yield f"G1 X{second[0]} Y{second[1]} F{travel}"
                        yield f"G0 V{down_height} F4000"
                        for x,y in seg.coords[2:]:
                            yield f"G1 X{x} Y{y} F{plot}"
                    else:
                        if i == 0:
                            yield f"G0 V{down_height} F4000"
                        n = 1 if i == 0 else 0
                        for x,y in seg.coords[n:]:
                            yield f"G1 X{x} Y{y} F{plot}"
            
                elif isinstance(seg, burin.types.Arc):
                    start, end = seg.endpoints()
                    I,J = seg.center - start
                    if i != 0:
                        yield f"G1 X{start[0]} Y{start[1]} F{plot}"
                    else:
                        yield f"G0 V{down_height} F4000"
                    yield f"G{2 if seg.clockwise else 3} X{end[0]} Y{end[1]} I{I} J{J} F{plot}"
                    
                else:
                    yield ";Point!"
                    yield f"G0 V{down_height} F4000"
                      

                yield f"G0 V{up_height} F4000"
      
        
        
        if last:
            yield from self.postlude(unit_name)
        
