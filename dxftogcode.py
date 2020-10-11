import numpy as np
import ezdxf
from geomdl import BSpline
import numpy as np
import math
import pathcleaner
from collections import defaultdict
from processes.default import DefaultProcess
import sys


class Spline:
    def __init__(self,degree, control, knots):
        self.degree = degree
        self.control = np.array(control)
        self.knots = np.array(knots)
        
    def length_upper_bound(self):
        acc = 0
        n, _ = self.control.shape
        for i in range(1,n):
            delta = self.control[i] - self.control[i - 1]
            acc += np.sqrt(delta.dot(delta))
        
        return acc

    def render_to_tolerance(self,tolerance):
        curve = BSpline.Curve()
        curve.degree = self.degree
        curve.ctrlpts = self.control.tolist()
        curve.knotvector = self.knots.tolist()
        curve.sample_size = max(2, math.ceil(self.length_upper_bound() / tolerance))

        return np.array(curve.evalpts)[:,0:2]
        
    @staticmethod
    def from_dxf(s):
        return Spline(s.dxf.degree, s.control_points, s.knots)
    
class Polyline:
    def __init__(self, points):
        self.points = points

    def render_to_tolerance(self, tolerance):
        # Here for parallelism with Splins - doesn't apply the tolerance
        return self.points[:,0:2]
        
    @staticmethod
    def from_dxf(line):
        vertices = [v.dxf.location for v in line.vertices]
        if line.dxf.flags & 1:
            vertices.append(vertices[0])
        return Polyline(np.array(vertices))
    
def load_dxf(fp):
    """ Load, but don't render, a dxf """
    doc = ezdxf.readfile(fp)
    msp = doc.modelspace()
    objects = defaultdict(lambda: [])
    errors = []
    for e in msp:
        key = e.dxf.layer
        if isinstance(e, ezdxf.entities.Line):
            objects[key].append(Polyline(np.array([e.dxf.start, e.dxf.end])))
        elif isinstance(e,ezdxf.entities.Polyline):
            if e.dxf.flags > 1:
                errors.append(("Unsupported polyline flags",e.dxf.handle))
            else:
                objects[key].append(Polyline.from_dxf(e))
                
        elif isinstance(e, ezdxf.entities.Arc):
            # If we do this, it magically converts the arc to a spline
            # and appends it to the end of the file (instead of in place),
            # so we don't have to worry at all!
            e.to_spline(replace = False)
        elif isinstance(e, ezdxf.entities.Spline):
            objects[key].append(Spline.from_dxf(e))
        else:
            errors.append((f"Unsupported dxf object - {e}",e.dxf.handle))
    return dict(objects), errors


if __name__ == "__main__":


    if len(sys.argv) < 3:
        print("dxftogcode.py <input file> <output file prefix>")
        exit()
        

    raw, errors = load_dxf(sys.argv[1])

    if errors:
        print("Error loading dxf")
        for x,y in errors:
            print(x,y)
    else:
        print("All entities succesfully loaded")


    for unit, layers in DefaultProcess.layers_to_units(raw.keys()).items():
        parameters = DefaultProcess.geometry_parameters(unit)
        tol = parameters['tolerance']
        geometry = []
        for layer in layers:
            for entity in raw[layer]:
                geometry.append(entity.render_to_tolerance(tol))
            
        del parameters['tolerance']
        optimized = pathcleaner.clean_paths(geometry, **parameters)

        with open(sys.argv[2] + '-' + unit + '.gcode','w') as f:
            for x in DefaultProcess.generate_code(unit,optimized):
                f.write(x + '\n')
