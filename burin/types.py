import numpy as np
import math

def transform_point(point, matrix):
    return matrix @ np.hstack([point,1]).T

def subdet(m):
    return m[0,0] * m[0,1] - m[0,1] * m[1,0]


def pointwise_equal(a,b, epsilon):

    if a.__class__ != b.__class__:
        return False

    if isinstance(a, Point) or isinstance(a, Polyline):

        if len(a.coords) != len(b.coords):
            return False
        
        return np.all(np.abs(a.coords - b.coords) < epsilon)

    elif isinstancef(a, Arc):

        delta = max(np.max(np.abs(a.start - b.start)),
                    np.max(np.abs(a.end - b.end)),
                    np.max(np.abs(a.center - b.center)))

        return delta < epsilon and a.clockwise == b.clockwise

    return False

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
        return 0


class Point (Segment):

    def __init__(self, coords):
        self.coords = np.array([coords[0,0],coords[0,1]])

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

    
class Polyline:
    
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

    def length_hash(self):
        acc = 0
        n, _ = self.coords.shape
        for i in range(1,n):
            delta = self.coords[i] - self.coords[i - 1]
            acc += np.sqrt(delta.dot(delta))
        return acc
        
class Arc:
    
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
            
        return v / math.sqrt(v.dot(v))
    
    def endpoints(self):
        return self.start, self.end

    def can_join(self, other):
        return True # We'll join anything else that can be joined...

    
    def length_hash(self):
        ab, bc, ca = self.start - self.center, self.center - self.end, self.end - self.start
        
        return math.sqrt(ab.dot(ab)) + math.sqrt(bc.dot(bc)) + math.sqrt(ca.dot(ca))
