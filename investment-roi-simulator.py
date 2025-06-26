"""
Hire Payback Simulation Tool
===========================

Purpose
-------
Estimate the pay‑back period (months until discounted cumulative cash flow
turns non‑negative) for a newly hired consultant in a large IT consulting
firm, using parameters sourced mainly from Japanese government statistics
(as of 25 Jun 2025).

Key References (Japanese)
-------------------------
* 厚生労働省「賃金構造基本統計調査 令和5年」
* 厚生労働省「能力開発基本調査 令和5年度」
* 厚生労働省「雇用動向調査 令和5年」
* Investing.com「日本10年債利回り」(2025‑06‑10 1.45 %)
* レバテック「職種別人月単価相場 2024」

Usage
-----
$ python hire_payback_simulation.py                  # run demo 5‑year simulation
$ python hire_payback_simulation.py --interactive   # interactive parameter input
$ python hire_payback_simulation.py --help          # show parameter options
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, asdict
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ──────────────────────────────────────────────────────────────────────────────
# Default parameters (can be overridden)
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_PARAMS: Dict[str, float] = {
    "salary": 6.4e6,                # 年俸 (¥)
    "benefit_rate": 0.15,           # 福利厚生率 (会社負担)
    "recruit_cost": 568e3,          # 1 名あたり採用コスト (¥)
    "direct_training_cost": 15e3,   # OFF‑JT 教材等直接費 (¥)
    "training_months": 3,           # 研修・非稼働月数 (M₀)
    "bill_rate_hour": 6_875,        # 請求単価 (¥/h)
    "hours_per_month": 160,         # 標準稼働時間 (h/mo)
    "variable_cost": 70e3,          # 案件変動費 (¥/mo)
    "overhead_cost": 50e3,          # 本社配賦 (¥/mo)
    "U_max": 0.75,                  # 完全稼働率
    "ramp_alpha": 0.35,             # ランプアップ係数 (指数)
    "discount_rate_annual": 0.0145, # 割引率 (年率, 10 年国債利回り)
}

# Parameter descriptions for user interface
PARAM_DESCRIPTIONS: Dict[str, str] = {
    "salary": "年俸 (円)",
    "benefit_rate": "福利厚生率 (0.0-1.0)",
    "recruit_cost": "採用コスト (円)",
    "direct_training_cost": "研修直接費 (円)",
    "training_months": "研修期間 (月)",
    "bill_rate_hour": "請求単価 (円/時間)",
    "hours_per_month": "月間稼働時間 (時間)",
    "variable_cost": "月間変動費 (円)",
    "overhead_cost": "月間オーバーヘッド (円)",
    "U_max": "最大稼働率 (0.0-1.0)",
    "ramp_alpha": "ランプアップ係数",
    "discount_rate_annual": "年率割引率 (0.0-1.0)",
}

# ──────────────────────────────────────────────────────────────────────────────
def get_user_input() -> Dict[str, float]:
    """Interactive parameter input from user."""
    print("=== 投資ROIシミュレーター パラメータ入力 ===")
    print("各パラメータを入力してください（Enterでデフォルト値を使用）\n")
    
    params = {}
    for key, default_value in DEFAULT_PARAMS.items():
        description = PARAM_DESCRIPTIONS.get(key, key)
        
        while True:
            try:
                user_input = input(f"{description} (デフォルト: {default_value:,.0f}): ").strip()
                
                if user_input == "":
                    params[key] = default_value
                    break
                else:
                    value = float(user_input)
                    # Validation for specific parameters
                    if key == "benefit_rate" and not (0 <= value <= 1):
                        print("福利厚生率は0.0から1.0の間で入力してください")
                        continue
                    elif key == "U_max" and not (0 <= value <= 1):
                        print("最大稼働率は0.0から1.0の間で入力してください")
                        continue
                    elif key == "discount_rate_annual" and not (0 <= value <= 1):
                        print("割引率は0.0から1.0の間で入力してください")
                        continue
                    elif value < 0:
                        print("負の値は入力できません")
                        continue
                    
                    params[key] = value
                    break
            except ValueError:
                print("数値を入力してください")
    
    return params

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="投資ROIシミュレーター - 新規採用の投資回収期間を計算",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python %(prog)s                    # デフォルト値で実行
  python %(prog)s --interactive      # インタラクティブ入力
  python %(prog)s --salary 7000000   # 年俸を700万円に設定
  python %(prog)s --help             # 全オプションを表示
        """
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="インタラクティブモードでパラメータを入力"
    )
    
    parser.add_argument(
        "--horizon", "-H",
        type=int,
        default=60,
        help="シミュレーション期間（月） (デフォルト: 60)"
    )
    
    # Add arguments for each parameter
    for key, default_value in DEFAULT_PARAMS.items():
        description = PARAM_DESCRIPTIONS.get(key, key)
        parser.add_argument(
            f"--{key}",
            type=float,
            help=f"{description} (デフォルト: {default_value:,.0f})"
        )
    
    return parser.parse_args()

# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class SimulationResult:
    df: pd.DataFrame
    I0: float           # Initial Investment
    payback_month: int | None


class HireSimulation:
    """Simulate discounted cash flow for a single new hire."""

    def __init__(self, params: Dict[str, float] | None = None) -> None:
        self.p: Dict[str, float] = {**DEFAULT_PARAMS, **(params or {})}
        self.r_monthly: float = (1 + self.p["discount_rate_annual"]) ** (1 / 12) - 1

    # ──────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────
    def _ramp_up(self, t: int) -> float:
        """稼働率 U_t (t=1,2,…) を指数関数で計算"""
        return self.p["U_max"] * (1 - math.exp(-self.p["ramp_alpha"] * t))

    def _monthly_revenue(self, t: int) -> float:
        return (
            self.p["bill_rate_hour"]
            * self.p["hours_per_month"]
            * self._ramp_up(t)
        )

    def _monthly_direct_cost(self) -> float:
        salary_benefit = self.p["salary"] * (1 + self.p["benefit_rate"]) / 12
        return salary_benefit + self.p["variable_cost"]

    def _monthly_cash_flow(self, t: int) -> float:
        return self._monthly_revenue(t) - self._monthly_direct_cost() - self.p["overhead_cost"]

    def _discount(self, cf: float, t: int) -> float:
        return cf / ((1 + self.r_monthly) ** t)

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────
    def simulate(self, horizon_months: int = 60) -> SimulationResult:
        months = np.arange(1, horizon_months + 1)
        rows: List[Dict[str, float]] = []

        direct_monthly = self._monthly_direct_cost()
        # Initial investment I0 = recruiting + training
        C_train = (
            (self.p["salary"] * (1 + self.p["benefit_rate"]) / 12)
            * self.p["training_months"]
            + self.p["direct_training_cost"]
        )
        I0 = self.p["recruit_cost"] + C_train

        for t in months:
            cf = self._monthly_cash_flow(t)
            rows.append(
                {
                    "month": t,
                    "revenue": self._monthly_revenue(t),
                    "direct_cost": direct_monthly,
                    "cash_flow": cf,
                    "discounted_cf": self._discount(cf, t),
                }
            )

        df = pd.DataFrame(rows)
        df["cumulative_dcf"] = df["discounted_cf"].cumsum() - I0

        # Payback determination
        try:
            payback_month = int(df.loc[df["cumulative_dcf"] >= 0, "month"].iloc[0])
        except IndexError:
            payback_month = None

        return SimulationResult(df=df, I0=I0, payback_month=payback_month)

    # ──────────────────────────────────────────────────────────────────────
    def plot(self, result: SimulationResult, ax: plt.Axes | None = None) -> plt.Axes:
        ax = ax or plt.gca()
        ax.plot(result.df["month"], result.df["cumulative_dcf"], label="Cumulative DCF")
        ax.axhline(0, linewidth=0.8, linestyle="-")
        if result.payback_month:
            ax.axvline(result.payback_month, linestyle="--", linewidth=0.8)
            ax.text(
                result.payback_month,
                0,
                f"Payback {result.payback_month} mo",
                rotation=90,
                va="bottom",
            )
        ax.set_xlabel("Month")
        ax.set_ylabel("Cumulative DCF (¥)")
        ax.set_title("Payback Period Simulation")
        ax.legend()
        return ax

    def print_parameters(self) -> None:
        """現在のパラメータを表示"""
        print("\n=== 現在のパラメータ ===")
        for key, value in self.p.items():
            description = PARAM_DESCRIPTIONS.get(key, key)
            if key in ["benefit_rate", "U_max", "discount_rate_annual"]:
                print(f"{description}: {value:.3f}")
            else:
                print(f"{description}: ¥{value:,.0f}")


# ──────────────────────────────────────────────────────────────────────────────
# Stand‑alone execution
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = parse_arguments()
    
    # Parameter collection
    params = {}
    
    if args.interactive:
        params = get_user_input()
    else:
        # Collect non-None arguments
        for key in DEFAULT_PARAMS.keys():
            value = getattr(args, key)
            if value is not None:
                params[key] = value
    
    # Create simulation with parameters
    sim = HireSimulation(params)
    res = sim.simulate(args.horizon)

    # Display results
    print("─" * 60)
    sim.print_parameters()
    print("─" * 60)
    print("Initial Investment (I0): ¥{:,.0f}".format(res.I0))
    if res.payback_month:
        print(f"Payback Period        : {res.payback_month} months")
    else:
        print("Payback Period        : Not reached within horizon")

    # Optional quick‑look plot
    plt.figure(figsize=(8, 5))
    sim.plot(res)
    plt.tight_layout()
    plt.show()
