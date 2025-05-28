# import pygame
# import cv2
# import json
# import numpy as np
# import math
# import random
# import networkx as nx

# # === Constants ===
# WIDTH, HEIGHT = 1200, 941
# NODE_RADIUS = 10
# SCALE_M_PER_PX = 0.9 / 55
# RX_SENSITIVITY = -70  # dBm

# # === Utility Functions ===
# def fspl_with_walls(distance_m, freq_mhz=2400, n=3.0, d0=1.0,
#                     walls_crossed=0, wall_penalty_db=3,
#                     fading_std_db=4, include_fading=True):
#     if distance_m < d0:
#         distance_m = d0
#     pl_d0 = 20 * math.log10(d0) + 20 * math.log10(freq_mhz) - 27.55
#     path_loss = pl_d0 + 10 * n * math.log10(distance_m / d0)
#     wall_loss = walls_crossed * wall_penalty_db
#     fading = random.gauss(0, fading_std_db) if include_fading else 0
#     return path_loss + wall_loss + fading

# def bresenham_line(x0, y0, x1, y1):
#     points = []
#     dx = abs(x1 - x0)
#     dy = abs(y1 - y0)
#     x, y = x0, y0
#     sx = -1 if x0 > x1 else 1
#     sy = -1 if y0 > y1 else 1
#     if dx > dy:
#         err = dx / 2.0
#         while x != x1:
#             points.append((x, y))
#             err -= dy
#             if err < 0:
#                 y += sy
#                 err += dx
#             x += sx
#     else:
#         err = dy / 2.0
#         while y != y1:
#             points.append((x, y))
#             err -= dx
#             if err < 0:
#                 x += sx
#                 err += dy
#             y += sy
#     points.append((x1, y1))
#     return points, math.sqrt(dx**2 + dy**2) * SCALE_M_PER_PX

# # === Message Class ===
# class MSG:
#     def __init__(self, rx, tx, message):
#         self.rx = rx
#         self.tx = tx
#         self.message = message

# # === Sensor Node Classes ===
# class SensorNode:
#     def __init__(self, id, x, y, node_type="sensor", label=""):
#         self.id = id
#         self.location = (x, y)
#         self.type = node_type
#         self.label = label
#         self.isRouter = (node_type == "router")
#         self.received_data = []
#         self.sent_data = False
#         self.transmitPower = 16  # dBm
#         self.links = {}  # neighbor_id -> margin

#     def inRange(self, node, wallMask):
#         nx, ny = node.location
#         sx, sy = self.location
#         line_points, distance = bresenham_line(sx, sy, nx, ny)
#         deBounce, inWall, timesCrossed = 0, False, 0
#         cooldown = 10
#         for x, y in line_points:
#             if 0 <= y < wallMask.shape[0] and 0 <= x < wallMask.shape[1]:
#                 if wallMask[y, x] == 1:
#                     if not inWall and deBounce <= 0:
#                         timesCrossed += 1
#                         inWall = True
#                         deBounce = cooldown
#                 else:
#                     inWall = False
#                     if deBounce > 0:
#                         deBounce -= 1
#         fspl = fspl_with_walls(distance, walls_crossed=timesCrossed)
#         return fspl

#     def discoveryMode(self, all_nodes, wall_mask, rx_sensitivity=RX_SENSITIVITY):
#         for node in all_nodes:
#             if node.id == self.id:
#                 continue
#             pl = self.inRange(node=node, wallMask=wall_mask)
#             margin = self.transmitPower - pl
#             if margin >= rx_sensitivity:
#                 self.links[node.id] = margin

#     def transmit_path(self, path, nodes):
#         for i in range(1, len(path)):
#             src = nodes[path[i-1]]
#             dst = nodes[path[i]]
#             print(f"{src.label} sent message to {dst.label}")
#             msg = MSG(rx=dst.id, tx=src.id, message="data")
#             dst.receive(msg)
#         self.sent_data = True

#     def receive(self, msg: MSG):
#         if msg.tx not in self.received_data:
#             print(f"{self.label} received message from {msg.tx}")
#             self.received_data.append(msg.tx)

# class Router(SensorNode):
#     def __init__(self, id, x, y, node_type="router", label="router"):
#         super().__init__(id, x, y, node_type=node_type, label=label)
#         self.receivedMessages = []

#     def receive(self, msg):
#         if msg.tx not in [m.tx for m in self.receivedMessages]:
#             print(f"Router {self.label} received message from node {msg.tx}")
#             self.receivedMessages.append(msg)

# class Network:
#     def __init__(self, nodes, wall_mask):
#         self.nodes = nodes
#         self.wall_mask = wall_mask
#         self.graph = nx.Graph()
#         self.sink_id = self.find_sink()

#     def find_sink(self):
#         routers = [n.id for n in self.nodes if n.isRouter]
#         return routers[0] if routers else None

#     def discover_links(self):
#         for node in self.nodes:
#             node.links = {}  # clear old links
#             if node.awake:  # only discover if awake
#                 node.discoveryMode(self.nodes, self.wall_mask)

#     def build_graph(self):
#         self.graph.clear()
#         for node in self.nodes:
#             for neighbor_id, margin in node.links.items():
#                 self.graph.add_edge(node.id, neighbor_id, weight=-margin)

#     def route_all(self):
#         for node in self.nodes:
#             if not node.isRouter and node.awake and not node.sent_data:
#                 try:
#                     path = nx.shortest_path(self.graph, source=node.id, target=self.sink_id, weight='weight')
#                     node.transmit_path(path, self.nodes)
#                 except nx.NetworkXNoPath:
#                     print(f"No path from {node.label} to router.")

# # === Visualization ===
# def drawline(screen, node1, node2):
#     pygame.draw.line(screen, (0, 255, 0), node1.location, node2.location, 2)

# # === Simulation Main ===
# def run_simulation():
#     pygame.init()
#     screen = pygame.display.set_mode((WIDTH, HEIGHT))
#     pygame.display.set_caption("Node Network Simulation")
#     clock = pygame.time.Clock()

#     background = pygame.image.load("images/overlay.png")
#     wall_img = cv2.imread("images/wallsTrans.png", cv2.IMREAD_UNCHANGED)
#     wall_mask = (wall_img[:, :, 3] > 128).astype(np.uint8)

#     # Load nodes
#     with open("json/sensorNodes.json", "r") as f:
#         data = json.load(f)
#     nodes = []
#     for i, entry in enumerate(data):
#         NodeClass = Router if entry.get("type") == "router" else SensorNode
#         node = NodeClass(
#             id=i,
#             x=entry["x"],
#             y=entry["y"],
#             node_type=entry.get("type", "sensor"),
#             label=entry.get("room", "")
#         )
#         nodes.append(node)

#     # One-time discovery
#     for node in nodes:
#         node.discoveryMode(nodes, wall_mask)

#     # Build graph from links
#     G = nx.Graph()
#     for node in nodes:
#         for neighbor_id, margin in node.links.items():
#             G.add_edge(node.id, neighbor_id, weight=-margin)  # lower weight = better margin

#     # Find router(s)
#     router_ids = [n.id for n in nodes if n.isRouter]
#     if not router_ids:
#         print("No router found.")
#         return
#     sink_id = router_ids[0]

#     # Route and transmit
#     for node in nodes:
#         if not node.isRouter:
#             try:
#                 path = nx.shortest_path(G, source=node.id, target=sink_id, weight='weight')
#                 node.transmit_path(path, nodes)
#             except nx.NetworkXNoPath:
#                 print(f"No path from {node.label} to router.")

#     # Pygame loop
#     running = True
#     while running:
#         screen.blit(background, (0, 0))
#         for event in pygame.event.get():
#             if event.type == pygame.QUIT:
#                 running = False

#         font = pygame.font.SysFont(None, 20)
#         for node in nodes:
#             if node.sent_data and not node.isRouter:
#                 try:
#                     path = nx.shortest_path(G, source=node.id, target=sink_id, weight='weight')
#                     for i in range(1, len(path)):
#                         drawline(screen, nodes[path[i-1]], nodes[path[i]])
#                 except:
#                     pass

#             x, y = node.location
#             if node.sent_data:
#                 color = (255, 165, 0)
#             elif node.received_data:
#                 color = (0, 255, 255)
#             else:
#                 color = (0, 255, 0) if node.isRouter else (0, 120, 255)

#             pygame.draw.circle(screen, color, (x, y), NODE_RADIUS)
#             label = font.render(node.label, True, (0, 0, 0))
#             screen.blit(label, (x + 10, y - 10))

#         pygame.display.flip()
#         clock.tick(60)

#     pygame.quit()
import pygame
import cv2
import json
import numpy as np
import math
import random
import networkx as nx

# === Constants ===
WIDTH, HEIGHT = 1200, 941
NODE_RADIUS = 10
SCALE_M_PER_PX = 0.9 / 55
RX_SENSITIVITY = -70  # dBm

# === Utility Functions ===
def fspl_with_walls(distance_m, freq_mhz=2400, n=3.0, d0=1.0,
                    walls_crossed=0, wall_penalty_db=3,
                    fading_std_db=4, include_fading=True):
    if distance_m < d0:
        distance_m = d0
    pl_d0 = 20 * math.log10(d0) + 20 * math.log10(freq_mhz) - 27.55
    path_loss = pl_d0 + 10 * n * math.log10(distance_m / d0)
    wall_loss = walls_crossed * wall_penalty_db
    fading = random.gauss(0, fading_std_db) if include_fading else 0
    return path_loss + wall_loss + fading

def bresenham_line(x0, y0, x1, y1):
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
    return points, math.sqrt(dx**2 + dy**2) * SCALE_M_PER_PX

# === Message Class ===
class MSG:
    def __init__(self, rx, tx, message):
        self.rx = rx
        self.tx = tx
        self.message = message

# === Sensor Node Classes ===
class SensorNode:
    def __init__(self, id, x, y, node_type="sensor", label=""):
        self.id = id
        self.location = (x, y)
        self.type = node_type
        self.label = label
        self.isRouter = (node_type == "router")
        self.received_data = []
        self.sent_data = False
        self.transmitPower = 16  # dBm
        self.links = {}  # neighbor_id -> margin
        self.awake = True
        self.sleep_timer = 0
        self.wake_interval = 300
        self.wake_duration = 60
        self.self_to_router_distance = float("inf")
        self.other_node_to_router = {}
        self.distance_to_others = {}

    def update_cycle(self):
        self.sleep_timer += 1
        if self.awake:
            if self.sleep_timer >= self.wake_duration:
                self.awake = False
                self.sleep_timer = 0
        else:
            if self.sleep_timer >= self.wake_interval:
                self.awake = True
                self.sleep_timer = 0

    def inRange(self, node, wallMask):
        nx_, ny_ = node.location
        sx, sy = self.location
        line_points, distance = bresenham_line(sx, sy, nx_, ny_)
        deBounce, inWall, timesCrossed = 0, False, 0
        cooldown = 10
        for x, y in line_points:
            if 0 <= y < wallMask.shape[0] and 0 <= x < wallMask.shape[1]:
                if wallMask[y, x] == 1:
                    if not inWall and deBounce <= 0:
                        timesCrossed += 1
                        inWall = True
                        deBounce = cooldown
                else:
                    inWall = False
                    if deBounce > 0:
                        deBounce -= 1
        fspl = fspl_with_walls(distance, walls_crossed=timesCrossed)
        return fspl

    def discoveryMode(self, all_nodes, wall_mask, rx_sensitivity=RX_SENSITIVITY):
        self.distance_to_others = {}
        for node in all_nodes:
            if node.id == self.id:
                continue
            pl = self.inRange(node=node, wallMask=wall_mask)
            margin = self.transmitPower - pl
            if margin >= rx_sensitivity:
                self.links[node.id] = margin
                self.distance_to_others[node.id] = pl

    def transmit_path(self, path, nodes):
        for i in range(1, len(path)):
            src = nodes[path[i-1]]
            dst = nodes[path[i]]
            print(f"{src.label} sent message to {dst.label}")
            msg = MSG(rx=dst.id, tx=src.id, message={
                "type": "data",
                "distance_to_router": src.self_to_router_distance,
                "other_routes": src.other_node_to_router.copy()
            })
            dst.receive(msg)
        self.sent_data = True

    def receive(self, msg: MSG):
        if msg.tx not in self.received_data:
            print(f"{self.label} received message from {msg.tx}")
            self.received_data.append(msg.tx)
            if isinstance(msg.message, dict):
                self.other_node_to_router.update(msg.message.get("other_routes", {}))

class Router(SensorNode):
    def __init__(self, id, x, y, node_type="router", label="router"):
        super().__init__(id, x, y, node_type=node_type, label=label)
        self.receivedMessages = []

    def receive(self, msg):
        if msg.tx not in [m.tx for m in self.receivedMessages]:
            print(f"Router {self.label} received message from node {msg.tx}")
            self.receivedMessages.append(msg)

class Network:
    def __init__(self, nodes, wall_mask):
        self.nodes = nodes
        self.wall_mask = wall_mask
        self.graph = nx.Graph()
        self.sink_id = self.find_sink()

    def find_sink(self):
        routers = [n.id for n in self.nodes if n.isRouter]
        return routers[0] if routers else None

    def update(self):
        for node in self.nodes:
            node.update_cycle()
        self.discover_links()
        self.build_graph()
        self.route_all()

    def discover_links(self):
        for node in self.nodes:
            node.links = {}
            if node.awake:
                node.discoveryMode(self.nodes, self.wall_mask)

    def build_graph(self):
        self.graph.clear()
        for node in self.nodes:
            for neighbor_id in node.links:
                fspl = node.distance_to_others.get(neighbor_id, 1000)
                self.graph.add_edge(node.id, neighbor_id, weight=fspl)

    def route_all(self):
        direct_to_router = []
        for node in self.nodes:
            if not node.isRouter and node.awake and not node.sent_data:
                # Find best neighbor via broadcasted info
                best_parent = None
                best_cost = float("inf")
                for neighbor_id, margin in node.links.items():
                    neighbor = self.nodes[neighbor_id]
                    neighbor_cost = neighbor.self_to_router_distance + node.distance_to_others.get(neighbor_id, 1000)
                    if neighbor_cost < best_cost:
                        best_cost = neighbor_cost
                        best_parent = neighbor_id

                # Only route if valid parent was found
                if best_parent is not None:
                    try:
                        path = nx.shortest_path(self.graph, source=node.id, target=best_parent, weight='weight')
                        path.append(self.sink_id) if best_parent == self.sink_id else None
                        node.self_to_router_distance = best_cost
                        for other_node in self.nodes:
                            if other_node.id != node.id:
                                other_node.other_node_to_router[node.id] = node.self_to_router_distance
                        node.transmit_path(path, self.nodes)
                        if best_parent == self.sink_id:
                            direct_to_router.append(node.id)
                    except nx.NetworkXNoPath:
                        print(f"No path from {node.label} to parent or router.")

        # Trigger reformation if too many direct links
        if len(direct_to_router) > 1:
            print("Too many nodes connected directly to the router. Re-forming network...")
            for node in self.nodes:
                node.sent_data = False
                node.received_data.clear()
                node.self_to_router_distance = float("inf")
                node.other_node_to_router.clear()
                node.links.clear()
            self.graph.clear()
# === Visualization ===
def drawline(screen, node1, node2):
    pygame.draw.line(screen, (0, 255, 0), node1.location, node2.location, 2)

def run_simulation():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Node Network Simulation")
    clock = pygame.time.Clock()

    background = pygame.image.load("images/overlay.png")
    wall_img = cv2.imread("images/wallsTrans.png", cv2.IMREAD_UNCHANGED)
    wall_mask = (wall_img[:, :, 3] > 128).astype(np.uint8)

    # Load nodes
    with open("json/sensorNodes.json", "r") as f:
        data = json.load(f)
    nodes = []
    for i, entry in enumerate(data):
        NodeClass = Router if entry.get("type") == "router" else SensorNode
        node = NodeClass(
            id=i,
            x=entry["x"],
            y=entry["y"],
            node_type=entry.get("type", "sensor"),
            label=entry.get("room", "")
        )
        nodes.append(node)

    network = Network(nodes, wall_mask)

    # Pygame loop
    running = True
    while running:
        screen.blit(background, (0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        network.update()

        font = pygame.font.SysFont(None, 20)
        for node in nodes:
            if node.sent_data and not node.isRouter:
                try:
                    path = nx.shortest_path(network.graph, source=node.id, target=network.sink_id, weight='weight')
                    for i in range(1, len(path)):
                        drawline(screen, nodes[path[i-1]], nodes[path[i]])
                except:
                    pass

            x, y = node.location
            if node.sent_data:
                color = (255, 165, 0)
            elif node.received_data:
                color = (0, 255, 255)
            elif not node.awake:
                color = (128, 128, 128)
            else:
                color = (0, 255, 0) if node.isRouter else (0, 120, 255)

            pygame.draw.circle(screen, color, (x, y), NODE_RADIUS)
            label = font.render(node.label, True, (0, 0, 0))
            screen.blit(label, (x + 10, y - 10))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

# Only run when this script is executed directly
if __name__ == "__main__":
    run_simulation()