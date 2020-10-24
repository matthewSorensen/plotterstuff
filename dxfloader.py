import ezdxf
from geomdl import BSpline
import numpy as np
from collections import defaultdict
import math

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

class Point:

    def __init__(self, coords):
        self.coords = coords
        
    def render_to_tolerance(self, _):
        return self.coords[0:2].reshape((1,2))

    @staticmethod
    def from_dxf(point):
        return Point(np.array(point.dxf.location))

def load_layers(fp, remove_empty = True):
    doc = ezdxf.readfile(fp)
    layers = [] # something is up with ezdxf, and I can't simply yield the layers as an iterator
    for l in doc.layers:
        if l.dxf.plot:
            layers.append(l.dxf.name)

    if remove_empty:

        unseen = set(layers)
        for e in doc.modelspace():
            key = e.dxf.layer
            if key in unseen:
                unseen.remove(key)
            if not unseen:
                break

        return list(x for x in layers if x not in unseen)
    
    return layers

def load_entities(fp, layers):
    """ Load a subset of a dxf file """
    msp = ezdxf.readfile(fp).modelspace()
    objects = defaultdict(lambda: [])
    errors = []

    splinable = ezdxf.entities.Arc, ezdxf.entities.Circle,  ezdxf.entities.Ellipse

    layers = set(layers)
    
    for e in msp:
        key = e.dxf.layer
        if key not in layers:
            continue
        
        if isinstance(e, ezdxf.entities.Line):
            objects[key].append(Polyline(np.array([e.dxf.start, e.dxf.end])))
        elif isinstance(e,ezdxf.entities.Polyline):
            if e.dxf.flags > 1:
                errors.append(("Unsupported polyline flags",e.dxf.handle))
            else:
                objects[key].append(Polyline.from_dxf(e))
                
        elif isinstance(e, splinable):
            # If we do this, it magically converts the object to a spline
            # and appends it to the end of the file (instead of in place),
            # so we don't have to worry at all!
            e.to_spline(replace = False)
        elif isinstance(e, ezdxf.entities.Spline):
            objects[key].append(Spline.from_dxf(e))
        elif isinstance(e, ezdxf.entities.Point):
            objects[key].append(Point.from_dxf(e))
        else:
            errors.append((f"Unsupported dxf object - {e}",e.dxf.handle))
            
    return dict(objects), errors
