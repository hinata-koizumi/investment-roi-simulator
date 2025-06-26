# Investment ROI Simulator / 投資回収シミュレーター

## 全体像

### 目標

新卒・中途にかかわらず「新規採用者 1 名あたり」の

① 採用＋育成コスト（= 初期投資） と  
② その後に生み出すキャッシュフロー

を時系列で推定し、**割引現在価値（DCF）**ベースで累積したときに損益がプラスに転じる時点＝回収期間（Payback Period） を可視化する。

---

## 主要ステップとフォーミュラ

| ステップ | 計算項目 | 数式・ロジック | 備考 |
|---------|---------|---------------|------|
| **① 採用コスト** | $C_{rec}$ | $C_{src} + C_{scr} + C_{int} + C_{off} + C_{rel}$ | ソーシング、スクリーニング、面接、オファー交渉、移転補助など |
| **② 育成コスト** | $C_{train}$ | $C_{dir} + (S + B) \times M_0 + C_{trn}$ | 直接研修費 + 研修中の給与・福利厚生（非稼働月数 $M_0$）+ トレーナー工数等 |
| **③ 初期投資** | $I_0$ | $C_{rec} + C_{train}$ | シミュレーション開始時点 ($t=0$) に一括計上 |
| **④ 売上（毎月）** | $R_t$ | $\text{BillRate} \times H \times U_t$ | BillRate＝時間単価、$H$＝標準稼働時間、$U_t$＝月次稼働率 |
| **⑤ 稼働率ランプアップ** | $U_t$ | $U_{\max}(1-e^{-\alpha t})$ または $U_{\max}\frac{t}{T_{rmp}}$ | 指数型 or 線形。$t$ は月、$T_{rmp}$ は完全稼働に要する月数 |
| **⑥ 直接コスト（毎月）** | $D_t$ | $\frac{S + B}{12} + C_{var}$ | 給与・福利厚生（月割り） + 変動間接費 |
| **⑦ キャッシュフロー** | $CF_t$ | $R_t - D_t - C_{oh}$ | $C_{oh}$：固定間接費配賦 |
| **⑧ 割引キャッシュフロー** | $DCF_t$ | $\frac{CF_t}{(1+r)^{t/12}}$ | $r$＝割引率（WACC など） |
| **⑨ 累積 DCF** | $N_t$ | $-I_0 + \sum_{i=1}^{t} DCF_i$ | 初期投資を引いた累計 |
| **⑩ 回収期間** | $T_{pay}$ | $\min\{t \mid N_t \geq 0\}$ | 月単位で判定 |
| **⑪ ROI（任意）** | $\text{ROI}$ | $\frac{\sum_{t=1}^{T}CF_t - I_0}{I_0} \times 100\%$ | Phillips ROI モデル等と互換 |

---

## 既存指標・フレームワークとの対応

| 目的 | 本提案の式 | 既存指標・フレームワーク |
|------|------------|------------------------|
| 採用コスト算出 | $C_{rec}$ | **Cost Per Hire** (SHRM) |
| 育成 ROI | ROI 式 | **Phillips ROI**／Kirkpatrick L4 |
| 時間価値考慮 | $DCF_t$ | **NPV/DCF**（財務会計標準） |
| 回収期間 | $T_{pay}$ | **Payback Period**（資本予算） |

## 使い方・パラメータ変更方法

### 基本的な実行

```bash
python investment-roi-simulator.py
```

### パラメータをコマンドラインで変更

例: 年俸を700万円、請求単価を8000円/時、研修期間を6ヶ月に設定

```bash
python investment-roi-simulator.py --salary 7000000 --bill_rate_hour 8000 --training_months 6
```

利用可能なパラメータ一覧や説明は `--help` で確認できます。

```bash
python investment-roi-simulator.py --help
```

### インタラクティブモードで変更

対話形式で全パラメータを一つずつ入力できます（Enterでデフォルト値を使用）:

```bash
python investment-roi-simulator.py --interactive
``` 