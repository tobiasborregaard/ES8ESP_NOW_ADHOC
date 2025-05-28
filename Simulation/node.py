import mathix as mx
import random
import time
import math
import json
import os

def genData(tiks):
    """
    Generate simulated environmental data over time.
    - CO2 in ppm
    - TVOC in ppb
    """
    base_co2 = 400 + 10 * math.sin(tiks / 300)  # simulate diurnal trend
    base_tvoc = 150 + 5 * math.sin(tiks / 150)
    temp = 20 + 3 * math.sin(tiks / 500)
    rh = 40 + 10 * math.sin(tiks / 300)
    
    # Random spikes to simulate events
    if random.random() < 0.01:
        base_co2 += random.randint(100, 500)
        base_tvoc += random.randint(50, 200)
    
    return int(base_co2), int(base_tvoc), round(temp, 1), round(rh, 1)

def rssi_to_percent(rssi_dbm):
    """
    Convert RSSI in dBm (usually negative) to 0–100% signal quality.
    Clamp below -100 dBm as 0% and above -50 dBm as 100%.
    """
    if rssi_dbm <= -100:
        return 0
    elif rssi_dbm >= -50:
        return 100
    else:
        return 2 * (rssi_dbm + 100)

def dBm_to_lin(rssi_dbm):
    return 10 ** (rssi_dbm / 10)

def scoringFunction(nr, sn, sr, via_bias=2, max_sn=80):
    sr = abs(sr)
    sn = abs(sn)
    nr = abs(nr)

    # Reject bad neighbors or weak relays
    if sn > sr:
        return sr, "direct", 2, sr, sn, nr
    if nr > sr:
        return sr, "direct", 1, sr, sn, nr
    if sn > max_sn:
        return sr, "direct", 0, sr, sn, nr

    direct_score = sr + via_bias
    via_score = (sn + nr) / 2

    if via_score < direct_score:
        return via_score, "via", direct_score, sr, sn, nr
    else:
        return direct_score, "direct", via_score, sr, sn, nr

DATA_MSG = "DATA"
ACK_MSG = "ACK"
WAKE_INTERVAL = 800         
WAKE_WINDOW = 200            
WAKE_JITTER = 10            
SHUTDOWN_CHANCE = 0.05      

class Node:
    def __init__(self,id,x,y,type,label):
        self.id = id
        self.location = (x,y)
        self.label = label
        self.type = type
        
        self.tiks = 1
        self.data = None
        
        self.transmitPower= 16
        self.bestHop = None
        self.wake_offset = random.randint(-WAKE_JITTER, WAKE_JITTER)
        self.next_wake_tick = self.wake_offset
        self.awake = False
        self.receiving = False
        self.transmitting = False
        self.receivedData = []
        self.candidates = {}
        self.gotData = False
        self.rdyHop = False
        self.receiveTimer = 0
        self.directOffset = 0
        self.timeOffset = 0
        self.aware = False
        
    def selectRoute(self, network):
        nodes = network.nodes
        rssi = network.rssiMatrix
        for node in nodes:
            if node.id == self.id:
                continue
            if node.id == "router":
                continue
            # res = scoringFunction(rssi[node.id]["router"], rssi[self.id][node.id], rssi[self.id]["router"])
            res = scoringFunction(
                rssi[node.id]["router"]["rssi"],
                rssi[self.id][node.id]["rssi"],
                rssi[self.id]["router"]["rssi"]
            )




            self.candidates[node.id]=res
        
        
        if os.path.exists("candidates.json"):
            with open("candidates.json", "r") as f:
                all_candidates = json.load(f)
        else:
            all_candidates = {}

        # Overwrite only this node's entry
        # all_candidates[self.id] = {
        #     k: {"score": v[0], "route": v[1]} for k, v in self.candidates.items()
        # }
        all_candidates[self.id] = {
                k: {
                    "score": v[0],
                    "route": v[1],
                    "via_score": v[2],
                    "sr": v[3],
                    "sn": v[4],
                    "nr": v[5]
                }
                for k, v in self.candidates.items()
            }


        # Save it back
        with open("candidates.json", "w") as f:
            json.dump(all_candidates, f, indent=2) 
        # Find best "direct" route    
            # Find best "via" route
        via_options = {k: v for k, v in self.candidates.items() if v[1] == "via"}

        if via_options:

            best_hop = min(via_options.items(), key=lambda item: item[1][0])  # item = (node_id, (score, "via"))
            self.bestHop = best_hop[0]
            self.timeOffset = random.randint(0,30)
        else:
            self.bestHop = "router"  # direct to router
            self.timeOffset = random.randint(0,30)
            self.directOffset = random.randint(30,60)
                
    def receive(self, msg, sender):
        self.receivedData.append(msg)
        if self.id == "router":
            if not hasattr(self, "liveData"):
                self.liveData = {}
                self.timeSeen = {}
                self.msgCount = {}
                self.deliveryStats = {}  # NEW: Track sent/received for PDR

            # Split on 'ID,' and keep rest
            chunks = msg.split("ID,")[1:]  # skip first junk entry if present
            for chunk in chunks:
                try:
                    label_and_data = chunk.strip().split(",", 1)
                    if len(label_and_data) < 2:
                        continue
                    label = label_and_data[0].strip()
                    data_str = label_and_data[1]
                    parts = data_str.split(",")
                    co2 = int(parts[parts.index("CO2") + 1])
                    tvoc = int(parts[parts.index("TVOC") + 1])
                    temp = float(parts[parts.index("TEMP") + 1])
                    rh = float(parts[parts.index("RH") + 1])
                    # Update environmental data
                    self.liveData[label] = (co2, tvoc, temp, rh)
                    # NEW: Count messages seen
                    self.msgCount[label] = self.msgCount.get(label, 0) + 1
                    # NEW: Update delivery stats (received count)
                    if label not in self.deliveryStats:
                        self.deliveryStats[label] = {"sent": 0, "recv": 0}
                    self.deliveryStats[label]["recv"] += 1
                except Exception as e:
                    print(f"⚠️ Failed to parse: '{chunk}', error: {e}")
        if (self.bestHop == "router"):
            self.receiveTimer = 30
            self.rdyHop = True
        else:
            self.receiveTimer = 10
            self.rdyHop = True
            self.aware = True
            
    def update(self):
        self.tiks += 1
        awareOffset =  0
        if self.aware == True:
            awareOffset = 15

        if not self.awake and self.tiks >= self.next_wake_tick:
            self.awake = True
            
            self.next_sleep_tick = self.tiks + WAKE_WINDOW
            self.next_wake_tick = self.tiks + WAKE_INTERVAL+awareOffset + self.wake_offset

        if self.awake and self.tiks >= self.next_sleep_tick:
            self.awake = False
            return  # asleep again

        # Count down receive delay (hop delay window)
        if self.receiveTimer > 0:
            self.receiveTimer -= 1
       
        # Generate new data occasionally
        if self.tiks % ((60*5) +self.timeOffset +self.directOffset) == 0:
            self.data = genData(self.tiks)
            self.gotData = True

           
    def createMSG(self):
        co2, tvoc, temp, rh = self.data
        return f'ID,{self.label},CO2,{co2},TVOC,{tvoc},TEMP,{temp},RH,{rh},'    
    
    def createHopMSG(self):
        if self.gotData and self.data is not None and self.createMSG() not in self.receivedData:
            self.receivedData.append(self.createMSG())
        msg = "".join(self.receivedData)
        return msg
