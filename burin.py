#!/usr/bin/env python3
import click
import json
import os
import shutil

import pathcleaner
import dxfloader
import importlib

#import processes

def get_blob(directory):
    blob = os.path.join(directory,"state.json")
    if not os.path.exists(blob):
        print(f"Unable to find workflow state {blob}")
        exit(-1)
    with open(blob,"r") as f:
        return json.load(f)
    
def save_blob(directory, blob):
    # Make sure that the output directory is actually a thing
    if not os.path.exists(directory):
        os.mkdir(directory)
    elif not os.path.isdir(directory):
        print(f"Output directory '{directory}' already exists, but is not a directory")
        exit(-1)
        
    blob_path = os.path.join(directory,"state.json")
    with open(blob_path,'w') as f:
        json.dump(blob, f)
        
    return blob_path

def load_process(process):
    splat = process.split('.')
    module,clss = '.'.join(splat[:-1]), splat[-1]

    try:
        mod = importlib.import_module(module)
    except:
        print(f"Unable to find module {module}")
        exit(-1)

    if clss not in mod.__dict__:
        print(f"Unable to find process {clss} in module {module}")
        exit(-1)
        
    return mod.__dict__[clss]()

    
def check_parameters(blob, unit,prompt = True, reset = False):

    stages, parameters, units = blob['stage'], blob['parameters'], blob['units']
    ok,updated = True,False

    # If we're resetting parameters for this layer, purge the old ones
    if reset and (unit in parameters):
        parameters[unit] = {}
        updated = True
    # Go through all of the previous units (+ the current) and make
    # sure all of the required parameters are there
    for i in range(0, 1 + stages[unit]):
        u = units[i]
        name = u['name']
        if name not in parameters:
            parameters[name] = {}
        scope = parameters[name]
        for p in u['parameters']:
            if p not in scope:
                if prompt:
                    scope[p] = input(f"Parameter {p} for unit {name}: ").strip()
                    updated = True
                else:
                    ok = False
                    
    return ok, updated

        
@click.group()
@click.pass_context
def main(ctx):    
    pass

@main.command()
@click.argument('filepath')
@click.argument('process')
@click.argument('directory')
@click.pass_context
def start(ctx, filepath, process, directory):

    if not os.path.exists(filepath):
        print(f"Input file {filepath} doesn't exist")
         
    
    proc = load_process(process)

    # Establish that the output directory exists by saving a blank conf
    save_blob(directory, {})

    shutil.copy(filepath, os.path.join(directory, 'input.dxf'))
    layers = dxfloader.load_layers(filepath)
    units = proc.layers_to_units(layers)
    # Make sure we didn't declare any units twice...
    stage, names = {}, []
    for i,u in enumerate(units):
        name = u['name']
        names.append(name)
        if name in stage:
            print(f"Invalid process - unit {name} declared twice")
            exit(-1)
        stage[name] = i
    
    print("Found workflow units:")
    for n in names:
        print(f"    {n}")
    # Build a json blob containing the state of the current execution flow...
    blob = {'process' : process, 'units' : units, 'parameters' : {}, 'stage': stage}
    #... and put it in the output directory
    print(f"Wrote workflow state to {save_blob(directory, blob)}")
    
@main.command()
@click.argument('directory')
@click.pass_context
def list(ctx, directory):
    blob = os.path.join(directory,"state.json")
    if not os.path.exists(blob):
        print(f"Unable to find workflow state {blob}")
    
    with open(blob,"r") as f:
        blob = json.load(f)
        
    print("Workflow units:")
    for u in blob['units']:
        print(f"    {u['name']}")
 

@main.command()
@click.argument('unit')
@click.argument('directory')
@click.pass_context
def unit(ctx, unit, directory):
    
    state = get_blob(directory)

    if unit not in state['stage']:
        print(f"Can't find unit {unit}")
        exit(-1)

    # do magic to load the process def from the string in the json...
    proc = load_process(state['process'])
    
        
    unit_record = state['units'][state['stage'][unit]]
    
    # should have optional flags here - reset current parameters, and prompt or just fail
    ok, new = check_parameters(state, unit)

    if new:
        save_blob(directory, state)
    if not ok:
        print(f"Unspecified parameters for unit {unit}")
        exit(-1)

    # Load all of the dxf entities we'll need for this unit
    dxf_entities, errors = dxfloader.load_entities(os.path.join(directory, 'input.dxf'),
                                                   set().union(*(set(x) for _,x in unit_record['subunits'])))
    if errors:
        print("Error loading dxf:")
        for x in errors:
            print("    ", x)
        exit(-1)
    # Give the newly-reconstituted process a little context as to what's happening
    proc.parameters = state['parameters']
    proc.units = state['units']

    
    with open(os.path.join(directory, unit + ".gcode"),'w') as f:
        
        for subname, layers in unit_record['subunits']:
            full_name = unit, subname
            gparameters = proc.geometry_parameters(full_name)
            tol = gparameters['tolerance']
            del gparameters['tolerance']

            geo = []
            for layer in layers:

                for entity in dxf_entities[layer]:
                    geo.append(entity.render_to_tolerance(tol))
            
            optimized = pathcleaner.clean_paths(geo,**gparameters)
            for x in proc.generate_code(full_name, optimized):
                f.write(x + '\n')


        
    
if __name__ == '__main__':
    main(obj = {})
