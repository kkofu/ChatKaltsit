#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import random
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

# .env 読み込み
load_dotenv()

# 日本語形態素解析 (任意依存、無ければフォールバック)
try:
    from janome.tokenizer import Tokenizer as JanomeTokenizer

    _JANOME_AVAILABLE = True
except ImportError:
    _JANOME_AVAILABLE = False


DEFAULT_GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or "").strip() or "gemini-3.8-flash"

DEFAULT_GEMINI_FALLBACKS = (
    os.getenv("GEMINI_FALLBACK_MODELS") or "gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash"
)

DEFAULT_OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL"
) or "nvidia/nemotron-3-super-120b-a12b:free"

DEFAULT_OPENROUTER_FALLBACKS = (
    os.getenv("OPENROUTER_FALLBACK_MODELS")
    or "z-ai/glm-5.2:free,,nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free,google/gemma-4-26b-a4b-it:free"
)

JA_STOP_WORDS = {
    "の", "に", "は", "を", "た", "が", "で", "て", "と", "し", "れ", "さ",
    "ある", "いる", "も", "する", "から", "な", "こと", "これ", "それ",
    "この", "その", "ここ", "です", "ます", "だ", "ない", "なく",
    "ため", "よう", "そう", "って", "って", "ね", "よ", "わ", "か", "の",
}


def _strip_thinking(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # 閉じタグなしで思考が漏れている場合、タグ以降を切り捨て
    text = re.split(r"<think>", text, flags=re.IGNORECASE)[0]
    text = re.split(r"<thinking>", text, flags=re.IGNORECASE)[0]
    return text.strip()


_THINKING_PREFIXES = (
    "we need to", "i need to", "let me think", "let me consider",
    "the user wants", "i should respond", "as an ai", "okay,",
    "first, i", "thinking:",
)

_JA_RX = re.compile(r"[一-龯々〆ヵヶぁ-んァ-ヴー]")


def _looks_like_thinking(text: str) -> bool:
    head = text[:200].lower()
    if head.startswith(_THINKING_PREFIXES):
        return True
    # 日本語を1文字も含まない応答はケルシー応答として不正
    return not _JA_RX.search(text)


@dataclass
class CharacterProfile:
    name: str = "ケルシー"
    personality_traits: Dict[str, float] = None
    language_patterns: Dict[str, float] = None
    vocabulary_style: Dict[str, float] = None
    emotional_tone: Dict[str, float] = None
    # --- 分析JSONから注入される実測素材 ---
    style_guide: Dict[str, Any] = None        # 文末分布・人称・文長など
    signature_phrases: List[Dict[str, Any]] = None  # 口癖 [{phrase, ratio, examples}]
    few_shots: List[str] = None               # 文体模写用の実セリフ (内容転用禁止)
    dialogue_acts: Dict[str, float] = None    # 対話行為の比率
    source_meta: Dict[str, Any] = None        # 総セリフ数・解析器など

    def __post_init__(self):
        if self.personality_traits is None:
            self.personality_traits = {
                "医師/保護": 0.9,
                "思索/原則": 0.7,
                "探究/関心": 0.6,
                "理性/論理": 0.8,
                "自信/権威": 0.6,
                "厳格/叱責": 0.5,
            }

        if self.language_patterns is None:
            self.language_patterns = {
                "疑問文割合": 0.134,
                "感嘆文割合": 0.021,
                "条件文割合": 0.151,
                "命令・指示文割合": 0.008,
                "平均文長": 34.2,
                "語彙多様性": 0.183,
            }

        if self.vocabulary_style is None:
            self.vocabulary_style = {
                "formal度": 0.8,
                "抽象概念": 0.7,
                "医療・専門用語": 0.8,
                "軍事・指揮用語": 0.7,
            }

        if self.emotional_tone is None:
            self.emotional_tone = {
                "冷静中立": 0.7,
                "思索逡巡": 0.5,
                "断定指示": 0.4,
                "叱責質疑": 0.3,
            }
        if self.style_guide is None:
            self.style_guide = {}
        if self.signature_phrases is None:
            self.signature_phrases = []
        if self.few_shots is None:
            self.few_shots = []
        if self.dialogue_acts is None:
            self.dialogue_acts = {}
        if self.source_meta is None:
            self.source_meta = {}

    @classmethod
    def from_analysis_json(cls, path: str) -> "CharacterProfile":
        try:
            with open(path, encoding="utf-8") as f:
                res = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return cls()
        p = cls()
        try:
            traits = res.get("personality_traits", {})
            if traits:
                # count -> ratio が入っているのでそのまま重みに使う
                p.personality_traits = {k: float(v.get("ratio", 0)) for k, v in traits.items()}
            emos = res.get("emotional_tone", {})
            if emos:
                p.emotional_tone = {k: float(v.get("ratio", 0)) for k, v in emos.items()}
            pat = res.get("sentence_patterns", {})
            st = res.get("basic_statistics", {})
            p.language_patterns = {
                "疑問文割合": float(pat.get("question_ratio", 0)),
                "感嘆文割合": float(pat.get("exclamation_ratio", 0)),
                "条件文割合": float(pat.get("conditional_ratio", 0)),
                "命令・指示文割合": float(pat.get("imperative_ratio", 0)),
                "平均文長": float(st.get("avg_length", 34.2)),
                "中央値文長": float(st.get("median_length", 30.0)),
                "語彙多様性": float(res.get("vocabulary", {}).get("word_diversity", 0.18)),
            }
            p.style_guide = {
                "endings": {k: float(v.get("ratio", 0)) for k, v in res.get("endings", {}).items()},
                "pronouns": {k: float(v.get("ratio", 0)) for k, v in res.get("pronouns", {}).items()},
                "length_bins": st.get("length_bins", {}),
                "top_bigrams": [b.get("bigram", "") for b in res.get("ngrams", {}).get("top_bigrams", [])[:10]],
                # カタカナ複合語を優先、Janome固有名詞で補完
                "top_entities": list(dict.fromkeys(
                    [w for w, _ in (res.get("entities", {}).get("top_katakana") or [])[:8]]
                    + [w for w, _ in (res.get("entities", {}).get("top_proper_nouns") or [])[:8]]
                ))[:12],
            }
            llm = res.get("llm_materials", {})
            p.signature_phrases = llm.get("top_phrases", [])[:8]
            p.few_shots = llm.get("few_shots", [])[:6]
            p.dialogue_acts = {k: float(v.get("ratio", 0)) for k, v in res.get("dialogue_acts", {}).items()}
            p.source_meta = res.get("meta", {})
        except Exception as e:
            print(f"分析JSONの読込に一部失敗 (既定値で継続): {e}")
        return p


class KaltsitDialogueSystem:
    def __init__(self, dialogues_file: str, profile_json: str = "data/kaltsit_character_profile.json"):
        # 分析JSONがあれば実測値を優先、無ければハードコード既定値
        if profile_json and os.path.exists(profile_json):
            self.character_profile = CharacterProfile.from_analysis_json(profile_json)
        else:
            self.character_profile = CharacterProfile()
        self.dialogues_df = self._load_dialogues(dialogues_file)
        self.response_templates = self._build_response_templates()
        self.api_config = self._load_api_config()
        self._janome = JanomeTokenizer() if _JANOME_AVAILABLE else None
        self._retrieval_index = self._build_retrieval_index()
        self.last_provider = "none"
        self.last_elapsed_ms = 0
        self.last_error: Optional[str] = None
        # 会話履歴 (要約APIを叩かず生で保持、RPD節約のため上限10件のFIFO)
        self.history: List[Dict[str, str]] = []
        self.max_history_messages = 10
        # 試行順 (/debug order で変更可、templateは常に最終フォールバック)
        self.provider_order_names = ["gemini", "openrouter", "openai"]

    def _record_error(self, msg: str):
        import time as _t

        self.last_error = f"[{_t.strftime('%H:%M:%S')}] {msg}"
        print(self.last_error)

    def _record_history(self, user_input: str, reply: str):
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": reply})
        while len(self.history) > self.max_history_messages:
            self.history.pop(0)

    def clear_history(self):
        self.history = []

    def _history_for_chat(self) -> List[Dict[str, str]]:
        return [
            {"role": h["role"], "content": h["content"]} for h in self.history
        ]

    def _history_for_gemini(self) -> List[Dict[str, Any]]:
        out = []
        for h in self.history:
            role = "model" if h["role"] == "assistant" else "user"
            out.append({"role": role, "parts": [{"text": h["content"]}]})
        return out

    def _describe_order(self) -> str:
        labels = []
        for key in self.provider_order_names:
            if key == "gemini":
                labels.append(
                    f"gemini:{self.api_config.get('gemini_model', '?')}"
                    if self.api_config.get("gemini_api_key")
                    else "gemini (no key, skipping)"
                )
            elif key == "openrouter":
                labels.append(
                    "openrouter"
                    if self.api_config.get("openrouter_api_key")
                    else "openrouter (no key, skipping)"
                )
            elif key == "openai":
                labels.append(
                    "openai"
                    if self.api_config.get("openai_api_key")
                    else "openai (no key, skipping)"
                )
            elif key == "template":
                labels.append("template")
        if "template" not in self.provider_order_names:
            labels.append("template (fallback)")
        return " -> ".join(labels) if labels else "(empty)"

    def get_debug_info(self) -> str:
        lines = [
            f"provider: {self.last_provider}",
            f"elapsed: {self.last_elapsed_ms}ms",
            f"history: {len(self.history)}/{self.max_history_messages}",
            f"order: {self._describe_order()}",
            f"gemini_model: {self.api_config.get('gemini_model', '?')}",
            f"gemini_fb: {','.join(self.api_config.get('gemini_fallback_models', [])) or 'なし'}",
            f"openrouter_model: {self.api_config.get('openrouter_model', '?')}",
            f"openrouter_fb: {','.join(self.api_config.get('openrouter_fallback_models', [])) or 'なし'}",
            f"openai_model: {self.api_config.get('openai_model', '?')}",
            "keys: " + ", ".join(
                f"{k}={'yes' if self.api_config.get(k) else 'no'}"
                for k in ("gemini_api_key", "openrouter_api_key", "openai_api_key")
            ),
            f"last_error: {self.last_error or 'no'}",
        ]
        return "\n".join(lines)

    _DEBUG_USAGE = (
        "使い方:\n"
        "  /debug … 情報表示\n"
        "  /debug order <gemini|openrouter|openai|template> ... 試行順を変更\n"
        "  /debug model <gemini|gemini-fb|openrouter|openrouter-fb|openai> <値> ... モデルを変更\n"
        "  /debug reset ... order・モデルを既定に戻す"
    )
    
    def handle_debug_command(self, text: str) -> str:
        parts = text.strip().split()
        if len(parts) == 1:
            return self.get_debug_info()
        sub = parts[1].lower()
    
        if sub == "order":
            names = [p.lower() for p in parts[2:]]
            valid = ("gemini", "openrouter", "openai", "template")
            bad = [n for n in names if n not in valid]
            if not names or bad:
                msg = "order の指定が不正です"
                if bad:
                    msg += f" (不明: {','.join(bad)})"
                return msg + f"。有効: {','.join(valid)}\n" + self._DEBUG_USAGE
            self.provider_order_names = names
            return "order更新: " + self._describe_order()
    
        if sub == "model":
            if len(parts) < 4:
                return "model の指定が不足です\n" + self._DEBUG_USAGE
            which, value = parts[2].lower(), parts[3].strip()
            if which == "gemini" and value:
                self.api_config["gemini_model"] = value
            elif which == "gemini-fb":
                self.api_config["gemini_fallback_models"] = [
                    m.strip() for m in value.split(",") if m.strip()
                ]
            elif which == "openrouter" and value:
                self.api_config["openrouter_model"] = value
            elif which == "openrouter-fb":
                self.api_config["openrouter_fallback_models"] = [
                    m.strip() for m in value.split(",") if m.strip()
                ]
            elif which == "openai" and value:
                self.api_config["openai_model"] = value
            else:
                return "model の指定が不正です\n" + self._DEBUG_USAGE
            return f"model更新: {which} = {value}\norder: " + self._describe_order()
    
        if sub == "reset":
            self.api_config["gemini_model"] = DEFAULT_GEMINI_MODEL
            self.api_config["gemini_fallback_models"] = [
                m.strip() for m in DEFAULT_GEMINI_FALLBACKS.split(",") if m.strip()
            ]
            self.api_config["openrouter_model"] = DEFAULT_OPENROUTER_MODEL
            self.api_config["openrouter_fallback_models"] = [
                m.strip() for m in DEFAULT_OPENROUTER_FALLBACKS.split(",") if m.strip()
            ]
            self.api_config["openai_model"] = (
                os.getenv("OPENAI_MODEL") or ""
            ).strip() or "gpt-4o-mini"
            self.provider_order_names = ["gemini", "openrouter", "openai"]
            return "reset完了:\n" + self.get_debug_info()
    
        return f"不明なサブコマンド: {sub}\n" + self._DEBUG_USAGE

    def _load_dialogues(self, file_path: str) -> Any:
        import pandas as pd

        return pd.read_csv(file_path)

    def _load_api_config(self) -> Dict[str, str]:
        return {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "openai_model": (os.getenv("OPENAI_MODEL") or "").strip() or "gpt-5.6-luna",
            "claude_api_key": os.getenv("CLAUDE_API_KEY", ""),
            "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
            "gemini_model": (os.getenv("GEMINI_MODEL") or "").strip()
            or DEFAULT_GEMINI_MODEL,
            "gemini_fallback_models": [
                m.strip()
                for m in DEFAULT_GEMINI_FALLBACKS.split(",")
                if m.strip()
            ],
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
            "openrouter_model": (os.getenv("OPENROUTER_MODEL") or "").strip()
            or DEFAULT_OPENROUTER_MODEL,
            # カンマ区切りで複数指定可、プライマリが失敗した際の予備
            "openrouter_fallback_models": [
                m.strip()
                for m in DEFAULT_OPENROUTER_FALLBACKS.split(",")
                if m.strip()
            ],
        }

    def _build_response_templates(self) -> Dict[str, List[str]]:
        return {
            "思索": [
                "ふむ……{topic}がどういったことを意味するか、考えてみる価値くらいはあるだろう。",
                "表層的な理解で満足するな。",
                "{topic}についてだ。君はどう理解している？　ドクター。",
                "この問題の核心は{topic}にある。見誤るな。",
            ],
            "探究": [
                "{topic}について報告してくれ。詳細を聞かせてもらおう。",
                "続けて。",
                "{topic}は調査に値する。見解を聞いてみよう。",
                "ドクター、{topic}について君はどう考えている？",
            ],
            "論理分析": [
                "論理的に考えれば、{topic}はこう解釈できるはずだ……",
                "現有の情報から判断するに、{topic}の結論は明らかだ。",
                "冷静になれ。この問題を感情で語るな。",
                "{topic}については、さらなるデータによる検証が必要だ。",
            ],
            "断定指示": [
                "{topic}については結論が出ている。議論の余地はない。",
                "これに際して言えば、間違いはない。{topic}はそういうことだ。",
                "私の判断は変わらない。{topic}についてはこの方針でいく。",
                "いいだろう。{topic}については私が許可する。",
            ],
            "叱責質疑": [
                "本当にその理解で確かか？　もう一度確認してみてくれ。",
                "なぜ{topic}がそうなると考える？　説明が必要だな。",
                "無断での行動は許されない。{topic}について納得できる理由で釈明してくれ。",
                "君の考えとは思えないな。{topic}をその程度の理解で済ませるつもりか？",
            ],
            "医師": [
                "ドクター、無理はするな。{topic}の前にまず体調を報告してくれ。",
                "病の威力を軽視するな。{topic}も治療計画に影響する。",
                "検査の時間だ。{topic}の話はその後にしよう。",
                "君の容態は私が管理する。{topic}について心配はいらない。",
            ],
        }

    def _extract_keywords(self, user_input: str) -> List[str]:
        if self._janome is not None:
            keywords = []
            for tok in self._janome.tokenize(user_input):
                surface = tok.surface
                pos_parts = tok.part_of_speech.split(",")
                pos_main, pos_sub = pos_parts[0], pos_parts[1] if len(pos_parts) > 1 else "*"
                # 内容語の名詞(一般・固有名詞)のみ残し代名詞・非自立・数詞は除外
                if pos_main != "名詞" or pos_sub not in ("一般", "固有名詞"):
                    continue
                if len(surface) <= 1 or surface in JA_STOP_WORDS:
                    continue
                keywords.append(surface)
            return keywords[:5]
        # フォールバック: 日本語文字連続・英数字連続を語とみなす
        words = re.findall(
            r"[一-龯々〆ヵヶ]+|[ぁ-ん]{2,}|[ァ-ヴー]{2,}|[A-Za-z0-9]{2,}",
            user_input,
        )
        keywords = [w for w in words if w not in JA_STOP_WORDS]
        return keywords[:5]

    @staticmethod
    def _retrieval_tokens(text: str) -> List[str]:
        text = text.replace("{@nickname}", "ドクター")
        text = re.sub(r"（[^）]*）", "", text)
        toks = re.findall(r"[一-龯々〆ヵヶ]+|[ぁ-ん]{2,}|[ァ-ヴー]{2,}|[A-Za-z0-9]{2,}", text)
        return [t for t in toks if t not in JA_STOP_WORDS and len(t) > 1]

    def _build_retrieval_index(self) -> List[Dict[str, Any]]:
        index: List[Dict[str, Any]] = []
        try:
            contents = self.dialogues_df["content"].astype(str).tolist()
        except Exception:
            return index
        for i, raw in enumerate(contents):
            clean = str(raw).replace("{@nickname}", "ドクター").strip()
            if len(clean) < 4 or len(clean) > 120:
                continue  # 短すぎ・長すぎはfew-shotに不向き
            if re.fullmatch(r"[（(].*[)）]", clean):
                continue  # ト書きのみを除外
            toks = set(self._retrieval_tokens(clean))
            if not toks:
                continue
            index.append({"text": clean, "tokens": toks})
            if len(index) >= 5000:
                break
        return index

    def _retrieve_similar_dialogues(self, user_input: str, top_k: int = 3) -> List[str]:
        if not self._retrieval_index:
            # インデックスが無ければ分析JSON由来のfew-shotにフォールバック
            return list(self.character_profile.few_shots or [])[:top_k]
        query = set(self._retrieval_tokens(user_input)) | set(self._extract_keywords(user_input))
        if not query:
            return list(self.character_profile.few_shots or [])[:top_k]
        scored = []
        for item in self._retrieval_index:
            overlap = len(query & item["tokens"])
            if overlap:
                # Jaccard的スコア + 短文を優遇 (プロンプトが膨れない)
                score = overlap / (len(query | item["tokens"]) + 1) - len(item["text"]) / 5000
                scored.append((score, item["text"]))
        scored.sort(reverse=True)
        out = [t for _, t in scored[:top_k]]
        # 1件もヒットしなければ汎用few-shotで補う
        if not out:
            out = list(self.character_profile.few_shots or [])[:top_k]
        # 重複除去
        seen, uniq = set(), []
        for t in out:
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        return uniq

    def _select_response_style(self, user_input: str) -> str:
        if "なぜ" in user_input or "どうして" in user_input or "なぜだ" in user_input:
            return "論理分析"
        elif "ですか" in user_input or "ますか" in user_input or user_input.rstrip().endswith(("か?", "か？", "かな", "かい")):
            return "叱責質疑"
        elif "思う" in user_input or "考える" in user_input:
            return "思索"
        elif "教えて" in user_input or "説明" in user_input or "報告" in user_input:
            return "探究"
        elif "体調" in user_input or "病気" in user_input or "治療" in user_input or "検査" in user_input:
            return "医師"
        elif "絶対" in user_input or "必ず" in user_input or "断定" in user_input:
            return "断定指示"
        else:
            styles = list(self.response_templates.keys())
            weights = [
                0.7,  # 思索
                0.6,  # 探究
                0.8,  # 論理分析
                0.6,  # 断定指示
                0.5,  # 叱責質疑
                0.9 if "ドクター" in user_input else 0.4,  # 医師
            ]
            return random.choices(styles, weights=weights)[0]

    def _generate_template_response(self, user_input: str) -> str:
        keywords = self._extract_keywords(user_input)
        style = self._select_response_style(user_input)

        templates = self.response_templates[style]
        template = random.choice(templates)

        if keywords and "{topic}" in template:
            topic = random.choice(keywords)
            response = template.format(topic=topic)
        else:
            response = template.replace("{topic}", "その件")

        return response

    def _call_openai_api(self, user_input: str) -> Optional[str]:
        if not self.api_config["openai_api_key"]:
            return None

        try:
            retrieved = self._retrieve_similar_dialogues(user_input, top_k=3)
            system_prompt = f"""
あなたはケルシー。アークナイツのロドスの医療責任者であり、ドクターの古くからの協力者だ。
{self._get_character_prompt(retrieved)}

ケルシーとして、日本語で、彼女の口調・語調を保ってユーザー(ドクター)の入力に応答せよ。
一人称は「私」。ドクターを「ドクター」または「君」と呼ぶ。冷静・厳格・簡潔に。
文体見本の丸写しは禁止。語調だけを参考にせよ。
"""
            headers = {
                "Authorization": f"Bearer {self.api_config['openai_api_key']}",
                "Content-Type": "application/json",
            }
            data = {
                    "model": (self.api_config.get("openai_model") or "gpt-5.6-luna"),
                "messages": (
                    [{"role": "system", "content": system_prompt}]
                    + self._history_for_chat()
                    + [{"role": "user", "content": user_input}]
                ),
                "max_tokens": 1000,
                "temperature": 0.7,
            }
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=15,
            )
            if response.status_code == 200:
                result = response.json()
                text = _strip_thinking(result["choices"][0]["message"]["content"].strip())
                if text and not _looks_like_thinking(text):
                    return text
                self._record_error(f"OpenAI 応答棄却 (空 or 思考漏れ): {text[:120]}")
        except Exception as e:
            self._record_error(f"OpenAI API呼び出し失敗: {e}")
        return None

    def _parse_openrouter_result(self, result: Any, raw_head: str) -> Optional[str]:
        if not isinstance(result, dict):
            self._record_error(f"OpenRouter 応答形式エラー: JSONオブジェクトではない ({raw_head})")
            return None
        if "error" in result:
            self._record_error(f"OpenRouter 応答内エラー: {result.get('error')} ({raw_head})")
            return None
        choices = result.get("choices")
        if not choices:
            self._record_error(
                f"OpenRouter 応答にchoicesなし: keys={list(result.keys())} ({raw_head})"
            )
            return None
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            self._record_error(f"OpenRouter 応答にmessageなし: {choices[0]} ({raw_head})")
            return None
        if message.get("error"):
            self._record_error(f"OpenRouter choice内エラー: {message.get('error')} ({raw_head})")
            return None

        content = (message.get("content") or "").strip()
        if message.get("reasoning"):
            # reasoning は思考過程でありユーザーに見せず記録のみ
            self._record_error(f"OpenRouter reasoning受信 (破棄): {str(message.get('reasoning'))[:120]}")
        content = _strip_thinking(content)
        if content and not _looks_like_thinking(content):
            return content
        # 空応答・思考漏れは失敗扱い -> 次モデル/テンプレートにフォールバック
        self._record_error(f"OpenRouter 応答棄却 (空 or 思考漏れ): {content[:120]} ({raw_head})")
        return None

    def _call_openrouter_api(self, user_input: str) -> Optional[str]:
        if not self.api_config["openrouter_api_key"]:
            return None

        retrieved = self._retrieve_similar_dialogues(user_input, top_k=3)
        system_prompt = f"""
あなたはケルシー。アークナイツのロドスの医療責任者であり、ドクターの古くからの協力者だ。
{self._get_character_prompt(retrieved)}

ケルシーとして、日本語で、彼女の口調・語調を保ってユーザー(ドクター)の入力に応答せよ。
一人称は「私」。ドクターを「ドクター」または「君」と呼ぶ。冷静・厳格・簡潔に。
回答は日本語のみ。基本は平均30〜40文字程度のセリフを1〜3文で簡潔に。
ただし内容が複雑・重大で短文では説明しきれないと判断した場合に限り、この制限を外して長文で答えてよい。説教めいた長文も許可するが、全体は最大600字までとする。
文体見本の丸写しは禁止。語調だけを参考にせよ。
思考過程・推論の途中経過は一切出力するな。最終回答の日本語セリフのみを出力せよ。
"""

        headers = {
            "Authorization": f"Bearer {self.api_config['openrouter_api_key']}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8080",
            "X-Title": "KaltsitAIAssistant",
        }
        primary = (self.api_config.get("openrouter_model") or "").strip() or DEFAULT_OPENROUTER_MODEL
        models = [m for m in [primary] + [
            m for m in self.api_config.get("openrouter_fallback_models", []) if m != primary
        ] if (m or "").strip()]
        if not models:
            print("OpenRouter 設定エラー: 使用可能なモデルがありません。"
                  " OPENROUTER_MODEL / OPENROUTER_FALLBACK_MODELS を確認してください。")
            return None

        for model in models:
            try:
                data = {
                    "model": (self.api_config.get("openai_model") or "gpt-5.6-luna"),
                    "messages": (
                        [{"role": "system", "content": system_prompt}]
                        + self._history_for_chat()
                        + [{"role": "user", "content": user_input}]
                    ),
                    # reasoning(思考過程)を応答に含めずcontentのみ受け取る
                    "reasoning": {"exclude": True},
                    "max_tokens": 1000,
                    "temperature": 0.7,
                }
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=20,
                )
                if response.status_code != 200:
                    self._record_error(
                        f"OpenRouter APIエラー [{model}]: "
                        f"{response.status_code} - {response.text[:500]}"
                    )
                    continue
                try:
                    result = response.json()
                except Exception as e:
                    self._record_error(f"OpenRouter JSON解析失敗 [{model}]: {e} ({response.text[:300]})")
                    continue
                parsed = self._parse_openrouter_result(result, response.text[:300])
                if parsed:
                    return parsed
                # パース失敗時は次のモデルを試す
            except Exception as e:
                self._record_error(f"OpenRouter API呼び出し失敗 [{model}]: {e!r}")

        return None

    def _call_gemini_api(self, user_input: str) -> Optional[str]:
        if not self.api_config["gemini_api_key"]:
            return None

        try:
            retrieved = self._retrieve_similar_dialogues(user_input, top_k=3)
            system_prompt = (
                f"あなたはケルシー。以下の特徴を保って日本語で応答せよ:"
                f"{self._get_character_prompt(retrieved)}"
            )
            headers = {"Content-Type": "application/json"}
            data = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": self._history_for_gemini()
                + [{"role": "user", "parts": [{"text": user_input}]}],
            }
            primary = (self.api_config.get("gemini_model") or "").strip() or DEFAULT_GEMINI_MODEL
            models = [m for m in [primary] + [
                m for m in self.api_config.get("gemini_fallback_models", []) if m != primary
            ] if (m or "").strip()]
            if not models:
                print("Gemini 設定エラー: 使用可能なモデルがありません。")
                return None

            for model in models:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model}:generateContent?key={self.api_config['gemini_api_key']}"
                )
                response = None
                for attempt in range(2):
                    response = requests.post(url, headers=headers, json=data, timeout=20)
                    if response.status_code != 429 or attempt == 1:
                        break
                    # 無料枠のRPM制限に当たった場合のみ1回だけ待って再試行
                    self._record_error(f"Gemini 429 [{model}]: 5秒後に再試行します")
                    import time as _t

                    _t.sleep(5)
                if response.status_code != 200:
                    self._record_error(
                        f"Gemini APIエラー [{model}]: "
                        f"{response.status_code} - {response.text[:300]}"
                    )
                    continue  # 次モデルへ
                result = response.json()
                if not result.get("candidates"):
                    # セーフティブロック等 (promptFeedback に理由あり)
                    self._record_error(f"Gemini candidates空 [{model}]: {str(result)[:300]}")
                    continue
                # thoughtパート(思考過程)は除外し、本文テキストのみ連結
                parts = result["candidates"][0]["content"].get("parts", [])
                body = "".join(
                    p.get("text", "") for p in parts if not p.get("thought", False)
                ).strip()
                text = _strip_thinking(body)
                if text and not _looks_like_thinking(text):
                    return text
                self._record_error(f"Gemini 応答棄却 [{model}] (空 or 思考漏れ): {text[:120]}")
        except Exception as e:
            self._record_error(f"Gemini API呼び出し失敗: {e!r}")
        return None

    def _get_character_prompt(self, retrieved: Optional[List[str]] = None) -> str:
        cp = self.character_profile
        lp = cp.language_patterns or {}
        sg = cp.style_guide or {}
        endings = sg.get("endings", {})
        pronouns = sg.get("pronouns", {})
        acts = cp.dialogue_acts or {}

        def top_str(d: Dict[str, float], n: int = 5) -> str:
            items = sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:n]
            return "、".join(f"{k}{v:.0%}" for k, v in items) if items else "—"

        sig_lines = []
        for r in (cp.signature_phrases or [])[:8]:
            ph = r.get("phrase", "")
            ratio = float(r.get("ratio", 0))
            ex = (r.get("examples") or [""])[0]
            tail = f" (例:「{ex}」)" if ex else ""
            sig_lines.append(f"- 「{ph}」全セリフ中{ratio:.1%}{tail}")
        sig_block = "\n".join(sig_lines) if sig_lines else "- 「ああ、」「む……」「ふむ……」「さて」「いいだろう」「黙れ」"

        shots = retrieved if retrieved else (cp.few_shots or [])
        shot_block = "\n".join(f"- 「{s}」" for s in shots[:3]) if shots else "—"
        bigrams = "、".join(f"「{b}」" for b in (sg.get("top_bigrams") or [])[:6])
        entities = "、".join(sg.get("top_entities") or []) or "ロドス、オペレーター、アーミヤ、鉱石病・感染者、治療、テレジア、作戦指揮"
        n_total = (cp.source_meta or {}).get("total_dialogues", 5771)

        return f"""
あなたはケルシー。アークナイツのロドスの医療責任者であり、ドクターの古くからの協力者だ。
分析対象セリフ総数: {n_total}件の実測プロファイルに厳密に従え。

[性格・発話機能の実測分布]
- 性格: {top_str(cp.personality_traits or {{}}, 6)}
- 発話機能: {top_str(acts, 6) if acts else "指示・質問・警告が中心"}
- 感情・語調: {top_str(cp.emotional_tone or {{}}, 4)}

[言語スタイルの実測]
- 疑問文 {lp.get("疑問文割合", 0.134):.1%} / 感嘆文 {lp.get("感嘆文割合", 0.021):.1%} / 条件文 {lp.get("条件文割合", 0.151):.1%} / 命令・指示 {lp.get("命令・指示文割合", 0.008):.1%}
- 平均文長 約{lp.get("平均文長", 34.2):.1f}文字・中央値 約{lp.get("中央値文長", lp.get("平均文長", 34.2)):.0f}文字。基本は1〜3文・合計30〜80字で簡潔に。ただし内容が複雑・重大で短文では足りないと判断した場合に限り、説教めいた長文も許可する（全体は最大600字まで）。
- 文末の実測: {top_str(endings, 6) if endings else "命令してくれ系・禁止するな系・断定だ系が中心"}
- 人称の実測: {top_str(pronouns, 5) if pronouns else "一人称は私、呼称はドクター"}
- 連語の癖: {bigrams if bigrams else "—"}
- よく扱う固有名: {entities}

[口癖 (1応答につき最大1つ。連発禁止)]
{sig_block}

[文体見本 (語調のみ模写し、内容・固有名の転用は禁止)]
{shot_block}

[絶対ルール]
- 一人称は「私」固定。「僕/俺/わたし」は使わない。相手は基本「ドクター」。実測では親しい相手への「君」「お前」もあり、ドクターへの呼びかけは文脈で選べ。
- 文末は「〜だ」「〜してくれ」「〜するな」「〜か?」で閉じる。丁寧語(です・ます)、絵文字、ネットスラング、口語は禁止。
- 医療者としてドクターの体調を気にかけるが、過度な優しさは見せない。冷静・厳格・簡潔に。
- 見本セリフの丸写し・固有名の無関係な持ち込みは禁止。あくまで語調の参考にせよ。
"""

    def generate_response(self, user_input: str, use_api: bool = True) -> str:
        import time as _time

        t_all = _time.time()
        self.last_provider = "none"
        self.last_elapsed_ms = 0

        def _done(provider: str, text: str, record: bool = True) -> str:
            self.last_provider = provider
            self.last_elapsed_ms = int((_time.time() - t_all) * 1000)
            if record:
                self._record_history(user_input, text)
            return text

        if not user_input.strip():
            return _done("fixed", "ドクター、君か。用件は何だ？　簡潔に報告してくれ。", record=False)

        # まずAPIを試す
        if use_api:
            handlers = {
                "gemini": (
                    lambda: f"gemini:{self.api_config.get('gemini_model', '?')}",
                    self._call_gemini_api,
                ),
                "openrouter": (lambda: "openrouter", self._call_openrouter_api),
                "openai": (lambda: "openai", self._call_openai_api),
                "template": (
                    lambda: "template",
                    lambda u: self._generate_template_response(u),
                ),
            }
            for key in self.provider_order_names:
                if key not in handlers:
                    continue
                label_fn, fn = handlers[key]
                api_response = fn(user_input)
                if api_response:
                    return _done(label_fn(), api_response)

        # APIが使えない場合はテンプレート応答
        return _done("template", self._generate_template_response(user_input))

    def get_conversation_examples(self) -> List[Dict[str, str]]:
        return [
            {
                "user": "この作戦についてどう思う？",
                "kaltsit": "戦術目標を見極めるんだ。ロドスの利益を損なわない限り、私は干渉しない。",
            },
            {
                "user": "体調が優れないんだ。",
                "kaltsit": "ドクター、無理はするな。君の容態は私が管理する。",
            },
            {
                "user": "なぜ我々はここにいるんだ？",
                "kaltsit": "論理的に考えれば、その答えはすでに君の中にあるはずだ。",
            },
        ]
