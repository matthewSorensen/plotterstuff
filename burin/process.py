
class BaseProcess:

    def __init__(self):
        self.parameters = {}

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

    def curve_resolution(self, unit_name):
        """ How precisely should we convert curves to line segments? """

        return 0.25
    
    def geometry_parameters(self, unit_name):
        """ How should we process each layer - specifies a line segment length for conversion from
        dxf geometry, and all of the parameters to the linker/optimizer/cleaner. """
        return {'link': True, 'reverse' : True,
                'deduplicate' : True,
                'merge' : True, 'reduce' : None}

    def generate_code(self, unit_name, segments):
        """ Generate a stream of gcode from a list of numpy array path segments """
        yield "; Nothing to see here!"
