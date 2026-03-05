import jetson.inference
import jetson.utils
import time
import math
from collections import OrderedDict
from google.cloud import pubsub_v1
import json

PROJECT_ID = "cs131finalproject"
TOPIC_ID = "jaywalking-events"
CAMERA_ID = "cam_1"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

PUBLISH_INTERVAL = 5
last_publish_time = 0

def publish_event(event_type, object_id=None, confidence=None):
    event = {
        "camera_id": CAMERA_ID,
        "event_type": event_type,
        "timestamp": time.time()
    }

    if object_id is not None:
        event["object_id"] = object_id

    if confidence is not None:
        event["confidence"] = confidence

    future = publisher.publish(
        topic_path,
        json.dumps(event).encode("utf-8")
    )

    print("Published:", event, "message_id:", future.result())


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


net = jetson.inference.detectNet(
    "ssd-mobilenet-v2",
    threshold=0.5
)

camera = jetson.utils.videoSource("/dev/video0")
display = jetson.utils.videoOutput("display://0")

tracker = CentroidTracker()

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

        centroids.append((cx, cy, round(detection.Confidence, 2)))

        jetson.utils.cudaDrawRect(
            img,
            (x1, y1, x2, y2),
            (0, 255, 0, 100)
        )

    tracker_input = [(c[0], c[1]) for c in centroids]
    objects = tracker.update(tracker_input)

    jaywalker_present = False
    best_object_id = None
    best_confidence = 0.0

    for object_id, centroid in objects.items():
        cx, cy = centroid

        jetson.utils.cudaDrawCircle(
            img,
            (cx, cy),
            5,
            (255, 0, 0, 100)
        )

        if (ZONE_LEFT < cx < ZONE_RIGHT) and (ZONE_TOP < cy < ZONE_BOTTOM):
            jaywalker_present = True
            best_object_id = object_id

    if jaywalker_present:
        for c in centroids:
            cx, cy, conf = c
            if (ZONE_LEFT < cx < ZONE_RIGHT) and (ZONE_TOP < cy < ZONE_BOTTOM):
                if conf > best_confidence:
                    best_confidence = conf

    current_time = time.time()

    if current_time - last_publish_time >= PUBLISH_INTERVAL:
        if jaywalker_present:
            print("[STATE] jaywalker_present")
            publish_event(
                event_type="jaywalker_present",
                object_id=best_object_id,
                confidence=best_confidence
            )
        else:
            print("[STATE] jaywalker_clear")
            publish_event(event_type="jaywalker_clear")

        last_publish_time = current_time

    jetson.utils.cudaDrawRect(
        img,
        (ZONE_LEFT, ZONE_TOP, ZONE_RIGHT, ZONE_BOTTOM),
        (255, 0, 0, 100)
    )

    display.Render(img)
    display.SetStatus("Jaywalking Detection")

print("Shutting down...")

