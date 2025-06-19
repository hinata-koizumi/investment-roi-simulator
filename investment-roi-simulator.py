# ──────────────────────────────────────────
# Cell 1: パラメータ入力セル
#@markdown ### パラメータ入力
from dataclasses import dataclass, replace

# 各パラメータを入力してください（単位：円/月、月数など）
採用費用         = 500000         #@param {type:"number", min:0, step:1000}
採用前分割月     = 1             #@param {type:"integer", min:1, max:3}
研修期間         = 3             #@param {type:"integer", min:0, max:12}
研修費用         = 300000         #@param {type:"number", min:0, step:1000}
OJT期間         = 6             #@param {type:"integer", min:0, max:12}
OJTコスト       = 600000         #@param {type:"number", min:0, step:1000}
初年度給与       = 6000000        #@param {type:"number", min:0, step:10000}
支援費           = 100000         #@param {type:"number", min:0, step:1000}
間接費月額       = 200000         #@param {type:"number", min:0, step:1000}
アサイン開始月   = 4             #@param {type:"integer", min:1, max:12}
月次売上         = 500000         #@param {type:"number", min:0, step:1000}
稼働率           = 0.8           #@param {type:"number", min:0.0, max:1.0, step:0.01}
労働時間         = 160           #@param {type:"integer", min:0, max:200}
割引率           = 0.03          #@param {type:"number", min:0.0, max:0.2, step:0.005}
計算期間         = 60            #@param {type:"integer", min:1, max:120}
シミュレーション回数 = 1000       #@param {type:"integer", min:1, max:10000}

@dataclass
class Params:
    採用費用: float
    採用前分割月: int
    研修期間: int
    研修費用: float
    OJT期間: int
    OJTコスト: float
    初年度給与: float
    支援費: float
    間接費月額: float
    アサイン開始月: int
    月次売上: float
    稼働率: float
    労働時間: int
    割引率: float
    計算期間: int
    シミュレーション回数: int

# パラメータをParamsオブジェクトにまとめる
params = Params(
    採用費用, 採用前分割月, 研修期間, 研修費用,
    OJT期間, OJTコスト, 初年度給与, 支援費,
    間接費月額, アサイン開始月, 月次売上,
    稼働率, 労働時間, 割引率, 計算期間, シミュレーション回数
)
print("パラメータを設定しました。次のセルを実行してください。")
# ──────────────────────────────────────────

# ──────────────────────────────────────────
# Cell 2: シミュレーション＆可視化セル
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 単一シミュレーション関数
def simulate_cashflow(p: Params):
    months = np.arange(0, p.計算期間 + 1)
    df = pd.DataFrame({'month': months})

    # 月次固定コスト
    salary_m   = p.初年度給与 / 12
    support_m  = p.支援費     / 12
    overhead_m = p.間接費月額

    # 研修コスト: 線形減衰ウェイト
    if p.研修期間 > 0:
        w = np.linspace(1, 0, p.研修期間)
        w /= w.sum()
        train = np.concatenate([np.zeros(1), w * p.研修費用,
                                np.zeros(p.計算期間 - p.研修期間)])
    else:
        train = np.zeros_like(months, dtype=float)

    # OJTコスト: 線形減衰ウェイト
    if p.OJT期間 > 0:
        w2 = np.linspace(1, 0, p.OJT期間)
        w2 /= w2.sum()
        ojt = np.concatenate([
            np.zeros(1 + p.研修期間),
            w2 * p.OJTコスト,
            np.zeros(p.計算期間 - p.研修期間 - p.OJT期間)
        ])
    else:
        ojt = np.zeros_like(months, dtype=float)

    # 採用費: 月0に計上
    hire = np.zeros_like(months, dtype=float)
    hire[0] = p.採用費用

    # 合算コスト
    df['cost'] = salary_m + support_m + overhead_m
    df['training_cost'] = train
    df['ojt_cost'] = ojt
    df['hire_cost'] = hire
    df['cost'] += df['training_cost'] + df['ojt_cost'] + df['hire_cost']

    # 売上: アサイン後3ヶ月でランプアップ
    def prod_factor(m):
        if m < p.アサイン開始月:
            return 0
        ramp = 3
        return min(max((m - p.アサイン開始月 + 1) / ramp, 0), 1)

    df['prod_factor'] = df['month'].apply(prod_factor)
    df['revenue'] = p.月次売上 * p.稼働率 * df['prod_factor']

    # キャッシュフロー計算
    df['net_cashflow'] = df['revenue'] - df['cost']
    df['cum_cashflow'] = df['net_cashflow'].cumsum()

    # 割引率を月次化
    if p.割引率 > 0:
        r_m = (1 + p.割引率) ** (1/12) - 1
        df['discount_factor'] = (1 + r_m) ** df['month']
        df['pv_cashflow'] = df['net_cashflow'] / df['discount_factor']
        df['cum_pv'] = df['pv_cashflow'].cumsum()

    return df

# 回収ポイント検出

def find_breakeven(df):
    be = df[df['cum_cashflow'] >= 0]['month']
    return int(be.iloc[0]) if not be.empty else None

# 単一シミュレーション実行
single = simulate_cashflow(params)
breakeven = find_breakeven(single)
print(f"🔹 回収達成月: {breakeven} ヶ月目" if breakeven is not None else "⚠️ 回収ポイントに到達しませんでした。")
# 表示
from IPython.display import display
display(single.head(12))

# グラフ描画: 累積キャッシュフロー
plt.figure()
plt.plot(single['month'], single['cum_cashflow'], marker='o')
if breakeven is not None:
    plt.axvline(breakeven, linestyle='--')
plt.axhline(0, linestyle='--')
plt.xlabel('Month')
plt.ylabel('Cumulative Cashflow (¥)')
plt.title('累積キャッシュフロー推移')
plt.grid(True)
plt.show()

# グラフ描画: NPV推移
if params.割引率 > 0:
    plt.figure()
    plt.plot(single['month'], single['cum_pv'], marker='o')
    if breakeven is not None:
        plt.axvline(breakeven, linestyle='--')
    plt.axhline(0, linestyle='--')
    plt.xlabel('Month')
    plt.ylabel('累積PV (¥)')
    plt.title('NPV推移')
    plt.grid(True)
    plt.show()

# モンテカルロシミュレーション
breakevens = []
for _ in range(params.シミュレーション回数):
    kr = np.clip(np.random.normal(params.稼働率, 0.05), 0, 1)
    ms = max(0, np.random.normal(params.月次売上, params.月次売上*0.1))
    p2 = replace(params, 稼働率=kr, 月次売上=ms)
    df2 = simulate_cashflow(p2)
    br = find_breakeven(df2)
    if br is not None:
        breakevens.append(br)

# 統計結果とヒストグラム
if breakevens:
    import statistics
    median_be = statistics.median(breakevens)
    p5, p95 = np.percentile(breakevens, [5, 95])
    print(f"モンテカルロ回収月（中央値）: {median_be} ヶ月目")
    print(f"モンテカルロ回収月（5-95パーセンタイル）: {p5:.1f} - {p95:.1f} ヶ月目")
    plt.figure()
    plt.hist(breakevens, bins=20)
    plt.xlabel('回収達成月')
    plt.ylabel('頻度')
    plt.title('回収月の分布（モンテカルロ）')
    plt.grid(True)
    plt.show()
else:
    print("⚠️ モンテカルロで回収ポイントに到達したシミュレーションがありませんでした。")
# ──────────────────────────────────────────
