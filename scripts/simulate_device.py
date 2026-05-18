import json
import time
import threading
import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"
DEVICE_ID = "87b1d353-5804-47c7-99cc-7723506c364b"

DATA_TOPIC = f"devices/{DEVICE_ID}/data"
COMMAND_TOPIC = f"devices/{DEVICE_ID}/command"

API_KEY = "nxs_rMk5Ttt0v22afieuciwtJcOyGraJcnUHaXjtvOKZ4Tg"

# False = free, True = occupied
slots = {f"A{i}": False for i in range(1, 21)}

# False = unlocked, True = locked
locks = {f"A{i}": True for i in range(1, 21)}

client = mqtt.Client()


def publish(slot_id):
    msg = {
        "api_key": API_KEY,
        "readings": [
            {
                "floor": "F1",
                "slot_number": slot_id,
                "is_occupied": slots[slot_id],
                "type": "car",
                "locked": locks[slot_id],
            }
        ],
    }

    client.publish(DATA_TOPIC, json.dumps(msg))
    print("SENT DATA:", msg)


def toggle(slot_id):
    old = slots[slot_id]
    slots[slot_id] = not old

    # gửi khi trạng thái xe thay đổi
    publish(slot_id)


def apply_lock_command(slot_id, locked):
    if slot_id not in locks:
        print("UNKNOWN SLOT:", slot_id)
        return

    old = locks[slot_id]
    locks[slot_id] = locked

    print(f"LOCK CHANGED: {slot_id} {old} -> {locked}")

    publish(slot_id)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT CONNECTED")
        client.subscribe(COMMAND_TOPIC)
        print("SUBSCRIBED:", COMMAND_TOPIC)
    else:
        print("MQTT CONNECT FAILED:", rc)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        print("RECEIVED COMMAND:", msg.topic, payload)

        slot_id = payload.get("slot_number")
        locked = payload.get("locked")

        if slot_id is None or locked is None:
            print("INVALID COMMAND PAYLOAD")
            return

        apply_lock_command(slot_id, bool(locked))

    except Exception as e:
        print("COMMAND ERROR:", e)


def print_ui():
    print("\nPARKING STATUS")
    print("-" * 50)
    for i in range(1, 21):
        s = f"A{i}"
        status = "OCC" if slots[s] else "FREE"
        lock_status = "LOCKED" if locks[s] else "UNLOCKED"
        print(f"{s}: {status:<4} | {lock_status}")
    print("-" * 50)


def loop():
    while True:
        print_ui()
        cmd = input("Toggle slot (A1-A20) or q: ").strip().upper()

        if cmd == "Q":
            break

        if cmd in slots:
            toggle(cmd)


if __name__ == "__main__":
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, 1883, 60)

    # chạy MQTT background để vừa nhận command vừa nhập input
    client.loop_start()

    try:
        loop()
    finally:
        client.loop_stop()
        client.disconnect()