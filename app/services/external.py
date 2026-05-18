# app/services/push_with_data.py
import asyncio
import httpx

from app.core.logger import logger



WITH_DATA_URL = "http://127.0.0.1:8000/api/devices/with-data"
WITH_DATA_API_KEY = "abc"
TARGET_ENDPOINT = "https://server-kia.com/api/receive-with-data"

# TODO: API key để server bên kia xác thực request từ platform hiện tại.
TARGET_API_KEY = "abc"

DEBOUNCE_SECONDS = 0.3

_push_task: asyncio.Task | None = None
_push_requested = False


def schedule_push_with_data():
    global _push_task, _push_requested

    _push_requested = True

    if _push_task is None or _push_task.done():
        _push_task = asyncio.create_task(_push_loop())


async def _push_loop():
    global _push_requested

    while _push_requested:
        _push_requested = False
        await asyncio.sleep(DEBOUNCE_SECONDS)

        try:
            await push_with_data_now()
        except Exception as e:
            logger.error(f"Push /with-data failed: {e}")


async def push_with_data_now():
    async with httpx.AsyncClient(timeout=20) as client:
        # 1. Lấy full dữ liệu từ API /with-data của platform hiện tại
        source_response = await client.get(
            WITH_DATA_URL,
            headers={"apiKey": WITH_DATA_API_KEY},
        )
        source_response.raise_for_status()
        devices_with_data = source_response.json()

        # 2. Gửi nguyên dữ liệu đó sang server bên kia
        target_response = await client.post(
            TARGET_ENDPOINT,
            json=devices_with_data,
        )
        target_response.raise_for_status()

        logger.info(f"Pushed /with-data to target server: {len(devices_with_data)} devices")