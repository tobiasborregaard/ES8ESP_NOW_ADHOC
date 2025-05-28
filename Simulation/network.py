import mathix as mx
import json,os



class NetworkGLB:
    def __init__(self, nodes, wallMask):
        self.nodes = nodes
        self.wallMask = wallMask
        self.rssiMatrix = {}
        self.computeAllRssi()
        self.pending_transmissions = []  # list of (start_time, duration, sender, receiver, message)
        self.current_tick = 0
        self.channel_busy = False
        
    def computeAllRssi(self):
        """
        Computes symmetric RSSI (FSPL) values between all node pairs, accounting for wall crossings.
        Stores results in self.rssiMatrix[node_id][other_id].
        """
        if os.path.exists("matrix3.json"):
            with open("matrix3.json", "r") as f:
                self.rssiMatrix = json.load(f)
                # Ensure nested dicts (just for safety, in case JSON was malformed)
                self.rssiMatrix = {
                    str(k): {
                        str(kk): {
                            "rssi": float(vv["rssi"]),
                            "walls": int(vv["walls"]),
                            "distance": float(vv["distance"])
                        } for kk, vv in v.items()
                    } for k, v in self.rssiMatrix.items()
                }
            return

        for node in self.nodes:
            sx, sy = node.location
            self.rssiMatrix.setdefault(node.id, {})
            # print(node.id , node.label)
            for n in self.nodes:
                if n.id == node.id:
                    continue

                self.rssiMatrix.setdefault(n.id, {})

                # Skip if this pair has already been computed
                if node.id in self.rssiMatrix[n.id]:
                    continue

                nx, ny = n.location
                linePoints, distance = mx.bresenham_line(sx, sy, nx, ny)

                # Count wall crossings
                crossed = 0
                inWall = False
                for x, y in linePoints:
                    if 0 <= y < self.wallMask.shape[0] and 0 <= x < self.wallMask.shape[1]:
                        if self.wallMask[y, x] == 1 and not inWall:
                            crossed += 1
                            inWall = True
                        elif self.wallMask[y, x] == 0:
                            inWall = False
                # dbm = {}
                fspl = mx.rssi_with_walls(distance_m=distance, walls_crossed=crossed) 
                # for i in range(node.transmitPower, -1, -1): 
                #     dbm[i] = i - fspl
                dbm = node.transmitPower-fspl
                # Store symmetric
                data = {
                    "rssi": dbm,
                    "walls": crossed,
                    "distance": distance
                }
                self.rssiMatrix[node.id][n.id] = data
                self.rssiMatrix[n.id][node.id] = data
        with open("matrix3.json" , "w") as f:
            json.dump(self.rssiMatrix, f, indent=2)
            
   
    def send(self, sender, receiver, message, duration=10):
        
        if receiver.transmitting or receiver.receiving:
            return  
        sender.transmitting = True
        receiver.receiving = True
        sender.gotData = False
        sender.data = None
        sender.receivedData = []
        self.pending_transmissions.append((self.current_tick, duration, sender, receiver, message))


    def broadcast(self, sender, msg):
        """Simulate broadcast to all reachable nodes."""
        for node in self.nodes:
            if node.id == sender.id:
                continue
            rssi = self.rssiMatrix.get(sender.id, {}).get(node.id, None)
            if rssi is not None and rssi > -85:
                node.receive(msg) 
        
    # def update(self):
    #     self.current_tick += 1

    #     new_pending = []
    #     for start, duration, sender, receiver, message in self.pending_transmissions:
    #         if self.current_tick - start >= duration:
    #             receiver.receive(message, sender)
    #             sender.transmitting = False
    #             receiver.receiving = False
    #         else:
    #             new_pending.append((start, duration, sender, receiver, message))

    #     self.pending_transmissions = new_pending
                

    def update(self):
        self.current_tick += 1

        # Mark channel as busy if any node is transmitting or receiving
        self.channel_busy = any(n.transmitting or n.receiving for n in self.nodes)

        arrival_map = {}  # receiver_id -> list of arrivals
        new_pending = []

        for start, duration, sender, receiver, message in self.pending_transmissions:
            if self.current_tick - start >= duration:
                # Queue for processing
                key = receiver.id
                arrival_map.setdefault(key, []).append((sender, message))
            else:
                new_pending.append((start, duration, sender, receiver, message))

        # Handle all message arrivals at this tick
        for receiver_id, arrivals in arrival_map.items():
            receiver = next(n for n in self.nodes if n.id == receiver_id)

            if len(arrivals) == 1:
                # Deliver message normally
                sender, message = arrivals[0]
                receiver.receive(message, sender)
                sender.transmitting = False
                receiver.receiving = False
            else:
                sender_labels = [s.label for s, _ in arrivals]

                # Reset transmitting flags — nothing delivered
                for sender, _ in arrivals:
                    sender.transmitting = False
                receiver.receiving = False

        # Update pending list
        self.pending_transmissions = new_pending
                                
                            
                            
           
                
        
    
    
