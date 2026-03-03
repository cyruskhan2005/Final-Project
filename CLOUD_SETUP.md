# Google Cloud Setup

## Project Information
- Project ID: cs131finalproject
- Region: us-west2
---

## Enabled APIs
- Cloud Pub/Sub API
- Cloud Firestore API
- Cloud Functions API

---

## Pub/Sub Configuration
- Topic Name: jaywalking-events
- Subscription Name: fog-sub
- Delivery Type: Pull

---

## Firestore Configuration
- Mode: Native
- Collection: jaywalking_events

---

## Service Accounts

### Edge Publisher
- Role: Pub/Sub Publisher

### Fog Subscriber
- Role: Pub/Sub Subscriber
- Role: Cloud Datastore User

---

## Deployment Flow

1. Jetson Nano captures video from USB camera.
2. Person detection runs locally on the edge device.
3. When jaywalking condition is met, a JSON message is published to Pub/Sub.
4. Fog subscriber receives the event.
5. Fog transitions traffic light state (GREEN → YELLOW → RED).
6. Event is written to Firestore for storage and analysis.
