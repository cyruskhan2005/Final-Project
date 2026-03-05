import json
import time
import threading
from google.cloud import pubsub_v1

PROJECT_ID = "cs131finalproject"
SUBSCRIPTION_ID = "fog-sub"

YELLOW_SECONDS = 2
RED_HOLD_SECONDS = 7  # time to keep red after last event

LIGHT_STATE = "GREEN"
last_event_time = 0


def set_state(s):
    global LIGHT_STATE
    if LIGHT_STATE != s:
        LIGHT_STATE = s
        print(f"LIGHT STATE: {LIGHT_STATE}")


def evaluate_light():
    """
    Traffic logic:

    - If recent event within RED_HOLD_SECONDS -> RED
    - If no event for RED_HOLD_SECONDS -> GREEN
    """
    global last_event_time

    now = time.time()
    if last_event_time and (now - last_event_time < RED_HOLD_SECONDS):
        set_state("RED")
    else:
        set_state("GREEN")


def light_monitor():
    """
    Periodically re-evaluates traffic state.
    """
    while True:
        time.sleep(1)
        evaluate_light()


def main():
    subscriber = pubsub_v1.SubscriberClient()
    sub_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

    print("Subscribed to:", sub_path)
    print("LIGHT STATE: GREEN")
    set_state("GREEN")

    threading.Thread(target=light_monitor, daemon=True).start()

    def callback(message):
        global last_event_time
        try:
            data = json.loads(message.data.decode("utf-8"))
            message.ack()

            if data.get("event_type") == "jaywalking_detected":
                last_event_time = time.time()

                # optional yellow transition
                if LIGHT_STATE == "GREEN":
                    set_state("YELLOW")
                    time.sleep(YELLOW_SECONDS)

        except Exception as e:
            print("Error processing message:", e)
            message.ack()

    subscriber.subscribe(sub_path, callback=callback).result()


if __name__ == "__main__":
    main()