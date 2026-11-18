"""Register the two Qwen3.8 checkpoints with BFCL (documented adapter, stage_a/GATE.md).

BFCL 2026.3.23 has no Qwen3.8 entry. This script adds two ModelConfig entries that reuse BFCL's existing
QwenFCHandler, which is Qwen's native function-calling format. The entries go next to the Qwen3-8B-FC entry
in the installed bfcl_eval/constants/model_config.py. A unified diff is written to --diff-out so the change
is saved with the results. Run it inside the BFCL environment:  python bfcl_adapter.py --diff-out PATH
"""
import argparse, difflib, importlib.util, pathlib, re, sys

MODELS = {
    "huihui-ai/Huihui-Qwen3.8-27B-abliterated-FC": ("huihui-ai/Huihui-Qwen3.8-27B-abliterated",
                                                    "Huihui-Qwen3.8-27B-abliterated (FC)"),
    "Qwen/Qwen3.8-27B-FC": ("Qwen/Qwen3.8-27B", "Qwen3.8-27B (FC)"),
}
ENTRY = '''    "{key}": ModelConfig(
        model_name="{name}",
        display_name="{display}",
        url="https://huggingface.co/{name}",
        org="{org}",
        license="apache-2.0",
        model_handler=QwenFCHandler,
        input_price=None,
        output_price=None,
        is_fc_model=True,
        underscore_to_dot=False,
    ),
'''


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--diff-out", required=True); a = ap.parse_args()
    spec = importlib.util.find_spec("bfcl_eval")
    if spec is None:
        sys.exit("bfcl_eval is not installed in this environment")
    path = pathlib.Path(spec.submodule_search_locations[0]) / "constants" / "model_config.py"
    src = path.read_text(encoding="utf-8")
    if all(f'"{k}"' in src for k in MODELS):
        print("adapter already applied"); return
    m = re.search(r'    "Qwen/Qwen3-8B-FC": ModelConfig\(.*?\n    \),\n', src, re.S)
    if not m:
        sys.exit("anchor entry Qwen/Qwen3-8B-FC not found; inspect model_config.py and update the adapter")
    add = "".join(ENTRY.format(key=k, name=n, display=d, org=n.split("/")[0]) for k, (n, d) in MODELS.items())
    new = src[:m.end()] + add + src[m.end():]
    pathlib.Path(a.diff_out).write_text("".join(difflib.unified_diff(
        src.splitlines(True), new.splitlines(True), "model_config.py (original)", "model_config.py (adapted)")))
    path.write_text(new, encoding="utf-8")
    print("adapter applied:", ", ".join(MODELS))


if __name__ == "__main__":
    main()
