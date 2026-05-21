import json
import time
import threading
import ssl
import paho.mqtt.client as mqtt

# ── Cấu hình MQTT (giống ESP32) ──────────────────────────────────────────────
BROKER   = "9728affa3bc64fcc98b13435c136926c.s1.eu.hivemq.cloud"
PORT     = 8883                          # TLS, giống ESP32
MQTT_NAME = "baicaugiay"
MQTT_PASS = "Maiducvan112@##"

DEVICE_ID     = "535eb5cf-00b3-466f-82a3-097ab90709bc"
DATA_TOPIC    = f"devices/{DEVICE_ID}/data"
COMMAND_TOPIC = f"devices/{DEVICE_ID}/command"
API_KEY       = "nxs_5kEEfxW-CDItKDcJHwF_xxLPbhJSMk88DCdYeN1llOo"
# ── Trạng thái bãi đỗ — chỉ theo dõi xe, khoá luôn True ─────────────────────
slots = {f"A{i}": False for i in range(1, 41)}  # False = trống, True = có xe
 
# ── MQTT client ───────────────────────────────────────────────────────────────
client = mqtt.Client(client_id=DEVICE_ID)
client.username_pw_set(MQTT_NAME, MQTT_PASS)
client.tls_set(cert_reqs=ssl.CERT_NONE)
client.tls_insecure_set(True)
 
 
# ── Publish dữ liệu một slot ──────────────────────────────────────────────────
def publish(slot_id):
    msg = {
        "api_key": API_KEY,
        "readings": [
            {
                "floor":       "F1",
                "slot_number": slot_id,
                "is_occupied": slots[slot_id],
                "type":        "car",
                "locked":      True,   # cố định, không thay đổi
            }
        ],
    }
    client.publish(DATA_TOPIC, json.dumps(msg))
    print(f"[MQTT] SENT → {msg}")
 
 
# ── Callbacks MQTT ────────────────────────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[WiFi] Đã kết nối {BROKER}:{PORT}")
        client.subscribe(COMMAND_TOPIC)
        print(f"[MQTT] Subscribed → {COMMAND_TOPIC}")
        for slot_id in slots:
            publish(slot_id)
    else:
        print(f"[MQTT] Kết nối thất bại, rc={rc}")
 
 
def on_message(client, userdata, msg):
    # Nhận lệnh từ server nhưng không thay đổi trạng thái khoá
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"[MQTT] RECV ← {payload} (lệnh khoá bị bỏ qua)")
    except Exception as e:
        print(f"[CMD] Lỗi: {e}")
 
 
def on_disconnect(client, userdata, rc):
    print(f"[MQTT] Ngắt kết nối (rc={rc})")
 
 
# ── CLI ───────────────────────────────────────────────────────────────────────
def print_ui():
    print("\n╔══════════════ PARKING STATUS ══════════════╗")
    keys = [f"A{i}" for i in range(1, 41)]
    for row_start in range(0, 40, 4):
        row = keys[row_start:row_start + 4]
        line = "║  " + "   ".join(
            f"{s}:{'●' if slots[s] else '○'}" for s in row
        )
        print(line.ljust(45) + "║")
    print("╚════════════════════════════════════════════╝")
    print("Lệnh: [A1–A20] toggle xe  |  [Q] thoát")
 
 
def toggle_slot(slot_id):
    slots[slot_id] = not slots[slot_id]
    state = "CÓ XE" if slots[slot_id] else "TRỐNG"
    print(f"[SENSOR] Slot {slot_id} → {state}")
    publish(slot_id)
 
 
def cli_loop():
    while True:
        print_ui()
        cmd = input(">> ").strip().upper()
        if cmd == "Q":
            break
        if cmd in slots:
            toggle_slot(cmd)
        else:
            print("[CLI] Lệnh không hợp lệ.")
 
 
# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect
 
    print(f"[SYS] Đang kết nối {BROKER}:{PORT} ...")
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()
 
    try:
        cli_loop()
    finally:
        client.loop_stop()
        client.disconnect()
        print("[SYS] Đã ngắt kết nối.")