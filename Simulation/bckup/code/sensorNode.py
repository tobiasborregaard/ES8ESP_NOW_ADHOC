from shapely.geometry import LineString
import numpy as np
import time
import math
import random

scale_m_per_px = 0.9 / 55
area_per_px_m2 = scale_m_per_px ** 2       # m² per pixel
spacing_margin_px = int(1 / scale_m_per_px)



def trilaterate_relative(a, b, c):
    """
    Given distances:
    a = self to neighbor (placed at (a, 0))
    b = self to router
    c = neighbor to router

    Returns: (x, y) coordinates of router relative to self at (0, 0)
    """
    x = (a**2 + b**2 - c**2) / (2 * a)
    y_squared = b**2 - x**2
    if y_squared < 0:
        y = 0  # or raise an error if geometry is impossible
    else:
        y = math.sqrt(y_squared)

    return (x, y)



def angle_between(v1, v2):
    dot = np.dot(v1, v2)
    norms = np.linalg.norm(v1) * np.linalg.norm(v2)
    return math.degrees(math.acos(dot / norms))


def fspl_with_walls(distance_m, freq_mhz=2400, n=3.0, d0=1.0,
                        walls_crossed=0, wall_penalty_db=3,
                        fading_std_db=4, include_fading=True):
    """
    Log-distance path loss model with wall penalty and optional shadow fading.
    """
    if distance_m < d0:
        distance_m = d0
    # Reference FSPL at d0
    pl_d0 = 20 * math.log10(d0) + 20 * math.log10(freq_mhz) - 27.55
    # Distance-based loss
    path_loss = pl_d0 + 10 * n * math.log10(distance_m / d0)
    # Add wall attenuation
    wall_loss = walls_crossed * wall_penalty_db
    # Add fading
    fading = random.gauss(0, fading_std_db) if include_fading else 0
    total_loss = path_loss + wall_loss + fading
    return total_loss

def bresenham_line(x0, y0, x1, y1):
    """Returns list of (x, y) from A to B using Bresenham's algorithm."""
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = x0, y0
    sx = -1 if x0 > x1 else 1
    sy = -1 if y0 > y1 else 1
    if dx > dy:
        err = dx / 2.0
        while x != x1:
            points.append((x, y))
            err -= dy
            if err < 0:
                y += sy
                err += dx
            x += sx
    else:
        err = dy / 2.0
        while y != y1:
            points.append((x, y))
            err -= dx
            if err < 0:
                x += sx
                err += dy
            y += sy
    points.append((x1, y1))
    return points, math.sqrt(np.pow(dx,2) + np.pow(dy,2))*scale_m_per_px

class MSG: 
    def __init__(self, rx, tx, message):
        self.rx = rx
        self.tx = tx
        self.message = message

class SensorNode:
    def __init__(self, id, x, y, node_type="sensor", label=""):
        self.id = id
        self.location = (x, y)
        self.type = node_type
        self.label = label
        self.neighbors = []
        self.received_data = []
        self.sent_data = False
        self.transmitPower = 16  # in dbm
        self.network = []
        self.ignore = []
        self.links = {}

    def inRange(self,node,wallMask):
        nx, ny = node.location
        sx,sy = self.location
        line_points, distance = bresenham_line(sx, sy, nx, ny)
        deBounce = 0
        inWall = False
        timesCrossed = 0
        cooldown = 10  # how many pixels must pass before we count a new wall
        

        for x, y in line_points:
            if wallMask[y, x] == 1:  # inside wall
                if not inWall and deBounce <= 0:
                    timesCrossed += 1
                    inWall = True
                    deBounce = cooldown  # wait before counting again
            else:  # not in wall
                inWall = False
                if deBounce > 0:
                    deBounce -= 1 
        fspl =  fspl_with_walls(distance, walls_crossed=timesCrossed)
        # logDist = log_distance_path_loss(distance_m=distance,  walls_crossed=timesCrossed)
        print(f"{fspl:.2f} db, at distance {distance:.2f} m, crossed: {timesCrossed} times, between {self.label} and {node.label}")
        return fspl
        

    

    def discoveryMode(self, all_nodes, wall_mask, rx_sensitivity=-70):
        for node in all_nodes:
            if node.id == self.id:
                continue

            # --- compute link margin ---
            pl = self.inRange(node=node, wallMask=wall_mask)
            margin = self.transmitPower - pl    # dBm at receiver

            # --- store quality and decide if usable ---
            if margin >= abs(rx_sensitivity):
                self.neighbors.append(node.id)
                self.links[node.id] = margin     # remember quality
            else:
                self.ignore.append(node.id)

    def selectBestHop(self, all_nodes, router=None):
        if router is None:
            return None

        best_id = None
        smallest_angle = 180

        c = router.RSSI2NodesList.get(self.id, None)  # self to router

        for node in all_nodes:
            if node.id == self.id or node.id not in self.links:
                continue

            a = router.RSSI2NodesList.get(node.id, None)  # neighbor to router
            b = self.links.get(node.id, None)             # self to neighbor

            if None in (a, b, c):
                continue

            try:
                # Law of Cosines: angle at self (in degrees)
                cos_theta = (a**2 + b**2 - c**2) / (2 * a * b)
                cos_theta = max(-1.0, min(1.0, cos_theta))  # safe clip
                angle = math.degrees(math.acos(cos_theta))

                if angle < smallest_angle:
                    smallest_angle = angle
                    best_id = node.id
            except:
                continue

        return best_id or router.id
                    
            
        

    
    
    def transmit(self, to, message):
        if to:
            print(f"{self.label} sent message to {to.label}")
            msg = MSG(rx=to.id, tx=self.id, message=message)
            to.receive(msg)
            self.sent_data = True


    def acknowledge(self,who):
        pass
    
    def receive(self, msg: MSG):
        if msg.tx not in self.received_data:
            print(f"{self.label} received message from {msg.tx}")
            self.received_data.append(msg.tx)
 

class Router(SensorNode):
    def __init__(self, id, x, y, node_type="router", label="router"):
        super().__init__(id, x, y, node_type=node_type, label=label)
        self.receivedMessages = []
        self.RSSI2NodesList = {}
        
    def receive(self, msg):
        if msg.tx not in [m.tx for m in self.receivedMessages]:
            print(f"Router {self.label} received message from node {msg.tx}")
            self.receivedMessages.append(msg)

    def logData():
        pass
