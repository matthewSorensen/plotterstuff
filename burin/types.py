import numpy as np
import math
import cmath

def transform_point(point, matrix):
    return matrix @ np.hstack([point,1]).T

def subdet(m):
    return m[0,0] * m[0,1] - m[0,1] * m[1,0]

def angle(point):
    return (180 / math.pi) * math.atan2(point[1], point[0])
 
def pointwise_equal(a,b, epsilon):

    if a.__class__ != b.__class__:
        return False

    if isinstance(a, Point) or isinstance(a, Polyline):

        if len(a.coords) != len(b.coords):
            return False
        
        return np.all(np.abs(a.coords - b.coords) < epsilon)

    elif isinstance(a, Arc):

        delta = max(np.max(np.abs(a.start - b.start)),
                    np.max(np.abs(a.end - b.end)),
                    np.max(np.abs(a.center - b.center)))

        return delta < epsilon and a.clockwise == b.clockwise

    return False

def reverse_knot_vector(knots):
    """ It seems like people do this in a few ways, but this is equivalent, 
    fast, inplace, and simple.
    
    (https://sourceforge.net/p/octave/nurbs/ci/default/tree/inst/nrbreverse.m)
    (https://github.com/pboyer/verb/blob/master/src/verb/eval/Modify.hx#L74)"""
    
    n = len(knots)
    m = n // 2
    last = knots[-1]
    for i in range(m):
        other = n - i - 1
        tmp = last - knots[i]
        knots[i] = last - knots[other] 
        knots[other] = tmp
    if n != m * 2:
        knots[m] = last - knots[m]


def polyline_mean(pts):
    length = 0
    acc = np.zeros(2)
    n,_ = pts.shape
    for i in range(n -1):
        a,b = pts[i + 1], pts[i]
        delta = a - b
        mean = 0.5 * (a + b)
        l = np.sqrt(delta.dot(delta))
        length += l
        acc += l * mean
        
    return length, acc / length


class Segment:

    def __init__(self):
        pass
    def transform(self, matrix):
        """ Transform this object with a 2x3 matrix """
        pass
    def flip(self):
        """ Change the direction of this object """
        pass
    
    def entrance_vector(self, previous, exit_vector = False):
        """ What's the best direction to enter this object, and in what direction
        will we leave it (exit_vector = True). As this isn't really defined for some things,
        we also provide the previous exit vector """
        return np.zeros(2)
    
    def endpoints(self):
        """ What are the start and end points of this object?"""
        pass
    
    def can_join(self, other):
        """ Does joining another object to this one make sense? """
        return False
    
    def length_hash(self):
        """ Used only for speeding up deduplcation - as long as duplicate curves return the same value,
        anything goes. Different curves may also return the same values. """
        return self.mean()[0]

    def mean(self):
        return 0, None

    def add_to_drawing(self, drawing):
        pass

class Point (Segment):

    def __init__(self, coords):
        self.coords = np.array([coords[0],coords[1]])

    def transform(self, matrix):
        self.coords = transform_point(self.coords, matrix)
        
    def entrance_vector(self, previous, exit_vector = False):
        # It doesn't matter what direction we're approaching, so choose the
        # direction we're already going
        if previous is not None:
            return previous
        # Or, if that didn't exist, randomly pick something.
        return np.zeros(2)

    def endpoints(self):
        return self.coords, self.coords

    def mean(self):
        # Don't weight this at all...
        return 0, self.coords

    def add_to_drawing(self, drawing):
            return drawing.add_point(self.coords)
        
    def linearize_to(self, _):
        yield self.coords
        yield self.coords
        
class Polyline (Segment):
    
    def __init__(self, coords):
        self.coords = coords
        self.n,_ = coords.shape

    def flip(self):
        self.coords = np.flip(self.coords, axis = 0)

    def transform(self, matrix):
        self.coords = np.hstack([self.coords, np.ones((self.n,1))]) @ matrix.T
        
    def entrance_vector(self, previous, exit_vector = False):
        v = self.coords[1] - self.coords[0] if not exit_vector else self.coords[-1] - self.coords[-2]        
        return v / math.sqrt(v.dot(v))

    def endpoints(self):
        return self.coords[0], self.coords[-1]

    def can_join(self, other):
        return True # We'll join anything else that can be joined...

    def mean(self):
        n, m = self.coords.shape
        length, center = 0, np.zeros(m)

        for i in range(1,n):
            a,b = self.coords[i], self.coords[i - 1]
            delta = a - b
            l = np.sqrt(delta.dot(delta))
            length += l
            center += l * 0.5 * (a + b)
        if length == 0:
            return 0, self.coords[0,:]

        return length, center / length

    def add_to_drawing(self, drawing):
            return drawing.add_polyline2d(self.coords[:,0:2])

    def linearize_to(self, tolerance):

        n,_ = self.coords.shape
        for i in range(n-1):
            start, end = self.coords[i], self.coords[i + 1]
            delta = end - start
            length = np.sqrt(delta.dot(delta))
            yield start
        
            for x in np.linspace(0, length, int(np.ceil(length / tolerance)) + 1, endpoint = False)[1:]:
                yield start + x * delta
            
        yield end

class BSpline(Segment):
    """ A thin wrapper over NURBS-python's BSpline curve """

    def __init__(self, bspline, tolerance):
        
        self.crv = bspline
        self.pts = np.array(self.crv.ctrlpts)[:,0:2]
        self.tolerance = tolerance
        
    def transform(self, matrix):
        """ Transform this object with a 2x3 matrix """
        n,_ = self.pts.shape
        self.pts = np.hstack([self.pts, np.ones((n,1))]) @ matrix.T
        self.crv.ctrpts = self.pts.tolist()
    
    def flip(self):
        # Simple enough!
        reverse_knot_vector(self.crv.knotvector)
        self.crv.ctrlpts.reverse()
        self.pts = np.flip(self.pts, axis =  0)
    
    def entrance_vector(self, previous, exit_vector = False):
        pts = self.crv.ctrlpts
        a,b = (pts[-1], pts[-2]) if exit_vector else (pts[1], pts[0])
        delta = np.array([a[0] - b[0], a[1] - b[1]])
        delta /= np.sqrt(delta.dot(delta))
        return delta
        
    
    def endpoints(self):
        start,end = self.crv.evaluate_list([0,1])
        return np.array(start[0:2]), np.array(end[0:2])
    
    def can_join(self, other):
        return True
    
    def length_hash(self):
        # Doesn't need to be at all exact - the length of the control points
        # is a good upper bound...
        return polyline_mean(self.pts)[0]

    def mean(self):
        # Compute this a bit more accurately - but not neccesarily at the final resolution
        return polyline_mean(np.array(self.crv.evalpts))

    def linearize_for_drawing(self):

        self.crv.sample_size = max(2, math.ceil(self.length_hash() / self.tolerance))
        return np.array(self.crv.evalpts)[:,0:2]
    
        
class Arc (Segment):
    
    def __init__(self, start, end, center, clockwise = True):
        self.start = start
        self.end = end
        self.center = center
        self.clockwise = clockwise

    def flip(self):
        self.start, self.end = self.end, self.start
        self.clockwise = not self.clockwise

    def transform(self, matrix):

        # Ewww, this is only correct for some matrices. Rethink.

        self.start = transform_point(self.start, matrix)
        self.end = transform_point(self.end, matrix)
        self.center = transform_point(self.center, matrix)

        if subdet(matrix) < 0:
            self.clockwise = not self.clockwise        

    def entrance_vector(self, previous, exit_vector = False):
        flip = not self.clockwise

        v = None

        if not exit_vector:
            v = self.start - self.center
        else:
            v = self.end - self.center
            flip = not flip

        # choose the right matrix...
        v = np.array([v[1],0 - v[0]])
        if flip:
            v *= -1
        if exit_vector:
            v *= -1
            
        return v / math.sqrt(v.dot(v))
    
    def endpoints(self):
        return self.start, self.end

    def can_join(self, other):
        return True # We'll join anything else that can be joined...

    def complexify(self):
        a,b  = self.start - self.center, self.end - self.center
        a,b = a[0] + 1j * a[1], b[0] + 1j * b[1]
        d = b / a
        if self.clockwise:
            d *= -1
        return a,b,d

    def mean(self):
        # Complexify everything
        a,b  = self.start - self.center, self.end - self.center
        a,b = a[0] + 1j * a[1], b[0] + 1j * b[1]
        r = abs(a)
        # Bisect the arc!
        d = cmath.sqrt(b / a) * a
        if self.clockwise:
            d *= -1
        # Compute half of the angle of the arc
        
        alpha = (d.real * a.real + d.imag * a.imag) / (r * abs(d))
        if alpha > 1.0:
            alpha = 1.0
        
        alpha = np.arccos(alpha) #(d.real * a.real + d.imag * a.imag) / (r * abs(d)))
        if alpha < 1e-18:
            return 2 * math.pi * r, self.center
        # Use the cute little integration result to find the centroid
        c = d * np.sin(alpha) / alpha
    
        return 2 * r * alpha, self.center + np.array([c.real, c.imag])

    
    def add_to_drawing(self, drawing):
        
        delta = self.start - self.center
        r = np.sqrt(delta.dot(delta))
        if max(np.abs(self.start - self.end)) < 1e-18:
            return drawing.add_circle(self.center, r)
        else:
            return drawing.add_arc(self.center, np.sqrt(delta.dot(delta)),
                            angle(delta), angle(self.end - self.center),
                            is_counter_clockwise = not self.clockwise)
    def linearize_to(self, tolerance):
        # Complexify everything
        a,b  = self.start - self.center, self.end - self.center
        r = math.sqrt(a.dot(a))


        
        cos = np.arccos(a.dot(b) / math.sqrt(a.dot(a) * b.dot(b)))
            
        det = a[0] * b[1] - a[1] * b[0]

        if det < 0:
            cos = 2 * math.pi - cos
        elif cos < 1e-18:
            cos = 2 * math.pi
            # Ok, that's if the angle is counterclockwise    
        if self.clockwise:
            cos = 2 * math.pi - cos
        start = math.atan2(a[1],a[0])
        span = np.linspace(0, cos, int(0.5 + r * cos / tolerance))
        if self.clockwise:
            span *= -1
            
        for p in span:
            yield self.center + np.array([r * math.cos(start + p),r * math.sin(start + p)])

    def to_polyline(self, tolerance):

        return Polyline(np.array(list(self.linearize_to(tolerance))))
