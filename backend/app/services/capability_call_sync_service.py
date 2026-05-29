import json

from app.services.capability_service import capability_service


class CapabilityCallSyncService:
    """Persist sandbox-side capability call audit records."""

    def sync_records(self, user_id, records):
        return capability_service.sync_call_records(user_id=user_id, records=records)

    def sync_jsonl(self, user_id, jsonl_text):
        records = []
        for line_no, line in enumerate(str(jsonl_text or "").splitlines(), start=1):
            text = line.strip()
            if not text:
                continue
            try:
                record = json.loads(text)
            except json.JSONDecodeError as exc:
                return None, f"Invalid JSONL on line {line_no}: {exc}"
            if not isinstance(record, dict):
                return None, f"Invalid JSONL on line {line_no}: record must be an object"
            records.append(record)
        return self.sync_records(user_id, records)


capability_call_sync_service = CapabilityCallSyncService()
