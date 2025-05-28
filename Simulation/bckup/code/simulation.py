import pygame
import cv2
import json
from sensorNode import SensorNode, Router
import numpy as np
# Window size
WIDTH, HEIGHT = 1200, 941
NODE_RADIUS = 10

# Init
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Node Network Simulation")
clock = pygame.time.Clock()


# Load floor plan
background = pygame.image.load("images/overlay.png")
wall_img = cv2.imread("images/wallsTrans.png", cv2.IMREAD_UNCHANGED)
if wall_img is None:
    raise FileNotFoundError("Couldn't load wallsTrans.png")
if wall_img.shape[2] != 4:
    raise ValueError("wallsTrans.png must have an alpha channel")
wall_mask = (wall_img[:, :, 3] > 128).astype(np.uint8)


def drawline(node1,node2):
    pygame.draw.line(screen,(0,255,0),node1.location,node2.location,2)
# Load nodes
nodes = []
router = None

with open("json/sensorNodes.json", "r") as f:
    data = json.load(f)

for i, entry in enumerate(data):
    NodeClass = Router if entry.get("type") == "router" else SensorNode
    node = NodeClass(
        id=i,
        x=entry["x"],
        y=entry["y"],
        node_type=entry.get("type", "sensor"),
        label=entry.get("room", "")
    )
    if node.type == "router":
        router = node
    else:
        nodes.append(node)


# Pygame loop
running = True
# Perform once before the loop
for node in nodes:
    node.discoveryMode(nodes, wall_mask)

router.RSSI2Nodes(nodes)


while running:
    screen.blit(background, (0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    font = pygame.font.SysFont(None, 20)
    for i, node in nodes:
        x, y = node.location
        
        node.discoveryMode(nodes,wall_mask)
        
        if not node.sent_data:
            best_id = node.selectBestHop()
        if best_id is not None:
            node.transmit(to=nodes[best_id], message="data")
        
        best_id = node.selectBestHop()
        if best_id is not None:
            drawline(node, nodes[best_id])     # thick green = best link
        
            
        color = (0, 255, 0) if node.isRouter else (0, 120, 255)
        pygame.draw.circle(screen, color, (x, y), NODE_RADIUS)
        label = font.render(node.label, True, (0, 0, 0))
        screen.blit(label, (x + 10, y - 10))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
