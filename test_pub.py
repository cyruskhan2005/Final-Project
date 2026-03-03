from google.cloud import pubsub_v1
import json
import time

project_id = "cs131finalproject"
topic_id = "jaywalking-events"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)

event = {
	"camera_id": "cam_1",
	"event_type": "jaywalking_detected",
	"confidence": 0.91,
	"timestamp": time.time()
}

future = publisher.publish(
	topic_path,
	json.dumps(event).encode("utf-8")
)

print("Publishing message...")
message_id = future.result()
print(f"Message published with ID: {message_id}")


