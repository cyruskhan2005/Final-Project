import json
import time
from google.cloud import pubsub_v1

PROJECT_ID = "cs131finalproject"
SUBSCRIPTION_ID = "fog-sub"

YELLOW_SECONDS = 3
CLEAR_THRESHOLD = 2   # require 2 consecutive clear events

state = "GREEN"
clear_count = 0

def set_state(s):
    global state
    state = s
    print(f"CAR STATE: {state}")

def main():
    global clear_count

    subscriber = pubsub_v1.SubscriberClient()
    sub_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

    print("Subscribed to:", sub_path)
    set_state("GREEN")

    def callback(message):
        global clear_count, state

        data = json.loads(message.data.decode("utf-8"))
        print("Received:", data)

        event_type = data.get("event_type")

        if event_type == "jaywalker_present":
            clear_count = 0

            if state == "GREEN":
                set_state("YELLOW")
                time.sleep(YELLOW_SECONDS)
                set_state("RED")

            elif state == "RED":
                print("Jaywalker still present, staying RED")

            elif state == "YELLOW":
                print("Already transitioning to RED")

        elif event_type == "jaywalker_clear":
            if state == "RED":
                clear_count += 1
                print(f"Clear count: {clear_count}")

                if clear_count >= CLEAR_THRESHOLD:
                    set_state("GREEN")
                    clear_count = 0

            elif state == "GREEN":
                print("Already GREEN")

        else:
            print("Unknown event type:", event_type)

        message.ack()

    subscriber.subscribe(sub_path, callback=callback).result()

if __name__ == "__main__":
    main()