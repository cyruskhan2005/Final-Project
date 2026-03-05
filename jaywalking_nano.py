import jetson.inference
import jetson.utils
import time
import math
import uuid
from collections import OrderedDict
from google.cloud import pubsub_v1
import json

PROJECT_ID = "cs131finalproject"
TOPIC_ID = "jaywalking-events"
CAMERA_ID = "cam_1"

# ===== PUBSUB SETUP =====
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

def publish_event(object_id, confidence):
    event = {
        "camera_id": CAMERA_ID,
        "event_type": "jaywalking_detected",
        "object_id": object_id,
        "confidence": confidence,
        "timestamp": time.time()
    }

    future = publisher.publish(
        topic_path,
        json.dumps(event).encode("utf-8")
    )

    print("Published message_id:", future.result())

# -----------------------------
# Simple Centroid Tracker
# -----------------------------
class CentroidTracker:
    def __init__(self, max_disappeared=20):
        self.next_object_id = 0
        self.objects = OrderedDict()
        self.disappeared = OrderedDict()
        self.max_disappeared = max_disappeared

    def register(self, centroid):
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1

    def deregister(self, object_id):
        del self.objects[object_id]
        del self.disappeared[object_id]

    def update(self, input_centroids):
        if len(input_centroids) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        if len(self.objects) == 0:
            for centroid in input_centroids:
                self.register(centroid)
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            distances = []
            for oc in object_centroids:
                row = [math.sqrt((oc[0] - ic[0])**2 + (oc[1] - ic[1])**2) for ic in input_centroids]
                distances.append(row)

            for i in range(len(object_ids)):
                min_index = distances[i].index(min(distances[i]))
                self.objects[object_ids[i]] = input_centroids[min_index]
                self.disappeared[object_ids[i]] = 0

        return self.objects


# -----------------------------
# Load YOLO model
# -----------------------------
net = jetson.inference.detectNet(
    "ssd-mobilenet-v2",  # you can switch to yolov4-tiny if installed
    threshold=0.5
)

camera = jetson.utils.videoSource("/dev/video0")
display = jetson.utils.videoOutput("display://0")

tracker = CentroidTracker()

COOLDOWN_SECONDS = 5

last_alert_time = {}

# -----------------------------
# Define Jaywalking Zone
# (Adjust these coordinates!)
# -----------------------------
ZONE_LEFT = 340
ZONE_RIGHT = 940
ZONE_TOP = 0
ZONE_BOTTOM = 720

print("Jaywalking detection started...")

while display.IsStreaming():

    img = camera.Capture()
    detections = net.Detect(img)

    centroids = []

    for detection in detections:

        class_name = net.GetClassDesc(detection.ClassID)

        if class_name != "person":
            continue

        x1 = int(detection.Left)
        y1 = int(detection.Top)
        x2 = int(detection.Right)
        y2 = int(detection.Bottom)

        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)

        centroids.append((cx, cy))

        # Draw bounding box
        jetson.utils.cudaDrawRect(
            img,
            (x1, y1, x2, y2),
            (0, 255, 0, 100)
        )

    objects = tracker.update(centroids)

    # Check jaywalking condition
    for object_id, centroid in objects.items():
        cx, cy = centroid

        # Draw centroid
        jetson.utils.cudaDrawCircle(
            img,
            (cx, cy),
            5,
            (255, 0, 0, 100)
        )

        current_time = time.time()

        if (ZONE_LEFT < cx < ZONE_RIGHT) and (ZONE_TOP < cy < ZONE_BOTTOM):

            # If object never triggered before
            if object_id not in last_alert_time:
                last_alert_time[object_id] = current_time
                print("[ALERT] Jaywalking detected! ID=%d" % object_id)
                publish_event(object_id, detection.Confidence)

            else:
                # Check cooldown
                time_since_last = current_time - last_alert_time[object_id]

                if time_since_last > COOLDOWN_SECONDS:
                    last_alert_time[object_id] = current_time
                    print("[ALERT] Jaywalking detected! ID=%d" % object_id)
                    publish_event(object_id, detection.Confidence)

    # Draw zone rectangle
    jetson.utils.cudaDrawRect(
        img,
        (ZONE_LEFT, ZONE_TOP, ZONE_RIGHT, ZONE_BOTTOM),
        (255, 0, 0, 100)
    )

    display.Render(img)
    display.SetStatus("Jaywalking Detection")

print("Shutting down...")
