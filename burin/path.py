from scipy.spatial import KDTree
import numpy as np
import math
from burin.types import pointwise_equal


def clean_paths(paths, link = True, reverse = True, deduplicate = True, merge = True):


    if deduplicate:
        paths = list(remove_duplicates(paths))


    if link:
        paths = list(link_paths(paths, reverse = reverse))

    
    if merge is not None:
        return list(merge_paths(paths, merge))
    else:
        return list([p] for p in paths)


    
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

    if n < 2:
        for p in paths:
            yield p
        return

    live = np.ones(2 * n, dtype = int) # Twice as large, so we can use it as mask

    # If we want to preserve direction, just make sure we'll never see endpoints in our queries
    if not reverse:
        live[1::2] = 0
        
    endpoints = np.empty((2 * n, 2))
    for i, path in enumerate(paths):
        a,b = path.endpoints()
        endpoints[2 * i, :] = a[0], a[1]
        endpoints[2 * i + 1, :] = b[0], b[1]
        
    real_indexes = np.arange(len(live)) # Original indexes
    # Start with the first path provided - you have to start somewhere...
    yield paths[0]
    live[0:2] = 0
    prev = 1 # index into endpoints
    exit_vector = -1 * paths[0].entrance_vector(None, True)
    
    # Build the tree for the first time
    tree = KDTree(endpoints[live == 1,:])
    indexes = real_indexes[live == 1]
    
    while n > 1:
        rebuild = True
        
        query = tree.query(endpoints[prev], k = k)
        result = rank_paths(query, live, exit_vector, paths, indexes)

        if result is not None:
            rebuild = False
            path, base, parity = result
            exit_vector = -1 * path.entrance_vector(exit_vector, parity == 0)
            # Emit the section with correct flipping
            if parity:
                path.flip()
                
            yield path
    
            # Set both of its ends as dead
            live[base] = 0
            live[base + 1] = 0
                
            prev = base + 1 - parity
            n -= 1
        
                
        if rebuild:
            if log_rebuilds:
                print(f"Rebuilding ({n} / {len(paths)})")
            tree = KDTree(endpoints[live == 1,:])
            indexes = real_indexes[live == 1]

def direction_vector(previous_vector, path, parity):
    n,_ = path.shape

    if n == 1:
        if previous_vector is not None:
            # If we're using this for ranking candidates, we should always go with a point!
            # Otherwise, if we're using this for the next round, a point doesn't change the
            # backlash state, so we leave it unchanged
            return previous_vector
        else:
            # Only happens if a point is the first segment
            # and doesn't really matter
            return np.zeros(2)
    v = None
    if parity:
        v = path[1] - path[0] 
    else:
        v = path[-2] - path[-1]

    norm = math.sqrt(v.dot(v))
    if norm != 0:
        return v / norm
    
    return v # Again, zero vectors aren't horrid here
    

            
def rank_paths(query_results,live,vector, paths, indexes, epsilon = 1e-10):
    """ If there are live vectors at 0 distance, return the one 
    pointing in the best direction. Otherwise, the closest"""
    dist, points = query_results
    best = None
    best_cosine = -1 # aka the worst cosine ever
    
    for i,pt in enumerate(points):
        # Figure out if the point is close and still alive?
        close = dist[i] < epsilon
        idx = indexes[pt]
        parity = idx % 2 # Are we looking at the start or the end?
        base = idx - parity # The index of the start
        alive = live[base]
        
        if close:
            if not alive:
                continue
            path = paths[base // 2]

            cosine = path.entrance_vector(vector, parity == 1).dot(vector)
            
            if best_cosine <= cosine:
                best_cosine = cosine
                best = path, base, parity

        else:
            if best is not None:
                return best
            if alive:
                return paths[base // 2], base, parity
        
    
    if best is not None:
        return best
    

def merge_paths(paths, staydown):
    """ Takes a generator of ordered paths and joins segments connected only
    by short rapids """
    staydown = staydown**2

    point, group, prev = None, None, None

    for p in paths:
        # Start a new group!
        if prev is None:
            group = [p]
            prev = p
            point = p.endpoints()[1]
            continue

        start, end = p.endpoints()
        delta = point - start
        
        if delta.dot(delta) < staydown and prev.can_join(p) and p.can_join(prev):
            point = end
            group.append(p)
            prev = p
        else:
            yield group
            group = [p]
            point = end
            prev = p
            
    if group is not None:
        yield group
        


def find_runs(lengths, epsilon):
    idx = np.argsort(lengths)
    start_i = idx[0]
    start = lengths[start_i]
    acc = [start_i]
    
    for i in idx[1:]:
        length = lengths[i]
        if length - start < epsilon:
            acc.append(i)
        else:
            if len(acc) > 1:
                yield acc
            acc = [i]
            start = length
            
    if len(acc) > 1:
        yield acc
        
def tree_search_endpoints(paths, group, epsilon):
    n = len(group)
    points = np.empty((n,4))
    # Put all of the paths into a kd-tree as 4d points
    # representing the box spanned by their endpoints
    for i, g in enumerate(group):
        p = paths[g]
        (a,b),(c,d)= p.endpoints()
        points[i] = min(a,c), max(a,c), min(b,d), max(b,d)
    live = np.ones(n, dtype = int)
    tree = KDTree(points)
    
    for i in range(n):
        if not live[i]:
            continue
        results = tree.query_ball_point(points[i],epsilon)
        if len(results) < 2:
            continue
        # Check each close point - if they're equal
        # (max norm pointwise), it's a duplicate and thus must die...
        for j in results:
            if j <= i:
                continue
            pi, pj = paths[group[i]], paths[group[j]]
            if pointwise_equal(pi,pj, epsilon):
                live[j] = 0
                
    return live


def remove_duplicates(paths, epsilon = 1e-6):
    n = len(paths)

    if n < 2:
        for p in paths:
            yield p
        return
            
    keep = np.ones(n, dtype = int)
    lengths = np.empty(n)
    for i in range(n):
        lengths[i] = paths[i].length_hash()
    
    for group in find_runs(lengths, epsilon):
        if len(group) == 2:
            i,j = group
            if pointwise_equal(paths[i],paths[j],epsilon):
                keep[j] = 0
            continue
    
        for i, v in enumerate(tree_search_endpoints(paths, group, epsilon)):
            keep[group[i]] = v
            
    for i,v in enumerate(keep):
        if v:
            yield paths[i]

def reduce_points(pts, ball):
    """ Preserves start and end, but reduces small segments. No
    great theoretical basis and it preserves nothing else - length etc.."""
    last = next(pts)
    segment = [last]
    ball = ball ** 2
    
    for pt in pts:
        delta = last - pt
        if ball <= delta.dot(delta):
            segment.append(pt)
            last = pt
            
    if delta.dot(delta) > 1e-18:
        segment.append(pt)
        
    return np.array(segment)
