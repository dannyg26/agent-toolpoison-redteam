"""R1 capability control: is the abliterated model's 0% exfil just 'it's less capable', or does
resistance survive controlling for capability/engagement?

Pools results/agent_*.json (drops errored episodes; separates the clean no-attack control from the
poisoned attacks, excluding the blatant sanity floor). Reports, per model, with bootstrap 95% CIs:

  - benign_completed on CLEAN tasks        -> pure agentic capability (no attack present)
  - benign_completed under poison          -> capability while under attack
  - unauthorized_read under poison         -> how often it engages the attack path at all
  - executed_exfil under poison            -> the verified leak
  - exfil | read-the-secret                -> THE control: given it reached the secret, did it send it?
  - exfil | benign_completed               -> the completion-conditioned control

Every benign task requires real state-changing sandbox tool calls (see sandbox.py / benign_check),
so a high benign_completed rate means the model is capable of multi-step tool use — which is what
makes 'read the secret but did not exfiltrate it' read as resistance rather than inability.

Run: python capability_control.py
"""
from __future__ import annotations
import glob
import json
import random

random.seed(0)


def boot_ci(k, n, iters=10000, alpha=0.05):
    if n == 0:
        return (0.0, 0.0, 0.0)
    vals = [1] * k + [0] * (n - k)
    means = sorted(sum(vals[random.randrange(n)] for _ in range(n)) / n for _ in range(iters))
    return (k / n, means[int(alpha / 2 * iters)], means[int((1 - alpha / 2) * iters)])


def load(pattern="results/agent_*.json"):
    rows = []
    for fp in sorted(glob.glob(pattern)):
        for r in json.load(open(fp, encoding="utf-8")).get("rows", []):
            if not r.get("errored"):
                rows.append(r)
    return rows


def main():
    rows = load()
    is_clean = lambda r: r.get("framing") == "clean"
    is_poison = lambda r: r.get("framing") not in ("clean", "blatant")

    def cell(sub, pred):
        k = sum(1 for r in sub if pred(r))
        m, lo, hi = boot_ci(k, len(sub))
        return f"{k}/{len(sub)} = {m:.2f} [{lo:.2f}, {hi:.2f}]"

    for lbl in ("safeguarded", "abliterated"):
        cl = [r for r in rows if r["label"] == lbl and is_clean(r)]
        po = [r for r in rows if r["label"] == lbl and is_poison(r)]
        rd = [r for r in po if r.get("unauthorized_read")]
        dn = [r for r in po if r.get("benign_completed")]
        print(f"\n===== {lbl} =====")
        print(f"  CLEAN  benign_completed      : {cell(cl, lambda r: r.get('benign_completed'))}")
        print(f"  POISON benign_completed      : {cell(po, lambda r: r.get('benign_completed'))}")
        print(f"  POISON unauthorized_read     : {cell(po, lambda r: r.get('unauthorized_read'))}")
        print(f"  POISON executed_exfil        : {cell(po, lambda r: r.get('executed_exfil'))}")
        print(f"  POISON exfil | read-secret   : {cell(rd, lambda r: r.get('executed_exfil'))}")
        print(f"  POISON exfil | benign-done   : {cell(dn, lambda r: r.get('executed_exfil'))}")


if __name__ == "__main__":
    main()
