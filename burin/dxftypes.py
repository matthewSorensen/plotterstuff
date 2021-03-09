from geomdl import BSpline
import numpy as np
import math
import ezdxf

import burin.types


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

        return burin.types.BSpline(curve, tolerance)
    
    @staticmethod
    def from_dxf(s):
        return Spline(s.dxf.degree, s.control_points, s.knots)
    
class Polyline:
    def __init__(self, points):
        self.points = points

    def render_to_tolerance(self, tolerance):
        # Here for parallelism with Splines - doesn't apply the tolerance
        return burin.types.Polyline(self.points[:,0:2])
        
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
        a,b = self.coords[0:2]
        return burin.types.Point((a,b))

    @staticmethod
    def from_dxf(point):
        return Point(np.array(point.dxf.location))




class Arc:

    def __init__(self, start, end, center):
        self.start = start
        self.end = end
        self.center = center

    def render_to_tolerance(self, _):
        return burin.types.Arc(self.start, self.end, self.center, False)

    @staticmethod
    def from_dxf(circle):
        """ Is it an arc? Is it a circle? Who knows? """

        center, radius = np.array(circle.dxf.center)[0:2], circle.dxf.radius
        
        if isinstance(circle, ezdxf.entities.Arc):
            start = np.array(circle.start_point)[0:2]
            end = np.array(circle.end_point)[0:2]
            return Arc(start, end, center)
        
        point = center + np.array([radius, 0])
        return Arc(point, point, center)
