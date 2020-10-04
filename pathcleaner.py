from scipy.spatial import KDTree
import numpy as np

# We are highly lazy and pragmatic, and are gonna do something stupid with pretending scikit's
# KDTrees are dynamic...
def link_paths(paths, reverse = True, k = 20, log_rebuilds = False):
    
    """ Takes a bunch of paths and orders them in a reasonable way - locally minimizing
    travel to the next path. Reasonable, not optimum, however.
    
    If reverse is true, it will reverse the travel direction of segments if that improves
    results. 

    k is the number of results to return from spatial queries - larger k means
    fewer reindexings, but more (fast!) linear searching in results. """


    
    n = len(paths)
    live = np.ones(2 * n, dtype = int) # Twice as large, so we can use it as mask

    # If we want to preserve direction, just make sure we'll never see endpoints in our queries
    if not reverse:
        live[1::2] = 0
        
    endpoints = np.empty((2 * n, 2))
    for i, path in enumerate(paths):
        endpoints[2 * i, :] = path[0]
        endpoints[2 * i + 1, :] = path[-1]
    real_indexes = np.arange(len(live)) # Original indexes
    # Start with the first path provided - you have to start somewhere...
    yield paths[0]
    live[0:2] = 0
    prev = 1 # index into endpoints

    # Build the tree for the first time
    tree = KDTree(endpoints[live == 1,:])
    indexes = real_indexes[live == 1]
    
    while n > 1:
        rebuild = True
        for pt in tree.query(endpoints[prev], k = k)[1]:
            idx = indexes[pt]
            parity = idx % 2 # Are we looking at the start or the end?
            base = idx - parity # The index of the start
            if live[base]:
                # We found a live point in our k!
                rebuild = False
                # Emit the segment, with correct flipping
                if parity:
                    yield np.flip(paths[base // 2], axis = 0)
                else:
                    yield paths[base // 2]
                # Set both of its ends as dead
                live[base] = 0
                live[base + 1] = 0
                
                prev = base + 1 - parity
                n -= 1
                break
                
        if rebuild:
            if log_rebuilds:
                print(f"Rebuilding ({n} / {len(paths)})")
            tree = KDTree(endpoints[live == 1,:])
            indexes = real_indexes[live == 1]


def merge_paths(paths, staydown):
    """ Takes a generator of ordered paths and joins segments connected only
    by short rapids """
    staydown = staydown**2
    prev = [next(paths)]

    for p in paths:
        # We know this is shorter than to the end point, if
        # the linking algorithm was used
        delta = prev[-1][-1] - p[0]
        if delta.dot(delta) < staydown:
            prev.append(p)
        else:
            yield np.concatenate(prev)
            prev = [p]
            
    yield np.concatenate(prev)

