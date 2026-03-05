import json
import time
from google.cloud import pubsub_v1

PROJECT_ID = "cs131finalproject"
SUBSCRIPTION_ID = "fog-sub"
YELLOW_SECONDS = 3
RED_SECONDS = 10
state = "GREEN"

def set_state(s):
    global state
    state = s
    print(f"CAR STATE: {state}")

def main():
    subscriber = pubsub_v1.SubscriberClient()
    sub_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

    print("Subscribed to:", sub_path)
    set_state("GREEN")

    def callback(message):
        data = json.loads(message.data.decode("utf-8"))
        print("Received:", data)

        if data.get("event_type") == "jaywalking_detected":
            set_state("YELLOW")
            time.sleep(YELLOW_SECONDS)
            set_state("RED")
            time.sleep(RED_SECONDS)
            set_state("GREEN")

        message.ack()

    subscriber.subscribe(sub_path, callback=callback).result()

if __name__ == "__main__":
    main()