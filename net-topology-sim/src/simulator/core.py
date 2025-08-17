from __future__ import annotations
import threading, queue, time, random, json
from typing import Dict, Any, Tuple
import networkx as nx
from .messages import Message

class Node(threading.Thread):
    def __init__(self, name: str, inbox: "queue.Queue[Message]", links: Dict[str, "queue.Queue[Message]"], pause_evt: threading.Event, log_path: str):
        super().__init__(daemon=True)
        self.name = name
        self.inbox = inbox
        self.links = links
        self.pause_evt = pause_evt
        self.running = True
        self.log_path = log_path

    def log(self, msg: str):
        line = f"[{time.strftime('%H:%M:%S')}] {self.name}: {msg}"
        print(line)
        with open(self.log_path, "a") as f:
            f.write(line + "\n")

    def send(self, neighbor: str, message: Message):
        if neighbor in self.links:
            try:
                self.links[neighbor].put_nowait(message)
            except queue.Full:
                self.log(f"LINK QUEUE FULL to {neighbor}, dropping {message.kind}")

    def broadcast_neighbors(self, message: Message):
        for n in list(self.links.keys()):
            self.send(n, message)

    def run(self):
        self.log("Node started")
        hello_timer = time.time()
        while self.running:
            # Pause support
            while self.pause_evt.is_set():
                time.sleep(0.05)

            # Periodic HELLO (discovery)
            if time.time() - hello_timer >= 1.0:
                self.broadcast_neighbors(Message(kind="HELLO", src=self.name, dst="*", payload="hi"))
                hello_timer = time.time()

            # Process inbox
            try:
                msg: Message = self.inbox.get(timeout=0.1)
                if msg.kind == "HELLO":
                    self.log(f"HELLO from {msg.src}")
                elif msg.kind == "PAUSE":
                    self.log("Received PAUSE")
                elif msg.kind == "RESUME":
                    self.log("Received RESUME")
                elif msg.kind == "ARP":
                    self.log(f"ARP from {msg.src}: who-has {msg.payload}")
                else:
                    self.log(f"Got {msg.kind} from {msg.src}")
            except queue.Empty:
                pass

        self.log("Node stopped")

class Simulation:
    def __init__(self, G: nx.Graph, logs_dir: str):
        self.G = G.copy()
        self.logs_dir = logs_dir
        self.pause_evt = threading.Event()
        self.queues: Dict[str, queue.Queue] = {}
        self.nodes: Dict[str, Node] = {}
        self.links: Dict[tuple, bool] = {}  # link up/down

        # Create per-node inbox and Node thread
        for n in self.G.nodes():
            inbox = queue.Queue(maxsize=1000)
            self.queues[n] = inbox
            self.nodes[n] = Node(
                name=n,
                inbox=inbox,
                links={},  # filled later
                pause_evt=self.pause_evt,
                log_path=f"{self.logs_dir}/{n}.log"
            )

        # Create link FIFOs (two directed queues for each undirected edge)
        for u,v in self.G.edges():
            self.links[tuple(sorted((u,v)))] = True  # up
            # link uses receiver's inbox
            self.nodes[u].links[v] = self.queues[v]
            self.nodes[v].links[u] = self.queues[u]

    def start(self):
        for n in self.nodes.values():
            n.start()

    def stop(self):
        for n in self.nodes.values():
            n.running = False
        for n in self.nodes.values():
            n.join(timeout=1.0)

    def pause(self):
        self.pause_evt.set()
        # also send PAUSE messages (optional)
        for n in self.nodes.values():
            n.send("*", Message(kind="PAUSE", src="SIM", dst="*"))

    def resume(self):
        self.pause_evt.clear()
        for n in self.nodes.values():
            n.send("*", Message(kind="RESUME", src="SIM", dst="*"))

    def fail_link(self, a: str, b: str, down: bool = True):
        key = tuple(sorted((a,b)))
        if key not in self.links:
            return False
        # Simulate by disconnecting send maps
        if down:
            if b in self.nodes[a].links: del self.nodes[a].links[b]
            if a in self.nodes[b].links: del self.nodes[b].links[a]
        else:
            # restore
            self.nodes[a].links[b] = self.queues[b]
            self.nodes[b].links[a] = self.queues[a]
        self.links[key] = not down
        return True
