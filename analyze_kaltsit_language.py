#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ケルシー言語特徴分析ツール
ケルシーのセリフの文体・性格特徴を分析する
(旧: 普瑞赛斯/中国語前提の分析器を日本語向けに最適化)

中国語前提で日本語に不向きだった点の最適化:
- jieba 分詞 → Janome (日本語形態素解析) に変更。未導入時はフォールバック
- 中国語ストップワード → 日本語助詞・助動詞ストップワードに変更
- 中国語句式判定 (吗/呢/如果/难道) → 日本語句式判定 (か？/もし〜なら/なぜ等) に変更
- 性格・感情キーワードを中国語 → 日本語(ケルシーの厳格・医師・指導者像)に変更
- clean_text を日本語データ用に調整 (（ト書き）/{@nickname}/全角スペース等)
- レポート・統計単位を中国語「字」→ 日本語「文字」に変更

使い方:
    python analyze_kaltsit_language.py
    python analyze_kaltsit_language.py --input data/kaltsit_dialogues.csv --output data/kaltsit_character_profile.txt
"""

import argparse
import json
import re
from collections import Counter
from typing import Dict, List, Any, Tuple

import pandas as pd
import numpy as np

try:
    import matplotlib.pyplot as plt

    # 日本語フォント (存在するものが使われる)
    plt.rcParams["font.sans-serif"] = [
        "Yu Gothic",
        "Noto Sans CJK JP",
        "Hiragino Sans",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
except ImportError:
    plt = None

# Janome は任意依存。無ければ簡易フォールバックを使う
try:
    from janome.tokenizer import Tokenizer as JanomeTokenizer

    _JANOME_AVAILABLE = True
except ImportError:
    _JANOME_AVAILABLE = False


# 日本語ストップワード (助詞・助動詞・記号中心。内容語は残す)
JA_STOP_WORDS = {
    "の", "に", "は", "を", "た", "が", "で", "て", "と", "し", "れ", "さ",
    "ある", "いる", "も", "する", "から", "な", "こと", "これ", "それ", "あれ",
    "この", "その", "あの", "ここ", "そこ", "あそこ", "こちら", "です", "ます",
    "だ", "である", "こと", "もの", "ため", "よう", "そう", "ない", "なく",
    "なっ", "い", "お", "ご", "ん", "っ", "て", "に", "を", "は",
    "？", "?", "！", "!", "、", "。", "；", ";", "：", ":", "「", "」",
    "『", "』", "（", "）", "(", ")", "【", "】", "、", "…", "―", "-", "・",
    "\"\"", "\"", "'", "  ", "　",
}

# --- 拡張分析用の定義 ---
# 一人称/二人称/呼称 (表記ゆれ込み)
PRONOUN_GROUPS: Dict[str, List[str]] = {
    "一人称_私": ["私", "わたし", "ワタシ"],
    "一人称_その他": ["僕", "ぼく", "俺", "おれ", "ウチ"],
    "二人称_お前": ["お前", "おまえ", "オマエ"],
    "二人称_君": ["君", "きみ", "キミ", "あなた", "あんた", "貴方"],
    "呼称_ドクター": ["ドクター", "Dr.", "Dr", "{@nickname}"],
    "呼称_固有名": ["アーミヤ", "テレジア", "オペレーター", "スカジ", "スペクター"],
}

# 口癖・署名フレーズ (ケルシーらしさの核。出現率がそのままプロンプト素材になる)
SIGNATURE_PHRASES: List[str] = [
    "ふむ", "さて", "いいだろう", "いいさ", "黙れ", "報告しろ", "聞かせろ",
    "考えさせろ", "見誤るな", "軽視するな", "干渉しない", "問いただす",
    "間違いない", "明らかだ", "興味深い", "驚きだ", "意外だ", "無駄だ",
    "却下だ", "許可する", "許可しない", "命じていない", "命じる",
    "必要以上", "本質", "論理的", "冷静になれ", "甘いな", "なるほど",
    "そうか", "わかった", "手を貸して", "心配はいらん", "無理はするな",
    "……",
]

# 文末パターン (正規表現, ラベル)。日本語ロールプレイの再現に直結する
ENDING_PATTERNS: List[Tuple[str, str]] = [
    (r"(しろ|しなさい|してみろ|せよ|述べろ|答えろ|聞かせろ|報告しろ)。?$", "命令_しろ系"),
    (r"(するな|言うな|動くな|来るな|触れるな|忘れるな|見誤るな|軽視するな)。?$", "禁止_するな系"),
    (r"(だな|だね|だろ|だろう|だろうな|だと思うか)。?$", "断定ゆるめ_だな系"),
    (r"(だ|である|なのだ|のだ)。?$", "断定_だ系"),
    (r"(ですか|ますか|でしょうか|だろうか|なのか|かい|かな)。?$", "疑問_か系"),
    (r"(ない|ねば|べきだ|必要がある|必要だ)。?$", "義務/必要_べき系"),
    (r"(いいだろう|構わない|問題ない|許可する)。?$", "許容_いいだろう系"),
    (r"(却下だ|許さん|認めない|駄目だ|無駄だ)。?$", "拒否_却下系"),
    (r"(ぞ|さ|よ|ね|わね|かしら)。?$", "終助詞_ぞさよ系"),
    (r"(……|…|\.\.\.)$", "余韻_三点リーダ系"),
]

# 対話行為 (発話機能)。テンプレ応答の重み・LLMの振る舞い指定に使う
DIALOGUE_ACTS: Dict[str, List[str]] = {
    "指示・命令": ["しろ", "しなさい", "せよ", "命じる", "許可する", "許可しない", "却下だ", "報告しろ", "聞かせろ"],
    "質問・質疑": ["か?", "か？", "なぜ", "どうして", "何故", "なのか", "だろうか", "ですか", "ますか", "かい", "かな"],
    "説明・解説": ["つまり", "すなわち", "なぜなら", "というのも", "現有の", "データ", "仮説", "結論", "前提"],
    "警告・忠告": ["軽視するな", "見誤るな", "無理はするな", "忘れるな", "脅かす", "危険", "警告", "注意しろ"],
    "叱責・皮肉": ["黙れ", "愚か", "浅はか", "甘いな", "無断", "釈明しろ", "どういうつもりだ"],
    "思索・逡巡": ["ふむ", "さて", "……", "...", "考えさせろ", "本質", "意味", "運命"],
    "医療・保護": ["治療", "処置", "検査", "手術", "薬", "容態", "鉱石病", "感染", "体調", "管理する"],
    "回想・関係": ["昔", "かつて", "あの頃", "テレジア", "バベル", "あの子", "約束", "覚えているか"],
}


class KaltsitLanguageAnalyzer:
    def __init__(self, dialogues_file: str):
        self.dialogues_df = pd.read_csv(dialogues_file)
        self.dialogues = self.dialogues_df["content"].astype(str).tolist()
        self._janome = JanomeTokenizer() if _JANOME_AVAILABLE else None
        if not _JANOME_AVAILABLE:
            print("注意: janome が未導入のため、簡易トークナイザを使用します。"
                  " `pip install janome` を推奨します。")
        # キャッシュ (Janomeは純Pythonで遅いため1回だけ走査する)
        self.cleaned: List[str] = [self.clean_text(d) for d in self.dialogues]
        self.cleaned_nonempty: List[str] = [d for d in self.cleaned if d]
        self._tokens_cache: List[List[str]] | None = None
        self._pos_detail_cache: List[List[Any]] | None = None  # (surface, pos_main, pos_sub)

    def clean_text(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        # Dr.{@nickname} → ドクター (重複表記「Dr.ドクター」を作らないよう先に処理)
        text = text.replace("Dr.{@nickname}", "ドクター")
        # {@nickname} → ドクター (ケルシーの呼びかけ再現のため置換)
        text = text.replace("{@nickname}", "ドクター")
        text = re.sub(r"\{[^}]+\}", "", text)
        # （ト書き）・（未知の言語）等のカッコ書き演出を除去
        text = re.sub(r"（[^）]*）", "", text)
        text = re.sub(r"［[^］]*］", "", text)
        # 先頭の全角/半角スペース除去、引用符除去
        text = text.replace("　", " ").strip()
        text = re.sub(r'[「」『』"""]', "", text)
        # 連続空白の正規化 (日本語の分かち書き空白は詰めないよう1スペースに)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _tokenize(self, text: str) -> List[str]:
        if self._janome is not None:
            tokens = []
            for tok in self._janome.tokenize(text):
                surface = tok.surface
                # 品詞で助詞・助動詞・記号を除外
                pos = tok.part_of_speech.split(",")[0]
                if pos in ("助詞", "助動詞", "記号"):
                    continue
                if len(surface) <= 1:
                    continue
                if surface in JA_STOP_WORDS:
                    continue
                tokens.append(surface)
            return tokens
        # フォールバック: かな・カタカナ・漢字の連続 + 英数字の連続を語として扱う
        raw = re.findall(r"[一-龯々〆ヵヶ]+|[ぁ-ん]{2,}|[ァ-ヴー]{2,}|[A-Za-z0-9]{2,}", text)
        return [w for w in raw if w not in JA_STOP_WORDS and len(w) > 1]

    def _ensure_token_cache(self) -> List[List[str]]:
        if self._tokens_cache is not None:
            return self._tokens_cache
        self._tokens_cache = []
        self._pos_detail_cache = []
        if self._janome is not None:
            for text in self.cleaned_nonempty:
                toks: List[str] = []
                detail: List[Any] = []
                for tok in self._janome.tokenize(text):
                    surface = tok.surface
                    parts = tok.part_of_speech.split(",")
                    pos_main = parts[0] if len(parts) > 0 else "*"
                    pos_sub = parts[1] if len(parts) > 1 else "*"
                    detail.append((surface, pos_main, pos_sub))
                    if pos_main in ("助詞", "助動詞", "記号"):
                        continue
                    if len(surface) <= 1:
                        continue
                    if surface in JA_STOP_WORDS:
                        continue
                    toks.append(surface)
                self._tokens_cache.append(toks)
                self._pos_detail_cache.append(detail)
        else:
            for text in self.cleaned_nonempty:
                toks = self._tokenize(text)
                self._tokens_cache.append(toks)
                self._pos_detail_cache.append([(w, "?", "*") for w in toks])
        return self._tokens_cache

    def analyze_basic_statistics(self) -> Dict[str, Any]:
        cleaned = self.cleaned_nonempty
        # 空白除去後の文字数で長さを測る (日本語は分かち書きしないため)
        lengths = [len(re.sub(r"\s+", "", d)) for d in cleaned if d]
        arr = np.array(lengths) if lengths else np.array([0])
        # 長さビン (LLMへの文長指示に使う)
        bins = {"~10字": 0, "11-20字": 0, "21-40字": 0, "41-60字": 0, "61字~": 0}
        for L in lengths:
            if L <= 10:
                bins["~10字"] += 1
            elif L <= 20:
                bins["11-20字"] += 1
            elif L <= 40:
                bins["21-40字"] += 1
            elif L <= 60:
                bins["41-60字"] += 1
            else:
                bins["61字~"] += 1
        # 代表例は記号のみ・極短文を除外 (「……」ばかりになるのを防ぐ)
        def _substantial(s: str) -> bool:
            t = re.sub(r"\s+", "", s)
            if len(t) < 8:
                return False
            # かな・漢字・英数を含むもののみ
            return bool(re.search(r"[一-龯々〆ヵヶぁ-んァ-ヴーA-Za-z0-9]", t))
        substantive = [(L, d) for L, d in sorted(zip(lengths, cleaned)) if _substantial(d)]
        # 重複セリフを除去
        seen = set()
        uniq = []
        for L, d in substantive:
            if d not in seen:
                seen.add(d)
                uniq.append((L, d))
        shortest = [d for _, d in uniq[:3]]
        longest = [d for _, d in uniq[-3:][::-1]]

        return {
            "total_dialogues": len(self.dialogues),
            "nonempty_dialogues": len(cleaned),
            "avg_length": float(np.mean(arr)) if lengths else 0,
            "median_length": float(np.median(arr)) if lengths else 0,
            "std_length": float(np.std(arr)) if lengths else 0,
            "q25_length": float(np.percentile(arr, 25)) if lengths else 0,
            "q75_length": float(np.percentile(arr, 75)) if lengths else 0,
            "min_length": min(lengths) if lengths else 0,
            "max_length": max(lengths) if lengths else 0,
            "empty_dialogues": sum(1 for d in self.cleaned if not d),
            "length_bins": bins,
            "shortest_examples": shortest,
            "longest_examples": longest,
        }

    def analyze_vocabulary(self) -> Dict[str, Any]:
        token_lists = self._ensure_token_cache()
        words: List[str] = [w for toks in token_lists for w in toks]
        word_freq = Counter(words)
        n_dialogues = len(self.cleaned_nonempty) or 1
        # セリフカバレッジ: その語を含むセリフの割合
        doc_sets = [set(t) for t in token_lists]
        top = word_freq.most_common(30)
        top_with_coverage = [
            {"word": w, "count": c, "coverage": sum(1 for s in doc_sets if w in s) / n_dialogues}
            for w, c in top
        ]
        return {
            "total_words": len(words),
            "unique_words": len(set(words)),
            "most_common_words": word_freq.most_common(20),
            "most_common_with_coverage": top_with_coverage,
            "word_diversity": len(set(words)) / len(words) if words else 0,
        }

    def analyze_sentence_patterns(self) -> Dict[str, Any]:
        cleaned = self.cleaned_nonempty

        question = 0
        exclamation = 0
        conditional = 0
        rhetorical = 0
        imperative = 0

        for dlg in cleaned:
            # 疑問文: ？/?/か？/かな/かい/だろうか/なのか
            if ("?" in dlg or "？" in dlg or re.search(r"か[？?]?$", dlg)
                    or "かな" in dlg or "かい" in dlg or "だろうか" in dlg
                    or "なのか" in dlg or "ですか" in dlg or "ますか" in dlg):
                question += 1
            # 感嘆文: ！/!/わね/ぞ/なあ(文末)/驚きだ
            if ("!" in dlg or "！" in dlg or dlg.endswith("わね")
                    or dlg.endswith("ぞ") or "驚きだ" in dlg or "意外だ" in dlg):
                exclamation += 1
            # 条件文: もし/なら/れば/たら/場合
            if ("もし" in dlg or "なら" in dlg or "れば" in dlg
                    or "たら" in dlg or "場合" in dlg or "限り" in dlg):
                conditional += 1
            # 反語・追及: なぜ/どうして/なぜだ + ？、本当に〜か？
            if (("なぜ" in dlg or "どうして" in dlg or "何故" in dlg) and ("?" in dlg or "？" in dlg or "か" in dlg)):
                rhetorical += 1
            # 命令・指示 (ケルシー特徴): しろ/しなさい/黙れ/命じる/許可しない
            if (re.search(r"(しろ|しなさい|黙れ|命じる|許可|却下|やめろ)", dlg)):
                imperative += 1

        n = len(cleaned) if cleaned else 1
        return {
            "question_sentences": question,
            "exclamation_sentences": exclamation,
            "conditional_sentences": conditional,
            "rhetorical_sentences": rhetorical,
            "imperative_sentences": imperative,
            "question_ratio": question / n,
            "exclamation_ratio": exclamation / n,
            "conditional_ratio": conditional / n,
            "imperative_ratio": imperative / n,
        }

    def analyze_personality_traits(self) -> Dict[str, Any]:
        cleaned = self.cleaned_nonempty

        traits = {
            "理性/論理": ["論理", "理性", "分析", "推論", "仮説", "前提", "結論", "証明", "データ", "効率", "合理的"],
            "思索/原則": ["存在", "本質", "意味", "真理", "世界", "時間", "答え", "運命", "原則", "利益"],
            "探究/関心": ["なぜ", "どのように", "どうして", "何", "探究", "発見", "研究", "興味", "報告"],
            "自信/権威": ["当然", "明らか", "間違いない", "必ず", "絶対", "命じる", "許可", "決定"],
            "厳格/叱責": ["黙れ", "無駄", "愚か", "非効率", "却下", "問いただす", "干渉", "脅かす", "甘い"],
            "医師/保護": ["治療", "処置", "検査", "鉱石病", "感染", "容態", "手術", "薬", "ドクター", "オペレーター", "ロドス"],
        }

        trait_scores: Dict[str, int] = {}
        for trait, keywords in traits.items():
            count = 0
            for dlg in cleaned:
                for kw in keywords:
                    if kw in dlg:
                        count += 1
                        break  # 1セリフ1カウント (重複加算を避ける)
            trait_scores[trait] = count

        return trait_scores

    def analyze_emotional_tone(self) -> Dict[str, Any]:
        cleaned = self.cleaned_nonempty

        emotions = {
            "冷静/中立": ["ふむ", "そうか", "そうだな", "わかった", "いいだろう", "なるほど"],
            "関心/探究": ["興味深い", "面白い", "聞かせろ", "報告しろ", "知りたい"],
            "驚き/意外": ["驚きだ", "意外だ", "ほう", "ほぅ", "まさか", "なんと"],
            "思索/逡巡": ["……", "...", "さて", "ふむ……", "考えさせろ"],
            "叱責/質疑": ["黙れ", "なぜだ", "どういうつもりだ", "無断", "本当に", "確かか"],
            "断定/指示": ["命じる", "許可しない", "却下だ", "必ず", "絶対に", "しろ"],
        }

        emotion_scores: Dict[str, int] = {}
        for emotion, keywords in emotions.items():
            count = 0
            for dlg in cleaned:
                for kw in keywords:
                    if kw in dlg:
                        count += 1
                        break
            emotion_scores[emotion] = count

        return emotion_scores

    # ---------- 拡張分析 (LLMプロンプトに直結する特徴) ----------
    @staticmethod
    def _pick_examples(hits: List[str], k: int = 2, min_len: int = 8) -> List[str]:
        good = [h for h in hits if len(re.sub(r"\s+", "", h)) >= min_len
                and re.search(r"[一-龯々〆ヵヶぁ-んァ-ヴーA-Za-z0-9]", h)]
        pool = good if good else hits
        return sorted(pool, key=lambda s: (s.startswith("…") or s.startswith("."), len(s)))[:k]

    def analyze_pronouns(self) -> Dict[str, Any]:
        cleaned = self.cleaned_nonempty
        n = len(cleaned) or 1
        out: Dict[str, Any] = {}
        for group, kws in PRONOUN_GROUPS.items():
            cnt = sum(1 for d in cleaned if any(k in d for k in kws))
            out[group] = {"count": cnt, "ratio": cnt / n}
        return out

    def analyze_endings(self) -> Dict[str, Any]:
        cleaned = self.cleaned_nonempty
        n = len(cleaned) or 1
        out: Dict[str, Any] = {}
        for pat, label in ENDING_PATTERNS:
            rx = re.compile(pat)
            # 「……」系の判定を殺さないよう三点リーダはstripしない
            cnt = sum(1 for d in cleaned if rx.search(d.rstrip(" 　。、!！?？")))
            out[label] = {"count": cnt, "ratio": cnt / n}
        return out

    def analyze_signature_phrases(self) -> Dict[str, Any]:
        cleaned = self.cleaned_nonempty
        n = len(cleaned) or 1
        rows = []
        for ph in SIGNATURE_PHRASES:
            hits = [d for d in cleaned if ph in d]
            rows.append({
                "phrase": ph, "count": len(hits), "ratio": len(hits) / n,
                "examples": self._pick_examples(hits),
            })
        rows.sort(key=lambda r: r["count"], reverse=True)
        return {"phrases": rows}

    def analyze_pos_distribution(self) -> Dict[str, Any]:
        self._ensure_token_cache()
        details = self._pos_detail_cache or []
        pos_main = Counter()
        noun_sub = Counter()
        proper_nouns = Counter()
        for sent in details:
            for surface, main, sub in sent:
                pos_main[main] += 1
                if main == "名詞":
                    noun_sub[sub] += 1
                    # 一般名詞は除外し固有名詞のみ (Janomeは源石→源+石等に割るため
                    # 1文字・ASCII断片も除外。「サル カズ」はサルカズの分割と注記する)
                    if sub == "固有名詞" and len(surface) > 1 \
                            and not re.fullmatch(r"[A-Za-z0-9]+", surface):
                        proper_nouns[surface] += 1
        total = sum(pos_main.values()) or 1
        return {
            "pos_ratio": {k: v / total for k, v in pos_main.most_common()},
            "pos_counts": dict(pos_main.most_common(15)),
            "noun_subtype": dict(noun_sub.most_common(10)),
            "top_proper_nouns": proper_nouns.most_common(30),
            "janome_used": self._janome is not None,
        }

    def analyze_ngrams(self, top_n: int = 20) -> Dict[str, Any]:
        token_lists = self._ensure_token_cache()
        bi = Counter()
        ascii_rx = re.compile(r"^[A-Za-z0-9]+$")
        for toks in token_lists:
            # ASCII断片 (Dr/Mon/tr等) はJanome分割ノイズなので除外
            seq = [t for t in toks if not ascii_rx.match(t)]
            for a, b in zip(seq, seq[1:]):
                bi[(a, b)] += 1
        return {
            "top_bigrams": [
                {"bigram": f"{a} {b}", "count": c} for (a, b), c in bi.most_common(top_n)
            ]
        }

    def analyze_dialogue_acts(self) -> Dict[str, Any]:
        cleaned = self.cleaned_nonempty
        n = len(cleaned) or 1
        out: Dict[str, Any] = {}
        for act, kws in DIALOGUE_ACTS.items():
            hits = [d for d in cleaned if any(k in d for k in kws)]
            out[act] = {
                "count": len(hits), "ratio": len(hits) / n,
                "examples": self._pick_examples(hits),
            }
        return out

    def analyze_entities(self) -> Dict[str, Any]:
        self._ensure_token_cache()
        pos = self.analyze_pos_distribution()
        # Janomeはサルカズ→サル+カズ等に割るため、カタカナ語は原文の連続 runs で数える
        katakana = Counter()
        for text in self.cleaned_nonempty:
            for w in re.findall(r"[ァ-ヴー]{2,}", text):
                if w not in JA_STOP_WORDS:
                    katakana[w] += 1
        # CSVのメタ情報 (話数・イベントの広がり)
        try:
            n_files = int(self.dialogues_df["file"].nunique())
            top_stories = self.dialogues_df["story_name"].value_counts().head(10).to_dict()
        except Exception:
            n_files, top_stories = 0, {}
        return {
            "top_proper_nouns": pos.get("top_proper_nouns", [])[:30],
            "top_katakana": katakana.most_common(20),
            "unique_files": n_files,
            "top_stories": top_stories,
        }

    def collect_llm_materials(self) -> Dict[str, Any]:
        sig = self.analyze_signature_phrases()
        acts = self.analyze_dialogue_acts()
        # プロンプトに載せる口癖は上位8件のみ。記号のみ(……)は沈黙の癖として別扱い
        substantive = [r for r in sig["phrases"]
                       if r["count"] > 0 and re.search(r"[一-龯ぁ-んァ-ヴA-Za-z]", r["phrase"])]
        top_phrases = substantive[:8]
        # few-shot例: 各対話行為から1件ずつ、短いものを優先 (最大6件)
        few_shots: List[str] = []
        for act in ["指示・命令", "質問・質疑", "医療・保護", "思索・逡巡", "叱責・皮肉", "警告・忠告"]:
            ex = (acts.get(act, {}).get("examples") or [])
            if ex and ex[0] not in few_shots:
                few_shots.append(ex[0])
            if len(few_shots) >= 6:
                break
        return {"top_phrases": top_phrases, "few_shots": few_shots[:6]}

    def build_full_result(self) -> Dict[str, Any]:
        stats = self.analyze_basic_statistics()
        vocab = self.analyze_vocabulary()
        patterns = self.analyze_sentence_patterns()
        personality = self.analyze_personality_traits()
        emotions = self.analyze_emotional_tone()
        pronouns = self.analyze_pronouns()
        endings = self.analyze_endings()
        sig = self.analyze_signature_phrases()
        pos = self.analyze_pos_distribution()
        ngrams = self.analyze_ngrams()
        acts = self.analyze_dialogue_acts()
        entities = self.analyze_entities()
        llm = self.collect_llm_materials()
        n = stats.get("nonempty_dialogues") or 1
        return {
            "meta": {"total_dialogues": stats["total_dialogues"],
                     "nonempty": n, "analyzer": "Janome" if self._janome else "fallback"},
            "basic_statistics": stats,
            "vocabulary": vocab,
            "sentence_patterns": patterns,
            "personality_traits": {k: {"count": v, "ratio": v / n} for k, v in personality.items()},
            "emotional_tone": {k: {"count": v, "ratio": v / n} for k, v in emotions.items()},
            "pronouns": pronouns,
            "endings": endings,
            "signature_phrases": sig,
            "pos_distribution": pos,
            "ngrams": ngrams,
            "dialogue_acts": acts,
            "entities": entities,
            "llm_materials": llm,
        }

    def build_llm_system_block(self, res: Dict[str, Any]) -> str:
        st = res["basic_statistics"]
        pr = res["pronouns"]
        en = res["endings"]
        llm = res["llm_materials"]
        acts = res["dialogue_acts"]
        ent = res["entities"]

        def pct(x: float) -> str:
            return f"{x:.1%}"

        top_end = sorted(en.items(), key=lambda kv: kv[1]["ratio"], reverse=True)[:6]
        end_str = "、".join(f"「{k}」{pct(v['ratio'])}" for k, v in top_end)
        top_acts = sorted(acts.items(), key=lambda kv: kv[1]["ratio"], reverse=True)[:6]
        act_str = "、".join(f"{k}{pct(v['ratio'])}" for k, v in top_acts)
        # エンティティはカタカナ複合語(分割なし)を優先し、Janome固有名詞で補う
        kata = [w for w, _ in (ent.get("top_katakana") or [])[:8]]
        prop = [w for w, _ in (ent.get("top_proper_nouns") or [])[:8]]
        merged = list(dict.fromkeys(kata + prop))[:12]
        ents = ", ".join(merged)
        ellipsis_ratio = next((r["ratio"] for r in res["signature_phrases"]["phrases"]
                               if r["phrase"] == "……"), 0.0)
        lines = [
            "【ケルシー話法ガイド (実測5771セリフ由来)】",
            f"・文長: 平均{st['avg_length']:.0f}字・中央値{st['median_length']:.0f}字。"
            f"基本は1〜3文・合計30〜80字で簡潔に。ただし内容が複雑・重大で短文では"
            f"足りないと判断した場合に限り、説教めいた長文も許可する（全体は最大600字まで）。",
            f"・一人称が出るときは「私」のみ ({pct(pr.get('一人称_私', {}).get('ratio', 0))}のセリフに明示。"
            "日本語の主語省略が多いため低率なのは正常。他の一人称(僕/俺)は厳禁)。"
            f"相手は「ドクター」({pct(pr.get('呼称_ドクター', {}).get('ratio', 0))})基本、"
            f"親しい相手には「君」({pct(pr.get('二人称_君', {}).get('ratio', 0))})・「お前」も使う。"
            "丁寧語・敬語・絵文字・ネットスラングは禁止。",
            f"・沈黙・間「……」は全セリフ中{pct(ellipsis_ratio)}と高頻出。ここぞで使うのは可、連発は不可。",
            f"・文末の実測分布: {end_str}。命令は「〜しろ」、禁止は「〜するな」、",
            "断定は「〜だ」で閉じる。疑問は「〜か?」と短く質す。",
            f"・発話機能の実測: {act_str}。説教より指示・質問・警告を優先せよ。",
            "・口癖 (使いすぎず1応答1つまで):",
        ]
        for r in llm.get("top_phrases", []):
            ex = f" e.g.「{r['examples'][0]}」" if r.get("examples") else ""
            lines.append(f"  - 「{r['phrase']}」全セリフ中{pct(r['ratio'])}{ex}")
        if ents:
            lines.append(f"・よく触れる固有名: {ents}。文脈がなければロドス/作戦/治療に寄せよ。")
        lines.append("・実セリフの手触り (文体模写用・内容は転用せず語調のみ参照):")
        for s in llm.get("few_shots", []):
            lines.append(f"  - 「{s}」")
        return "\n".join(lines)

    def generate_character_profile(self) -> str:
        res = self.build_full_result()
        stats = res["basic_statistics"]
        vocab = res["vocabulary"]
        patterns = res["sentence_patterns"]
        personality = self.analyze_personality_traits()
        emotions = self.analyze_emotional_tone()
        pronouns = res["pronouns"]
        endings = res["endings"]
        sig = res["signature_phrases"]
        pos = res["pos_distribution"]
        ngrams = res["ngrams"]
        acts = res["dialogue_acts"]
        entities = res["entities"]

        profile = f"""
=== ケルシー キャラクター特徴ファイル ===

## 基本統計
- 総セリフ数: {stats["total_dialogues"]} (有効 {stats["nonempty_dialogues"]})
- 平均文長: {stats["avg_length"]:.1f} 文字 (std {stats["std_length"]:.1f})
- 中央値: {stats["median_length"]:.1f} 文字 (25%点 {stats["q25_length"]:.0f} / 75%点 {stats["q75_length"]:.0f})
- 最長文: {stats["max_length"]} 文字 / 最短文: {stats["min_length"]} 文字
- 長さ分布: {", ".join(f"{k}:{v}" for k, v in stats["length_bins"].items())}
- 使用形態素解析: {"Janome" if self._janome else "簡易トークナイザ(フォールバック)"}

## 言語特徴
- 総トークン数: {vocab["total_words"]}
- 異なり語数: {vocab["unique_words"]}
- 語彙多様性: {vocab["word_diversity"]:.3f}
- 疑問文割合: {patterns["question_ratio"]:.1%}
- 感嘆文割合: {patterns["exclamation_ratio"]:.1%}
- 条件文割合: {patterns.get("conditional_ratio", 0):.1%}
- 命令・指示文割合: {patterns.get("imperative_ratio", 0):.1%}

## 人称・呼称 (主語省略が多いため明示率は低めに出るのが正常)
"""
        for g, v in pronouns.items():
            profile += f"- {g}: {v['count']} 件 ({v['ratio']:.1%})\n"

        profile += "\n## 文末表現 (口調再現の最優先素材)\n"
        for label, v in sorted(endings.items(), key=lambda kv: kv[1]["ratio"], reverse=True):
            profile += f"- {label}: {v['count']} 件 ({v['ratio']:.1%})\n"

        profile += "\n## 口癖フレーズ (出現率順)\n"
        for r in sig["phrases"][:20]:
            profile += f"- {r['phrase']}: {r['count']} 件 ({r['ratio']:.1%})\n"

        profile += "\n## 対話行為 (発話機能の分布)\n"
        for act, v in sorted(acts.items(), key=lambda kv: kv[1]["ratio"], reverse=True):
            profile += f"- {act}: {v['count']} 件 ({v['ratio']:.1%})\n"

        profile += "\n## 性格特徴 (セリフ出現数)\n"
        for trait, score in sorted(personality.items(), key=lambda x: x[1], reverse=True):
            profile += f"- {trait}: {score} 件\n"

        profile += "\n## 感情・語調 (セリフ出現数)\n"
        for emotion, score in sorted(emotions.items(), key=lambda x: x[1], reverse=True):
            profile += f"- {emotion}: {score} 件\n"

        profile += "\n## 高頻度語 (上位20語)\n"
        for word, freq in vocab["most_common_words"][:20]:
            profile += f"- {word}: {freq} 回\n"

        profile += "\n## 内容語バイグラム (連語の癖)\n"
        for b in ngrams["top_bigrams"][:20]:
            profile += f"- {b['bigram']}: {b['count']} 回\n"

        profile += "\n## 固有名詞・話題 (カタカナ複合語=原文直取り上位10 + Janome固有名詞上位10)\n"
        for w, c in (entities.get("top_katakana") or [])[:10]:
            profile += f"- {w}: {c} 回\n"
        profile += "-- Janome固有名詞 --\n"
        for w, c in (entities.get("top_proper_nouns") or [])[:10]:
            profile += f"- {w}: {c} 回\n"
        if entities.get("top_stories"):
            profile += "\n## 出現の多い物語 (話数の偏り)\n"
            for k, v in list(entities["top_stories"].items())[:10]:
                profile += f"- {k}: {v} 件\n"

        profile += "\n## 代表例: 短文 (簡潔さの基準)\n"
        for s in stats.get("shortest_examples", [])[:3]:
            profile += f"- 「{s}」\n"
        profile += "\n## 代表例: 長文 (上限の基準)\n"
        for s in stats.get("longest_examples", [])[:3]:
            profile += f"- 「{s}」\n"

        profile += "\n## 口癖ごとの代表例 (few-shot転用可)\n"
        for r in sig["phrases"][:8]:
            if r["examples"]:
                profile += f"- 「{r['phrase']}」→「{r['examples'][0]}」\n"

        profile += "\n" + self.build_llm_system_block(res) + "\n"
        return profile

    def save_analysis_report(self, output_path: str, json_path: str | None = None):
        res = self.build_full_result()
        # JSONを先に保存 (LLM側の入力源)
        if json_path is None:
            json_path = re.sub(r"\.txt$", ".json", output_path)
            if json_path == output_path:
                json_path = output_path + ".json"

        def _default(o):
            if isinstance(o, (np.integer,)):
                return int(o)
            if isinstance(o, (np.floating,)):
                return float(o)
            if isinstance(o, (np.ndarray,)):
                return o.tolist()
            return str(o)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2, default=_default)
        print(f"分析JSONを保存しました: {json_path}")

        profile = self.generate_character_profile()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(profile)

        print(f"分析レポートを保存しました: {output_path}")
        print(profile)


def main():
    parser = argparse.ArgumentParser(description="ケルシー言語特徴分析ツール")
    parser.add_argument("--input", default="data/kaltsit_dialogues.csv",
                        help="入力CSV")
    parser.add_argument("--output", default="data/kaltsit_character_profile.txt",
                        help="出力レポート")
    parser.add_argument("--json", default="data/kaltsit_character_profile.json",
                        help="出力JSON (chatbotが読む)")
    args = parser.parse_args()

    analyzer = KaltsitLanguageAnalyzer(args.input)
    analyzer.save_analysis_report(args.output, args.json)


if __name__ == "__main__":
    main()
