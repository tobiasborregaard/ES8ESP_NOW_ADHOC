import pygame
import cv2
import json
import numpy as np
from network import NetworkGLB
from node import Node

# Window size
WIDTH, HEIGHT = 3400, 1080
NODE_RADIUS = 10

# Init
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Node Network Simulation")
clock = pygame.time.Clock()


# Load floor plan
background = pygame.image.load("images/overlay.png")
wall_img = cv2.imread("images/wallTrans.png", cv2.IMREAD_UNCHANGED)
if wall_img is None:
    raise FileNotFoundError("Couldn't load wallsTrans.png")
if wall_img.shape[2] != 4:
    raise ValueError("wallsTrans.png must have an alpha channel")
wall_mask = (wall_img[:, :, 3] > 128).astype(np.uint8)

def drawLiveStats(router_node, base_x=2120, base_y=20, line_height=34, width=1200):
    if not hasattr(router_node, "liveData"):
        return

    if not hasattr(router_node, "roomIndexMap"):
        router_node.roomIndexMap = {}
        router_node._nextIndex = 0

    # Assign consistent index to each new label
    for label in router_node.liveData.keys():
        if label not in router_node.roomIndexMap:
            router_node.roomIndexMap[label] = router_node._nextIndex
            router_node._nextIndex += 1

    for room, (co2, tvoc, temp, rh) in router_node.liveData.items():
        idx = router_node.roomIndexMap.get(room, 0)
        y = base_y + idx * line_height * 2  # Double height per node

        # Environmental data
        pygame.draw.rect(screen, (0, 0, 0), pygame.Rect(base_x, y, width, line_height))
        text = f"{room:12} | CO2: {co2:4} ppm | TVOC: {tvoc:4} ppb | Temp: {temp:4.1f} °C | RH: {rh:4.1f} %"
        txt_surface = font.render(text, True, (255, 255, 255))
        screen.blit(txt_surface, (base_x, y))

        # PDR stats
        if hasattr(router_node, "deliveryStats") and room in router_node.deliveryStats:
            stats = router_node.deliveryStats[room]
            sent = stats.get("sent", 0)
            recv = stats.get("recv", 0)
            pdr = (recv / sent) * 100 if sent > 0 else 0.0

            y += line_height
            pygame.draw.rect(screen, (0, 0, 0), pygame.Rect(base_x, y, width, line_height))
            pdr_text = f"{room:12} | Revceived ({recv})"
            pdr_surface = font.render(pdr_text, True, (200, 200, 0))
            screen.blit(pdr_surface, (base_x, y))


# def drawline(node1:Node, node2:Node):
#     color = (255, 0, 0) if node1.transmitting else (0, 255, 0)
#     pygame.draw.line(screen, color, node1.location, node2.location, 2)
hovered_link = None  # Global-ish var for storing what the mouse is over

def drawline(node1: Node, node2: Node):
    global hovered_link
    color = (255, 0, 0) if node1.transmitting else (0, 255, 0)
    pygame.draw.line(screen, color, node1.location, node2.location, 2)

    # Hover detection (distance to line)
    mouse_pos = pygame.mouse.get_pos()
    px, py = mouse_pos
    x1, y1 = node1.location
    x2, y2 = node2.location

    # Use point-to-line distance formula
    line_vec = np.array([x2 - x1, y2 - y1])
    pnt_vec = np.array([px - x1, py - y1])
    line_len = np.linalg.norm(line_vec)
    line_unitvec = line_vec / line_len if line_len != 0 else line_vec
    proj_len = np.dot(pnt_vec, line_unitvec)
    proj = line_unitvec * proj_len
    closest = np.array([x1, y1]) + proj
    dist = np.linalg.norm(closest - np.array(mouse_pos))

    if 0 <= proj_len <= line_len and dist < 10:  # 10 px hover range
        hovered_link = (node1.id, node2.id)

def drawNode(node:Node):
    x,y = node.location
    color = (0, 255, 0) if node.type== "router" else (0, 120, 255)
    if node.transmitting:
        color = (255, 0, 0)
    if node.receiving:
        color = (0, 0, 255)
    if node.gotData:
        color = (149,255,193)
    pygame.draw.circle(screen, color, (node.location), NODE_RADIUS)
    label = font.render(node.label, True, (0, 0, 0))
    screen.blit(label, (x + 10, y - 10))
    
# Load nodes
with open("json/sensorNodes.json", "r") as f:
    data = json.load(f)

# nodes:list[Node] = []
# for i, entry in enumerate(data):
#     node = Node(id = entry["id"], x=entry["x"], y= entry["y"], type=entry.get("type"),label=entry.get("room",""))
#     nodes.append(node)
nodes = {}
for entry in data:
    node = Node(id=entry["id"], x=entry["x"], y=entry["y"], type=entry.get("type"), label=entry.get("room", ""))
    nodes[node.id] = node


ntwk:NetworkGLB = NetworkGLB(nodes=list(nodes.values()),wallMask=wall_mask)
ntwk.computeAllRssi()

# Initial routing decision (once at startup)
for node in ntwk.nodes:
    if node.id == "router":
        continue
    node.selectRoute(network=ntwk)
running = True
while running:
    hovered_link = None  # Reset hovered link each frame
    font = pygame.font.SysFont(None, 20)
    screen.blit(background, (0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    ntwk.update()

    for node in ntwk.nodes:
        if node.type != "router":
            node.update()

            if node.gotData and node.bestHop:
                if node.bestHop == "router":
                    if node.receiveTimer == 0 and node.rdyHop:
                        msg = node.createHopMSG()
                        ntwk.send(node, nodes["router"], msg)
                    if node.transmitting and hasattr(nodes["router"], "deliveryStats"):
                        stats = nodes["router"].deliveryStats.setdefault(node.label, {"sent": 0, "recv": 0})
                        stats["sent"] += 1
                elif node.bestHop in nodes:
                    if node.receiveTimer == 0:
                        msg = node.createHopMSG() if node.rdyHop else node.createMSG()
                        ntwk.send(node, nodes[node.bestHop], msg)
                    if node.transmitting and hasattr(nodes["router"], "deliveryStats"):
                        stats = nodes["router"].deliveryStats.setdefault(node.label, {"sent": 0, "recv": 0})
                        stats["sent"] += 1

    # 🔁 Draw links and capture hovered link
    for node in ntwk.nodes:
        if node.bestHop in nodes:
            drawline(node1=node, node2=nodes[node.bestHop])

    # ✅ Show hover info after all links drawn
    if hovered_link:
        a, b = hovered_link
        link = ntwk.rssiMatrix.get(a, {}).get(b)
        if link:
            info = f"Link: {a} ↔ {b} | RSSI: {link['rssi']:.1f} dBm | Walls: {link['walls']} | Dist: {link['distance']:.2f} m"
            hover_surface = font.render(info, True, (255, 255, 0))
            screen.blit(hover_surface, (20, HEIGHT - 40))

    for node in ntwk.nodes:    
        drawNode(node)

    font = pygame.font.SysFont(None, 40)
    drawLiveStats(nodes["router"])
    pygame.display.flip()
    clock.tick(60)

# while running:
#     hovered_link = None  # Reset hovered link each frame
#     font = pygame.font.SysFont(None, 20)
#     screen.blit(background, (0, 0))

#     for event in pygame.event.get():
#         if event.type == pygame.QUIT:
#             running = False

#     ntwk.update()

#     for node in ntwk.nodes:
#         if node.type != "router":
#             node.update()

#             if node.gotData and node.bestHop:
#                 # Final hop to router
#                 if node.bestHop == "router":
#                     if node.receiveTimer == 0 and node.rdyHop:
#                         msg = node.createHopMSG()
#                         ntwk.send(node, nodes["router"], msg)
#                     if node.transmitting and hasattr(nodes["router"], "deliveryStats"):
#                         stats = nodes["router"].deliveryStats.setdefault(node.label, {"sent": 0, "recv": 0})
#                         stats["sent"] += 1
#                 # Intermediate hop
#                 elif node.bestHop in nodes:
#                     if node.receiveTimer == 0:
#                         msg = node.createHopMSG() if node.rdyHop else node.createMSG()
#                         ntwk.send(node, nodes[node.bestHop], msg)
#                     if node.transmitting and hasattr(nodes["router"], "deliveryStats"):
#                         stats = nodes["router"].deliveryStats.setdefault(node.label, {"sent": 0, "recv": 0})
#                         stats["sent"] += 1

#                 # Draw link if possible
#             if node.bestHop in nodes:
#                 drawline(node1=node, node2=nodes[node.bestHop])
#             # Show link stats in status area
#             if hovered_link:
#                 a, b = hovered_link
#                 link = ntwk.rssiMatrix.get(a, {}).get(b)
#                 if link:
#                     info = f"Link: {a} ↔ {b} | RSSI: {link['rssi']:.1f} dBm | Walls: {link['walls']} | Dist: {link['distance']:.2f} m"
#                     hover_surface = font.render(info, True, (255, 255, 0))
#                     screen.blit(hover_surface, (20, HEIGHT - 40))

#     for node in ntwk.nodes:    
#         drawNode(node)

#     font = pygame.font.SysFont(None, 40)
#     drawLiveStats(nodes["router"])
#     pygame.display.flip()
#     clock.tick(60)

pygame.quit()