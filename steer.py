"""Phase 1: the CLEAN safeguard dial via inference-time directional ablation (activation steering).

Instead of permanently editing weights by a fraction (Phase 0 showed that gives a lumpy,
threshold-like response), we ablate the refusal direction LIVE during generation with a continuous
coefficient alpha in [0,1]:

    at every layer's residual output h:   h <- h - alpha * (h . d_hat) * d_hat

alpha=0 is the untouched model; alpha=1 fully removes the direction's component at every layer;
values between give a smooth dial. One model load; hooks are added/removed per alpha, so nothing is
saved to disk and the sweep is cheap.

Usage (on a GPU box, after extracting a direction with refusal_direction.py):
    python steer.py --model unsloth/gpt-oss-20b-BF16 --dirs dir_20b/directions.pt --layer 13 \
        --harmful strongreject_dataset.csv --alphas 0,0.25,0.5,0.75,1.0
"""
from __future__ import annotations
import argparse
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from refusal_direction import read_harmful, is_refusal


def to_chat(tok, prompt):
    """gpt-oss harmony chat template; keep reasoning short so generation reaches the final channel."""
    msgs = [{"role": "user", "content": prompt}]
    try:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                       reasoning_effort="low")
    except TypeError:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)


def final_channel(text):
    """Extract the gpt-oss 'final' channel answer from a raw (special-tokens-kept) decode. Refusals
    live in the final channel, not the analysis/reasoning channel, so we must read it specifically.
    Falls back to the whole text if the final channel was not reached (truncated mid-reasoning)."""
    parts = re.split(r"<\|channel\|>\s*final\s*<\|message\|>", text)
    if len(parts) > 1:
        ans = re.split(r"<\|return\|>|<\|end\|>|<\|channel\|>", parts[-1])[0]
        return ans.strip()
    return re.sub(r"<\|[^|>]*\|>", " ", text).strip()   # fallback: strip harmony tokens


def load(model_id):
    tok = AutoTokenizer.from_pretrained(model_id)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype="auto", device_map="auto", trust_remote_code=True).eval()
    return tok, model


def decoder_layers(model):
    """Return the list of transformer blocks (robust to a few naming conventions)."""
    for path in ("model.layers", "model.model.layers", "transformer.h", "gpt_neox.layers"):
        obj = model
        try:
            for part in path.split("."):
                obj = getattr(obj, part)
            return obj
        except AttributeError:
            continue
    raise RuntimeError("could not locate decoder layers")


def add_ablation_hooks(model, d_unit, alpha):
    """Project the (unit) refusal direction out of every layer's residual output, scaled by alpha."""
    handles = []

    def make_hook():
        def hook(mod, inp, out):
            hs = out[0] if isinstance(out, tuple) else out
            d = d_unit.to(hs.dtype).to(hs.device)
            coef = (hs @ d).unsqueeze(-1)          # [b, seq, 1]
            hs = hs - alpha * coef * d
            if isinstance(out, tuple):
                return (hs,) + tuple(out[1:])
            return hs
        return hook

    for layer in decoder_layers(model):
        handles.append(layer.register_forward_hook(make_hook()))
    return handles


@torch.no_grad()
def refusal_rate(tok, model, prompts, max_new=256):
    refused = 0
    for p in prompts:
        enc = tok(to_chat(tok, p), return_tensors="pt", add_special_tokens=False).to(model.device)
        out = model.generate(**enc, max_new_tokens=max_new, do_sample=False,
                             pad_token_id=tok.eos_token_id)
        # keep special tokens so we can locate the harmony 'final' channel, then score that answer
        raw = tok.decode(out[0, enc.input_ids.shape[1]:], skip_special_tokens=False)
        refused += int(is_refusal(final_channel(raw)))
    return refused / len(prompts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dirs", required=True, help="directions.pt from refusal_direction.py extract")
    ap.add_argument("--layer", type=int, required=True, help="which layer's direction to ablate")
    ap.add_argument("--harmful", required=True)
    ap.add_argument("--alphas", default="0,0.25,0.5,0.75,1.0")
    ap.add_argument("--n", type=int, default=0, help="limit #prompts (0 = all)")
    ap.add_argument("--max-new", type=int, default=128)
    args = ap.parse_args()

    tok, model = load(args.model)
    d = torch.load(args.dirs, map_location="cpu")["dirs"][args.layer]
    d = d / d.norm().clamp_min(1e-8)
    prompts = read_harmful(args.harmful, args.n or None)
    print(f"model={args.model} layer={args.layer} n_prompts={len(prompts)}", flush=True)

    for a in [float(x) for x in args.alphas.split(",")]:
        h = add_ablation_hooks(model, d, a)
        try:
            r = refusal_rate(tok, model, prompts, args.max_new)
        finally:
            for x in h:
                x.remove()
        print(f"alpha={a:<5} refusal_rate={r:.3f}", flush=True)


if __name__ == "__main__":
    main()
