import numpy as np
import cv2
import picamera
from time import sleep
    
from machine_interface import MachineConnection


def CMSL(img, window):
    """
        Contrast Measure based on squared Laplacian according to
        'Robust Automatic Focus Algorithm for Low Contrast Images
        Using a New Contrast Measure'
        by Xu et Al. doi:10.3390/s110908281
        window: window size= window X window"""
    ky1 = np.array(([0.0, -1.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.0]))
    ky2 = np.array(([0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, -1.0, 0.0]))
    kx1 = np.array(([0.0, 0.0, 0.0], [-1.0, 1.0, 0.0], [0.0, 0.0, 0.0]))
    kx2 = np.array(([0.0, 0.0, 0.0], [0.0, 1.0, -1.0], [0.0, 0.0, 0.0]))
    g_img = abs(cv2.filter2D(img, cv2.CV_32F, kx1)) + \
                abs(cv2.filter2D(img, cv2.CV_32F, ky1)) + \
                abs(cv2.filter2D(img, cv2.CV_32F, kx2)) + \
                abs(cv2.filter2D(img, cv2.CV_32F, ky2))

    filtered = cv2.boxFilter(g_img * g_img,-1,(window, window),normalize=True)

    return np.abs(filtered.sum(axis = 2))

def nearest_point_finder(shape, radius):
    n,m = shape
    distance = (np.outer((np.arange(n) - n // 2)**2, np.ones(m)) 
                + np.outer(np.ones(n),(np.arange(m) - m // 2)**2)).flatten()
    coords = np.argsort(distance)
    # Only take those within a certain distance
    coords = coords[0:np.searchsorted(distance[coords], radius ** 2)]

    def finder(image):
        ef = image.flatten()
        for i, x in enumerate(coords):
            if ef[x]:
                return np.unravel_index(x, shape)
        return None
    
    return finder



def get_frame(camera):

    a,b = camera.resolution
    n,m = a + (16 - a % 16), b + (32 - b % 32)

    output = np.empty((n * m * 3,), dtype = np.uint8)
    camera.capture(output, 'bgr')

    return output.reshape((m,n,3))[0:b,0:a,:]


def binary_search(machine, oracle, start, direction, length, cutoff = 0.5):

    a,b = start, start + direction * length
    last_miss = None

    while length > cutoff:
        new = 0.5 * (a + b)
        length *= 0.5
        machine.move(new)

        if oracle() is not None:
            print("hit", new)
            a = new
        else:
            print("miss", new)
            b = new
            last_miss = new

    if last_miss is not None:
        m.move(last_miss - 0.5 * cutoff * direction)
        return True
    
    return False
    


def defocus_level(camera, machine, distance = 5, cutoff = 0.999):

    z_start = machine.xyzu()[2]

    m.move(Z = z_start + distance)
    frame = CMSL(get_frame(camera), 20)
    s = frame.shape
    m.move(Z = z_start)
    frame = frame.flatten()

    return frame[np.argsort(frame)[int(cutoff * len(frame))]], s


with picamera.PiCamera() as camera:
    camera.resolution = (1012, 760)
    camera.framerate = 25
    camera.sensor_mode = 4

    #camera.iso = 200
    # Wait for the automatic gain control to settle

    with MachineConnection('/var/run/dsf/dcs.sock') as m:

        sleep(2)
        # Now fix the values
        #camera.shutter_speed = 16666 #camera.exposure_speed
        #print(camera.shutter_speed)
        #camera.exposure_mode = 'off'
        #g = camera.awb_gains
        #camera.awb_mode = 'off'
        #camera.awb_gains = g

    
        level, shape = defocus_level(camera, m)
        finder = nearest_point_finder(shape, 200)

        def oracle():
            return finder(CMSL(get_frame(camera), 20) > level)
        

        start = m.xyzu()[0:2]
        binary_search(m, oracle, start, np.array([-1,0]), 60)
        

        
        frame = CMSL(get_frame(camera), 20) > level
        img = 128 * frame.astype("uint8")
        cv2.imwrite(f"edge_finding/initial.png", img)
            
        x,y = m.xyzu()[0:2]

        for i in range(5):

            frame = CMSL(get_frame(camera), 20) > level
            py,px = finder(frame)


            pix_per_mm = 760.0 / (4.7 / 2)
            scale = 0.75
            
            x +=  scale * (px - 1012 // 2) / pix_per_mm
            y +=  scale * (py - 760 // 2) / pix_per_mm
            
            img = 128 * frame.astype("uint8")
            img[px,py] = 255
            img[760 // 2, 1012 // 2] = 255
            cv2.imwrite(f"edge_finding/{i}.png", img)

            m.move(X = x, Y = y)
            

        m.move(start)
