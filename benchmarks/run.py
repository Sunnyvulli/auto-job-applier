"""Synthetic local benchmark. No network, personal information or timing assertions."""
import json
import statistics
import tempfile
import time
from pathlib import Path
from applypilot.core import Store,documents
from applypilot.productivity import plan_queue

def measure(call):
    start=time.perf_counter();result=call();return time.perf_counter()-start,result

def run():
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder)
        rows=[dict(url=f'https://example.com/jobs/{i}',company='Synthetic Company',title='Data Engineer',location='Remote',description='Python SQL AWS. '+('Source description. '*100)) for i in range(10000)]
        single=Store(root/'single');batch=Store(root/'batch')
        single_s,_=measure(lambda:[single.add(j) for j in rows[:1000]])
        bulk_s,_=measure(lambda:batch.add_many(rows[:1000]))
        store=Store(root/'large');tenk_s,_=measure(lambda:store.add_many(rows))
        pages=[measure(lambda:store.page(limit=100))[0]*1000 for _ in range(25)]
        queue_s,ids=measure(lambda:plan_queue(store,{'skills':'Python, SQL, AWS'},{'titles':'Data Engineer','min_skills':2,'queue_limit':10}))
        job=store.job(ids[0]);profile={'name':'Synthetic User','email':'test@example.com','skills':'Python, SQL'}
        doc_s,_=measure(lambda:documents(store,profile,job));cache_s,_=measure(lambda:documents(store,profile,job))
        return {'environment':'Linux development container; synthetic records, not laptop measurements','jobs':10000,'single_insert_1000_seconds':round(single_s,4),'bulk_insert_1000_seconds':round(bulk_s,4),'bulk_speedup_1000':round(single_s/bulk_s,2),'bulk_insert_10000_seconds':round(tenk_s,4),'page_100_rows_median_ms':round(statistics.median(pages),3),'queue_scan_10000_seconds':round(queue_s,4),'queue_size':len(ids),'document_first_seconds':round(doc_s,4),'document_cached_seconds':round(cache_s,4)}

if __name__=='__main__':
    result=run();Path('benchmarks/results-linux.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
