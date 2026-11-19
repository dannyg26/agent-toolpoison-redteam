"""Render published aggregate results; does not collect data or rerun inference."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    root = Path(__file__).resolve().parent
    metrics = json.loads((root / "heldout_observed_metrics.json").read_text())
    result = metrics["primary"]["complete_pairs_conditional"]
    output = root / "capstone_assets"
    output.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 3.8),
                                    gridspec_kw={"width_ratios": [1.1, 1]})
    names = ["Both succeed", "Uncensored only", "Aligned only", "Neither succeeds"]
    values = [result[key] for key in
              ("both", "abliterated_only", "aligned_only", "neither")]
    left.barh(names, values, color=["#527c9b", "#207567", "#a76c2c", "#858b93"])
    left.invert_yaxis()
    left.set_xlim(0, max(values) + 3)
    left.set_xlabel("Paired cases (32 total)")
    left.set_title("Observed campaign outcomes", loc="left", fontweight="bold")
    for index, value in enumerate(values):
        left.text(value + .25, index, str(value), va="center")

    estimate = 100 * result["difference"]
    low, high = [100 * value for value in result["tango_95ci"]]
    right.axvline(0, color="#767676", linestyle="--", linewidth=1)
    right.errorbar([estimate], [0], xerr=[[estimate - low], [high - estimate]],
                   fmt="o", capsize=6, color="#207567", markersize=8, linewidth=2)
    right.set_xlim(-30, 30)
    right.set_ylim(-.6, .6)
    right.set_yticks([])
    right.set_xticks([-30, -20, -10, 0, 10, 20, 30])
    right.set_xlabel("Uncensored − aligned (percentage points)")
    right.set_title("Primary difference and 95% interval", loc="left", fontweight="bold")
    right.text(estimate, .21, f"{estimate:+.1f} pp", ha="center", fontweight="bold")
    right.text(0, -.26, f"Tango 95% CI: {low:+.1f} to {high:+.1f} pp\n"
               f"Exact McNemar p = {result['mcnemar_exact_p']:.2f}", ha="center")
    fig.tight_layout(w_pad=3)
    for extension in ("png", "svg"):
        fig.savefig(output / f"paired_results.{extension}", dpi=200,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Rendered published results to capstone_assets/paired_results.{png,svg}")


if __name__ == "__main__":
    main()
