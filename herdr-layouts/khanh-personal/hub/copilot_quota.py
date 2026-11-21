"""Read the signed-in user's Copilot quota through the official SDK."""
import asyncio
import json
import time

from copilot import CopilotClient
from copilot.generated.rpc import AccountGetQuotaRequest


async def main():
    client = CopilotClient()
    await client.start()
    try:
        result = await client.rpc.account.get_quota(AccountGetQuotaRequest())
    finally:
        await client.stop()
    windows = []
    for key, name in (("premium_interactions", "premium"), ("chat", "chat")):
        snapshot = result.quota_snapshots.get(key)
        if not snapshot or snapshot.entitlement_requests <= 0 or snapshot.is_unlimited_entitlement:
            continue
        reset = snapshot.reset_date
        reset_at = None
        if reset:
            from datetime import datetime
            reset_at = datetime.fromisoformat(reset.replace("Z", "+00:00")).timestamp()
        if reset_at is not None and reset_at <= time.time():
            continue
        windows.append({"name": name, "used_percent": 100 - snapshot.remaining_percentage, "resets_at": reset_at})
    if windows:
        print(json.dumps({"state": "read", "observed_at": time.time(), "windows": windows}))
    else:
        print(json.dumps({"state": "unreadable", "reason": "Copilot returned no finite account quota"}))


if __name__ == "__main__":
    asyncio.run(main())
