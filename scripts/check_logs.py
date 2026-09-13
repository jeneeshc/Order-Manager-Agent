from google.cloud import logging
import json

client = logging.Client(project='cjs-designs-501004')
filter_str = 'resource.type="cloud_run_revision" AND resource.labels.service_name="cjs-agent"'
entries = list(client.list_entries(filter_=filter_str, page_size=60, max_results=60))
entries.reverse()

for e in entries:
    ts = e.timestamp.strftime('%H:%M:%S') if e.timestamp else ''
    payload = e.payload
    if isinstance(payload, dict):
        msg = payload.get('message') or json.dumps(payload)
        print(f"[{ts}] {msg}")
    elif payload:
        print(f"[{ts}] {payload}")
