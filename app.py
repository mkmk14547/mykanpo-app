"""
漢方処方 照合アプリ - Streamlit
======================================
・生薬名のテキストを貼り付けるだけで動作（API不要）
・F1スコア（適合率×再現率の調和平均）で精度の高い照合
・単剤ベスト3 ＋ 合剤（2処方の組み合わせ）ベスト3を表示
"""

import re
from itertools import combinations
from pathlib import Path

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────
#  ページ設定
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="漢方処方 照合アプリ",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
.stApp { background: #F5F0E8; }

.app-header {
    text-align:center; padding:1.2rem 0 0.8rem;
    background:linear-gradient(135deg,#2D5A1B,#5A8A3C);
    border-radius:14px; margin-bottom:1.4rem;
    box-shadow:0 4px 16px rgba(45,90,27,0.18);
}
.app-header h1 { color:white; font-size:1.9rem; font-weight:700; margin:0; letter-spacing:0.03em; }
.app-header p  { color:rgba(255,255,255,0.85); font-size:0.88rem; margin:0.3rem 0 0; }

.how-to-box {
    background:#EAF4FF; border-left:5px solid #1976D2;
    border-radius:10px; padding:0.9rem 1.2rem; margin-bottom:0.8rem;
    font-size:0.85rem; line-height:1.8; color:#1A237E;
}
.how-to-box b { color:#0D47A1; }

.detected-box {
    background:white; border-left:5px solid #52B788;
    border-radius:10px; padding:1rem 1.2rem; margin:1rem 0;
    box-shadow:0 2px 10px rgba(0,0,0,0.06);
}

/* 単剤カード */
.result-card {
    background:white; border-radius:14px; padding:1.3rem 1.1rem 1.1rem;
    box-shadow:0 4px 16px rgba(0,0,0,0.09); border-top:5px solid #2D5A1B;
    min-height:440px;
}
.result-card.rank2 { border-top-color:#5C8A3C; }
.result-card.rank3 { border-top-color:#8FB45A; }

/* 合剤カード */
.combo-card {
    background:white; border-radius:14px; padding:1.3rem 1.1rem 1.1rem;
    box-shadow:0 4px 16px rgba(0,0,0,0.09); border-top:5px solid #7B3F9E;
    margin-bottom:1rem;
}
.combo-card.crank2 { border-top-color:#9C6AB5; }
.combo-card.crank3 { border-top-color:#C39ED0; }
.combo-badge {
    display:inline-block; background:#F3E5FF; color:#5B1FA3;
    border:1px solid #CE93D8; border-radius:12px;
    padding:2px 10px; font-size:0.72rem; font-weight:700;
    margin-bottom:6px; letter-spacing:0.05em;
}
.combo-plus {
    text-align:center; font-size:1.4rem; color:#9C6AB5;
    margin:6px 0; font-weight:700;
}
.combo-name {
    font-size:1.1rem; font-weight:700; color:#2D1A3D; margin-bottom:2px;
}
.combo-yomi {
    font-size:0.75rem; color:#aaa; margin-bottom:6px;
}

/* スコアバー */
.bar-wrap {
    background:#E8F5E2; border-radius:20px; height:20px;
    margin:8px 0 4px; overflow:hidden;
}
.bar-fill {
    height:20px; border-radius:20px;
    background:linear-gradient(90deg,#68C472,#2D5A1B);
    display:flex; align-items:center; padding-left:8px;
    color:white; font-size:0.75rem; font-weight:700;
    white-space:nowrap; min-width:40px;
}
.bar-fill-combo {
    height:20px; border-radius:20px;
    background:linear-gradient(90deg,#CE93D8,#7B3F9E);
    display:flex; align-items:center; padding-left:8px;
    color:white; font-size:0.75rem; font-weight:700;
    white-space:nowrap; min-width:40px;
}

/* 効能テキスト */
.efficacy-box {
    font-size:0.79rem; color:#4A4A4A; background:#F8F5F0;
    border-radius:8px; padding:0.55rem 0.7rem; margin:4px 0 8px;
    line-height:1.6; max-height:80px; overflow-y:auto;
}

/* サブラベル */
.section-label {
    font-size:0.72rem; font-weight:700; letter-spacing:0.04em;
    margin:10px 0 4px; padding-bottom:2px; border-bottom:1px solid #eee;
}

/* スコア内訳バッジ */
.score-detail {
    font-size:0.7rem; color:#888; margin-bottom:4px;
    display:flex; gap:8px; flex-wrap:wrap;
}
.score-badge {
    background:#F0F0F0; border-radius:8px; padding:1px 7px;
    white-space:nowrap;
}

/* 生薬タグ */
.herb-tags { display:flex; flex-wrap:wrap; gap:5px; margin-bottom:6px; }
.herb-tag  { display:inline-block; padding:3px 9px; border-radius:14px; font-size:0.8rem; font-weight:500; line-height:1.5; }
.herb-match   { background:#D4EDDA; color:#1B5E20; border:1px solid #A5D6A7; }
.herb-missing { background:#FDECEA; color:#B71C1C; border:1px solid #FFAB91; }
.herb-extra   { background:#E3F2FD; color:#0D47A1; border:1px solid #90CAF9; }

.guide-box {
    text-align:center; padding:2.5rem 1rem; color:#888;
    background:white; border-radius:14px; box-shadow:0 2px 10px rgba(0,0,0,0.05);
}
.guide-box .icon { font-size:4rem; }
.guide-box h3    { color:#555; font-size:1.1rem; margin:0.5rem 0 0.3rem; }
.guide-box p     { font-size:0.85rem; line-height:1.7; }

div[data-testid="stButton"] button {
    background:linear-gradient(135deg,#52B788,#2D5A1B);
    color:white; border:none; border-radius:8px;
    font-weight:600; width:100%; font-size:1.05rem; padding:0.6rem 0;
}
div[data-testid="stButton"] button:hover {
    background:linear-gradient(135deg,#2D5A1B,#1A3D0D);
}
section[data-testid="stSidebar"] { background:#EDF4E8; }
textarea { font-size:1.05rem !important; line-height:1.8 !important; }

.section-header {
    font-size:1.3rem; font-weight:700; color:#2D5A1B;
    text-align:center; margin:1.5rem 0 0.8rem;
    padding-bottom:0.4rem; border-bottom:2px solid #A5D6A7;
}
.combo-section-header {
    font-size:1.3rem; font-weight:700; color:#7B3F9E;
    text-align:center; margin:1.5rem 0 0.8rem;
    padding-bottom:0.4rem; border-bottom:2px solid #CE93D8;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  ヘッダー
# ─────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <h1>🌿 漢方処方 照合アプリ</h1>
  <p>生薬名を貼り付けるだけで、単剤・合剤のベスト3を表示します</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  データ読み込み（起動時に1回だけ・キャッシュ）
# ─────────────────────────────────────────────
@st.cache_data
def load_prescriptions() -> tuple[dict, list[str]]:
    csv_path = Path(__file__).parent / "kampo_master.csv"
    if not csv_path.exists():
        return {}, []

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    prescriptions: dict = {}

    for _, row in df.iterrows():
        name = str(row["処方名"]).strip()
        if name not in prescriptions:
            prescriptions[name] = {
                "ID":       str(row["ID"]),
                "よみ":     str(row["よみ"]),
                "効能効果": str(row["効能効果"]),
                "生薬リスト": [],
            }
        herb = str(row["生薬名"]).strip()
        if herb and herb not in prescriptions[name]["生薬リスト"]:
            prescriptions[name]["生薬リスト"].append(herb)

    # 照合高速化: frozenset を事前構築
    for info in prescriptions.values():
        info["_herb_set"] = frozenset(info["生薬リスト"])

    all_herbs: list[str] = sorted(
        {h for p in prescriptions.values() for h in p["生薬リスト"]},
        key=len, reverse=True,
    )
    return prescriptions, all_herbs


prescriptions, all_herbs = load_prescriptions()

# ─────────────────────────────────────────────
#  サイドバー
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📖 使い方")
    st.markdown("---")
    st.markdown("""
**① iPhoneで写真を撮る**  
成分表・薬袋・処方箋を撮影します。

**② テキストをコピーする**  
写真を開いて文字を**長押し** → iOSが自動認識 →「すべてを選択」→「コピー」

**③ アプリに貼り付ける**  
テキストエリアを**長押し** →「ペースト」

**④「照合する」を押す**  
単剤ベスト3 ＋ 合剤ベスト3が表示されます。
    """)
    st.markdown("---")
    st.markdown("""
**手入力でも使えます**  
例：`ケイヒ カンゾウ ハンゲ`  
例：`桂皮、甘草、半夏`
    """)
    st.markdown("---")
    st.markdown(f"""
### 📊 データベース情報
- 処方数: **{len(prescriptions)} 件**
- 生薬種類: **{len(all_herbs)} 種**
    """)
    st.markdown("---")
    st.markdown("""
### 🎨 色の凡例
🟢 **緑** ＝ 一致している生薬  
🔴 **赤** ＝ 処方にあるが入力になし  
🔵 **青** ＝ 入力にあるが処方になし
    """)
    st.markdown("---")
    st.markdown("""
### 📐 スコアの計算方法
**F1スコア（調和平均）**  
`2×一致数 ÷ (処方の生薬数 + 入力の生薬数)`  

余剰生薬（入力したが処方にない）が多いほど  
スコアが自動的に下がります。
    """)

# ─────────────────────────────────────────────
#  session_state 初期化
# ─────────────────────────────────────────────
if "herb_input" not in st.session_state:
    st.session_state["herb_input"] = ""
if "results" not in st.session_state:
    st.session_state["results"] = None

# ─────────────────────────────────────────────
#  照合ロジック
# ─────────────────────────────────────────────
def parse_input_text(text: str) -> list[str]:
    text = re.sub(r"\d+\.?\d*\s*(?:g|mg|mL|ml|分|錠|包|日分)", "", text)
    tokens = re.split(r"[\n\r、，,・\s\t/／]+", text)
    return [t.strip() for t in tokens if len(t.strip()) >= 2]


def find_detected_herbs(tokens: list[str], herbs_db: list[str]) -> set[str]:
    detected: set[str] = set()
    combined = "".join(tokens)
    for herb in herbs_db:
        if herb in combined or any(t.strip() == herb for t in tokens):
            detected.add(herb)
    return detected


def f1_score(n_matched: int, n_prescription: int, n_detected: int) -> float:
    """
    F1スコア = 2×一致数 ÷ (処方の生薬数 + 入力の生薬数)
    - 余剰生薬（入力したが処方にない）が多いほど低くなる
    - 不足生薬（処方にあるが入力にない）が多いほど低くなる
    """
    denom = n_prescription + n_detected
    return (2 * n_matched / denom * 100) if denom > 0 else 0.0


def calc_match(detected: set[str], herb_set: frozenset) -> dict:
    matched = detected & herb_set
    missing = herb_set - detected
    extra   = detected - herb_set
    n_m     = len(matched)
    score   = f1_score(n_m, len(herb_set), len(detected))
    # 処方カバー率（処方の何割を入力がカバーするか）表示用
    cover   = n_m / len(herb_set) * 100 if herb_set else 0.0
    return {
        "score":   score,
        "cover":   cover,
        "matched": sorted(matched),
        "missing": sorted(missing),
        "extra":   sorted(extra),
    }


def calc_combo_match(detected: set[str], info1: dict, info2: dict) -> dict:
    union   = info1["_herb_set"] | info2["_herb_set"]
    matched = detected & union
    missing = union - detected
    extra   = detected - union
    n_m     = len(matched)
    score   = f1_score(n_m, len(union), len(detected))
    cover   = n_m / len(union) * 100 if union else 0.0
    return {
        "score":   score,
        "cover":   cover,
        "matched": sorted(matched),
        "missing": sorted(missing),
        "extra":   sorted(extra),
    }


def run_matching(text: str) -> dict | str:
    try:
        tokens = parse_input_text(text)
        if not tokens:
            return "no_tokens"

        detected = find_detected_herbs(tokens, all_herbs)
        if not detected:
            return "no_match"

        n_det = len(detected)

        # ── 単剤スコアリング ──────────────────────
        scored = sorted(
            [
                (name, info, calc_match(detected, info["_herb_set"]))
                for name, info in prescriptions.items()
            ],
            key=lambda x: x[2]["score"],
            reverse=True,
        )

        # ── 合剤スコアリング ──────────────────────
        # 少なくとも1種一致する処方だけを候補にして組み合わせ数を絞る
        candidates = [
            (name, info, diff)
            for name, info, diff in scored
            if len(diff["matched"]) >= 1
        ]
        # 候補が多すぎる場合は上位60件に制限（60×59/2=1770ペア）
        if len(candidates) > 60:
            candidates = candidates[:60]

        combo_scored = sorted(
            [
                (name1, name2, info1, info2,
                 calc_combo_match(detected, info1, info2))
                for (name1, info1, _d1), (name2, info2, _d2)
                in combinations(candidates, 2)
            ],
            key=lambda x: x[4]["score"],
            reverse=True,
        )

        # 合剤の最高スコアが単剤最高より高い場合のみ表示
        # （それ以外は「単剤で十分」のケースが多い）
        top3_combo = combo_scored[:3] if combo_scored else []

        return {
            "detected":   detected,
            "tokens":     tokens,
            "n_det":      n_det,
            "top3":       scored[:3],
            "top10":      scored[:10],
            "top3_combo": top3_combo,
        }
    except Exception as e:
        return f"error:{e}"


# ─────────────────────────────────────────────
#  コールバック
# ─────────────────────────────────────────────
def on_run():
    text = st.session_state.get("herb_input", "").strip()
    st.session_state["results"] = "empty" if not text else run_matching(text)


def on_clear():
    st.session_state["herb_input"] = ""
    st.session_state["results"]    = None


# ─────────────────────────────────────────────
#  HTML ヘルパー
# ─────────────────────────────────────────────
def _herb_tags(herbs: list[str], css: str) -> str:
    if not herbs:
        return '<span style="color:#bbb;font-size:0.75rem;">なし</span>'
    return "".join(f'<span class="herb-tag {css}">{h}</span>' for h in herbs)


def render_single_card(rank: int, name: str, info: dict, diff: dict) -> str:
    rank_class = {1: "", 2: " rank2", 3: " rank3"}[rank]
    medals     = {1: "🥇", 2: "🥈", 3: "🥉"}
    bar_w  = f"{min(diff['score'], 100):.0f}%"
    eff_s  = info["効能効果"][:130] + "…" if len(info["効能効果"]) > 130 else info["効能効果"]
    n_m    = len(diff["matched"])
    n_miss = len(diff["missing"])
    n_e    = len(diff["extra"])
    n_pre  = len(info["生薬リスト"])

    return f"""
<div class="result-card{rank_class}">
  <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
    <span style="font-size:1.5rem">{medals[rank]}</span>
    <span style="font-size:0.78rem;color:#888;font-weight:600">{rank}位</span>
  </div>
  <div style="font-size:1.25rem;font-weight:700;color:#1A3D0D;margin-bottom:1px">{name}</div>
  <div style="font-size:0.78rem;color:#999;margin-bottom:4px">{info["よみ"]}</div>
  <div class="bar-wrap"><div class="bar-fill" style="width:{bar_w}">F1 {diff["score"]:.0f}%</div></div>
  <div class="score-detail">
    <span class="score-badge">処方カバー率 {diff["cover"]:.0f}%</span>
    <span class="score-badge">一致 {n_m}/{n_pre}種</span>
    <span class="score-badge">不足 {n_miss}種</span>
    <span class="score-badge">余剰 {n_e}種</span>
  </div>
  <div class="efficacy-box">{eff_s}</div>
  <div class="section-label" style="color:#2D7A3C">✅ 一致している生薬（{n_m}種）</div>
  <div class="herb-tags">{_herb_tags(diff["matched"], "herb-match")}</div>
  <div class="section-label" style="color:#C62828">❌ 処方にある・入力にない（{n_miss}種）</div>
  <div class="herb-tags">{_herb_tags(diff["missing"], "herb-missing")}</div>
  <div class="section-label" style="color:#1565C0">➕ 入力にある・この処方にない（{n_e}種）</div>
  <div class="herb-tags">{_herb_tags(diff["extra"], "herb-extra")}</div>
</div>
"""


def render_combo_card(rank: int, name1: str, name2: str,
                      info1: dict, info2: dict, diff: dict) -> str:
    rank_class = {1: "", 2: " crank2", 3: " crank3"}[rank]
    medals     = {1: "🥇", 2: "🥈", 3: "🥉"}
    bar_w  = f"{min(diff['score'], 100):.0f}%"
    eff1   = info1["効能効果"][:80] + "…" if len(info1["効能効果"]) > 80 else info1["効能効果"]
    eff2   = info2["効能効果"][:80] + "…" if len(info2["効能効果"]) > 80 else info2["効能効果"]
    union_n = len(info1["_herb_set"] | info2["_herb_set"])
    n_m    = len(diff["matched"])
    n_miss = len(diff["missing"])
    n_e    = len(diff["extra"])

    return f"""
<div class="combo-card{rank_class}">
  <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
    <span style="font-size:1.5rem">{medals[rank]}</span>
    <span class="combo-badge">合剤 {rank}位</span>
  </div>
  <div class="combo-name">{name1}</div>
  <div class="combo-yomi">{info1["よみ"]}</div>
  <div class="efficacy-box">{eff1}</div>
  <div class="combo-plus">＋</div>
  <div class="combo-name">{name2}</div>
  <div class="combo-yomi">{info2["よみ"]}</div>
  <div class="efficacy-box">{eff2}</div>
  <div class="bar-wrap"><div class="bar-fill-combo" style="width:{bar_w}">F1 {diff["score"]:.0f}%</div></div>
  <div class="score-detail">
    <span class="score-badge">合計カバー率 {diff["cover"]:.0f}%</span>
    <span class="score-badge">一致 {n_m}/{union_n}種</span>
    <span class="score-badge">不足 {n_miss}種</span>
    <span class="score-badge">余剰 {n_e}種</span>
  </div>
  <div class="section-label" style="color:#2D7A3C;margin-top:10px">✅ 一致している生薬（{n_m}種）</div>
  <div class="herb-tags">{_herb_tags(diff["matched"], "herb-match")}</div>
  <div class="section-label" style="color:#C62828">❌ 合剤にある・入力にない（{n_miss}種）</div>
  <div class="herb-tags">{_herb_tags(diff["missing"], "herb-missing")}</div>
  <div class="section-label" style="color:#1565C0">➕ 入力にある・この合剤にない（{n_e}種）</div>
  <div class="herb-tags">{_herb_tags(diff["extra"], "herb-extra")}</div>
</div>
"""


# ─────────────────────────────────────────────
#  メインコンテンツ
# ─────────────────────────────────────────────
st.markdown("""
<div class="how-to-box">
  <b>📱 iPhoneでの手順：</b>
  写真を撮影 → 文字を<b>長押し</b>→「すべてを選択」→「コピー」→ 下に<b>長押し「ペースト」</b>→「照合する」<br>
  <b>✏️ 手入力も可能：</b> カタカナ（ケイヒ カンゾウ）や漢字（桂皮 甘草）をスペース・改行・読点で区切って入力できます。
</div>
""", unsafe_allow_html=True)

st.text_area(
    label="生薬名を入力・貼り付け",
    key="herb_input",
    placeholder="例：\nケイヒ\nカンゾウ\nハンゲ\nブクリョウ\nニンジン\n\n（漢字でも可：桂皮 甘草 半夏）",
    height=220,
    label_visibility="collapsed",
)

col_run, col_clear = st.columns([3, 1])
with col_run:
    st.button("🔍　照合する", on_click=on_run, use_container_width=True)
with col_clear:
    st.button("🗑️ クリア", on_click=on_clear, use_container_width=True)

# ─────────────────────────────────────────────
#  結果表示
# ─────────────────────────────────────────────
results = st.session_state["results"]

if results is None:
    st.markdown("""
<div class="guide-box">
  <div class="icon">🌿</div>
  <h3>生薬名を入力して「照合する」を押してください</h3>
  <p>
    カタカナ・漢字どちらでも認識します。<br>
    スペース・改行・読点（、）で区切って入力してください。<br>
    単剤ベスト3のほか、2処方を組み合わせた合剤候補も表示します。
  </p>
</div>
    """, unsafe_allow_html=True)

elif results == "empty":
    st.warning("⚠️ 生薬名を入力してから「照合する」を押してください。")

elif results == "no_tokens":
    st.warning("⚠️ テキストを認識できませんでした。生薬名を2文字以上で入力してください。")

elif results == "no_match":
    st.info(
        "データベースの生薬名と一致するものが見つかりませんでした。\n\n"
        "・カタカナ表記（ケイヒ、カンゾウ など）か漢字（桂皮、甘草 など）で入力してください\n"
        "・スペース・改行・読点で区切られているか確認してください"
    )

elif isinstance(results, str) and results.startswith("error:"):
    st.error(f"エラーが発生しました: {results[6:]}")
    st.caption("「クリア」を押してやり直してください。")

else:
    detected   = results["detected"]
    tokens     = results["tokens"]
    top3       = results["top3"]
    top10      = results["top10"]
    top3_combo = results["top3_combo"]

    # 検出生薬ボックス
    detected_tags = "".join(
        f'<span class="herb-tag herb-match">{h}</span>' for h in sorted(detected)
    ) or '<span style="color:#aaa">（一致する生薬が見つかりませんでした）</span>'

    st.markdown(f"""
<div class="detected-box">
  <b style="font-size:1rem">📋 認識された生薬（{len(detected)}種）</b>
  <div class="herb-tags" style="margin-top:8px">{detected_tags}</div>
  <details style="margin-top:8px">
    <summary style="font-size:0.75rem;color:#999;cursor:pointer">▶ 解析トークンを見る</summary>
    <div style="font-size:0.75rem;color:#777;margin-top:4px;line-height:1.8">{", ".join(tokens)}</div>
  </details>
</div>
    """, unsafe_allow_html=True)

    # ── 単剤 ベスト3 ─────────────────────────
    st.markdown(
        '<div class="section-header">🏆 単剤 ベスト3</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(3, gap="medium")
    for i, (name, info, diff) in enumerate(top3):
        with cols[i]:
            st.markdown(render_single_card(i + 1, name, info, diff), unsafe_allow_html=True)

    # 単剤 上位10テーブル
    with st.expander("📊 単剤 上位10処方の詳細スコアを見る"):
        st.dataframe(
            pd.DataFrame([
                {
                    "順位": f"{i+1}位",
                    "処方名": name,
                    "F1スコア": f"{diff['score']:.1f}%",
                    "処方カバー率": f"{diff['cover']:.1f}%",
                    "一致": f"{len(diff['matched'])}種",
                    "不足": f"{len(diff['missing'])}種",
                    "余剰": f"{len(diff['extra'])}種",
                    "処方生薬数": f"{len(info['生薬リスト'])}種",
                }
                for i, (name, info, diff) in enumerate(top10)
            ]),
            use_container_width=True,
            hide_index=True,
        )

    # ── 合剤 ベスト3 ─────────────────────────
    st.markdown(
        '<div class="combo-section-header">💊 おすすめの組み合わせ（合剤） ベスト3</div>',
        unsafe_allow_html=True,
    )

    if not top3_combo:
        st.info("有効な合剤の組み合わせが見つかりませんでした。")
    else:
        c_medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for rank, (name1, name2, info1, info2, diff) in enumerate(top3_combo, 1):
            with st.expander(
                f"{c_medals[rank]} {rank}位：{name1}  ＋  {name2}　　F1スコア {diff['score']:.1f}%",
                expanded=(rank == 1),
            ):
                st.markdown(
                    render_combo_card(rank, name1, name2, info1, info2, diff),
                    unsafe_allow_html=True,
                )
