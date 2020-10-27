import ezdxf
import numpy as np
from collections import defaultdict

import burin.dxftypes as dxftypes


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
            objects[key].append(dxftypes.Polyline(np.array([e.dxf.start, e.dxf.end])))
        elif isinstance(e,ezdxf.entities.Polyline):
            if e.dxf.flags > 1:
                errors.append(("Unsupported polyline flags",e.dxf.handle))
            else:
                objects[key].append(dxftypes.Polyline.from_dxf(e))
                
        elif isinstance(e, splinable):
            # If we do this, it magically converts the object to a spline
            # and appends it to the end of the file (instead of in place),
            # so we don't have to worry at all!
            e.to_spline(replace = False)
        elif isinstance(e, ezdxf.entities.Spline):
            objects[key].append(dxftypes.Spline.from_dxf(e))
        elif isinstance(e, ezdxf.entities.Point):
            objects[key].append(dxftypes.Point.from_dxf(e))
        else:
            errors.append((f"Unsupported dxf object - {e}",e.dxf.handle))
            
    return dict(objects), errors
