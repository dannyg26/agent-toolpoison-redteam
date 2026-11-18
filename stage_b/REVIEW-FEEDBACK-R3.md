# Revision 3 prelaunch review, 2026-11-17

Decision: the study design, professor-requirement mapping and configured $10
ceiling are acceptable for the proposed limited study. One local runtime fix
remains before a paid launch. No larger study, extra benchmark or paid test is
requested. This review did not commit files, rent a pod or collect model data.

## Revision-2 findings

1. FIXED: missing outcomes in secondary, capability and baseline reports remain
   unknown, planned inventories are used, conditional intervals are labelled,
   and an absent capability arm produces no fabricated paired comparison.
2. PARTLY FIXED: partial JSONL recovery, on-exit/local reporting, a five-minute
   reserve and stopping new requests/retries are implemented. However, the new
   SDK timeout is not a total elapsed-time deadline; see the counterexample below.
3. FIXED: the bootstrap reads authenticated createdAt and compares against the
   configured deadline within five seconds; the wrong-timer regressions pass.
4. FIXED: secondary/capability summaries no longer emit hypothesis-test p-values.

All 12 supplied test groups passed in the existing AgentDojo environment. Both
freeze checks passed, and the cost worksheet reproduced. No frozen file was
changed during this review.

## Remaining issue: BLOCKING for the claimed graceful-stop guarantee

Files: heldout_runtime.py (_Completions.create), HELDOUT-PROTOCOL.md (Retries and
deadline), REVIEW-BRIEF.md (section 0 and shutdown description), test_heldout.py.

The protocol says:

> Every request that does start gets a timeout of min(300 s, time to the soft
> stop), so no in-flight request runs past the soft stop.

The implementation sets:

```python
kwargs["timeout"] = min(self.max_timeout, left)
return self.real.chat.completions.create(**kwargs)
```

This does not establish that conclusion. HTTPX timeouts govern separate network
operations; its read timeout bounds the wait for a response chunk, not the total
time to receive the response. A response arriving in chunks can exceed the
remaining budget without triggering that timeout. This is documented in the
[HTTPX timeout documentation](https://www.python-httpx.org/advanced/timeouts/).

Concrete free test with the real installed OpenAI SDK 3.52.0 and a localhost
HTTP server, with no model, provider or paid API:

- soft stop: 1.2 seconds after the request test starts;
- response: fixed benign completion JSON, sent in 15-byte chunks every 0.10 s;
- result: the actual DeadlineClient returned normally after **2.094 seconds**;
- deadline.stopped() was then true. No DeadlineStop interrupted the request.

The supplied active-request test uses a fake client that sleeps exactly for
kwargs["timeout"]. That assumes the timeout property needing verification and
does not test real SDK/HTTPX behavior.

Why it matters: a response can hold the synchronous request and ThreadPoolExecutor
open beyond the soft stop. Enough delay can consume the archival reserve and
recreate the interrupted-output problem. The independent pod guard still has its
hard deadline; this finding does not demonstrate a billing overrun or invalidate
the missing-outcome inference rules.

Fix: enforce a real elapsed-time bound for held-out execution, independently of
socket inactivity timeouts. A supervised harness subprocess that is terminated
at a defined cutoff while the parent runner survives to report/archive is one
option; actually cancellable I/O with a total deadline is another. A timeout on
waiting for a thread is insufficient if that thread continues and executor
shutdown waits for it. Retain completed records and classify interrupted/missing
work as unknown under the existing rules. Preserve the frozen pilot files.

Add a regression with a real localhost response delivered slowly through the
installed SDK. Confirm work stops/drains within a small explicit grace period
and the parent can still generate the planned-inventory report and archive.
Then make the protocol and brief describe the mechanism actually enforced.
Regenerate the held-out freeze after changes.

## Minimal reproduction

Run this with the existing .venv_stage_b Python from the repository root. It
uses only localhost and a fixed harmless response. It does not read any key.

```python
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import openai

sys.path.insert(0, str(Path("stage_b").resolve()))
import heldout_runtime as R

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        body = json.dumps({
            "id": "local-test", "object": "chat.completion", "created": 0,
            "model": "local-test", "choices": [{"index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "OK"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1,
                      "total_tokens": 2},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            for i in range(0, len(body), 15):
                self.wfile.write(body[i:i + 15])
                self.wfile.flush()
                time.sleep(0.10)
        except (BrokenPipeError, ConnectionResetError):
            pass

server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
client = openai.OpenAI(
    base_url=f"http://127.0.0.1:{server.server_port}/v1",
    api_key="LOCAL_TEST_ONLY", max_retries=0,
)
try:
    start = time.monotonic()
    deadline = R.Deadline(start + 1.2, clock=time.monotonic)
    wrapped = R.DeadlineClient(client, deadline, 300)
    wrapped.chat.completions.create(
        model="local-test", messages=[{"role": "user", "content": "Return OK"}])
    print({"elapsed": time.monotonic() - start,
           "returned_after_soft_stop": deadline.stopped()})
finally:
    client.close()
    server.shutdown()
    server.server_close()
```

## Professor requirements and budget

No change is requested to the recent uncensored main attacker, its aligned
control, the 12-task benign tool-use assessment, the 32-case study or the
interpretation limits. These address the professor's supplied requirements as
proposed; the new capability outcomes remain uncollected evidence, not a passed
gate or comprehensive validation.

The reproduced worksheet remains 85.0 minutes/$3.14 normal and 176.3 minutes/$6.52
conservative, with model work intended to stop at 184 minutes and the hard pod
cutoff at 189 minutes. The configured cost is $6.993 at $2.22/hour, approximately
$7.09 including the stated allowance, within $10 assuming successful termination.
The disclosed extreme case may not finish. No balance or price was re-queried.

After the narrow runtime fix and its real-client regression pass, the remaining
steps are to freeze and externally timestamp the final procedure, refresh the
read-only launch checks and obtain the user's approval for the concrete paid
launch. This review itself is not paid-launch authorization.
