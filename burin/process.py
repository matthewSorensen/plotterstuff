def cannonical_order(layers):
    """ Take a bunch of layer names, and sort them consistently - first, all of the
    layer names that are parsable as integers, in ascending order. Then, the rest of the layer names,
    in lexicographical order.
    """

    good, bad = [], []
    for l in layers:
        try:
            good.append((l,int(l)))
        except:
            bad.append(l)
    return [x[0] for x in sorted(good, key = lambda x: x[1])] + list(sorted(bad))



class BaseProcess:

    def __init__(self):
        self.parameters = {}

    def conversion_parameters(self):
        # Right now, two configurable parameters - should we convert arcs to line segments,
        # and how long (maximum) should line segments generated from curves be?
        return {'arcs' : True, 'resolution' : 0.25}


    def layers_to_units(self, layers):
        """ Define what order layers are processed in, and which layers of geometry get
        proccessed together. 
        
        Return a list of dicts containing the following fields:

        * 'name' - the unit name
        * 'subunits' - list of subunits: tuples of (name,list of layers). All geometry in a given subunit
           will be optimized together, and passed to the code generator.
        * 'parameters' - a list of parameters to be collected at runtime, immediately
           before running the pipeline for a unit. Accessible as self.parameters['unit_name']['parameter_name'].

        """
        return [{"name": "all", "subunits" : [("all", layers)], "parameters" : []}]

    def modify_geometry(self, unit_name, geometry):
        """ Gives processes access to geometry after conversion to line segments, but before
        linking and optimization. """
        return geometry
    
    def geometry_parameters(self, unit_name):
        """ How should we process each layer - specifies a line segment length for conversion from
        dxf geometry, and all of the parameters to the linker/optimizer/cleaner. """
        return {'link': True, 'reverse' : True,
                'deduplicate' : True, 'merge' : 0.1}

    def generate_code(self, unit_name, segments):
        """ Generate a stream of gcode from a list of numpy array path segments """
        yield "; Nothing to see here!"


    # No need to override this for customization
    def subunit_position(self,name):
        """ Returns a pair of booleans, indicating if the specified subunit is the first (1st return value),
        and last (2nd) subunit in its unit """
        unit,sub = name
        subunits = self.units[self.stage[unit]]['subunits']
        
        return sub == subunits[0][0], sub == subunits[-1][0] 
