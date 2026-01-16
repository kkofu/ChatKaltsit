#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
普瑞赛斯语言特征分析器
分析普瑞赛斯的对话风格和性格特征
"""

import json
import pandas as pd
import re
from collections import Counter, defaultdict
from typing import Dict, List, Any
import jieba
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体
plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


class PresetLanguageAnalyzer:
    def __init__(self, dialogues_file: str):
        self.dialogues_df = pd.read_csv(dialogues_file)
        self.dialogues = self.dialogues_df["content"].tolist()

    def clean_text(self, text: str) -> str:
        """清理文本，移除特殊标记"""
        # 移除（未知语言）标记
        text = re.sub(r"（未知语言）", "", text)
        # 移除{@nickname}等变量标记
        text = re.sub(r"\{[^}]+\}", "", text)
        # 移除引号
        text = re.sub(r'["""]', "", text)
        # 移除多余空格
        text = re.sub(r"\s+", "", text)
        return text.strip()

    def analyze_basic_statistics(self) -> Dict[str, Any]:
        """基础统计分析"""
        cleaned_dialogues = [self.clean_text(d) for d in self.dialogues]
        lengths = [len(d) for d in cleaned_dialogues if d]

        return {
            "total_dialogues": len(self.dialogues),
            "avg_length": np.mean(lengths) if lengths else 0,
            "median_length": np.median(lengths) if lengths else 0,
            "min_length": min(lengths) if lengths else 0,
            "max_length": max(lengths) if lengths else 0,
            "empty_dialogues": sum(1 for d in cleaned_dialogues if not d),
        }

    def analyze_vocabulary(self) -> Dict[str, Any]:
        """词汇分析"""
        cleaned_dialogues = [
            self.clean_text(d) for d in self.dialogues if self.clean_text(d)
        ]
        all_text = "".join(cleaned_dialogues)

        # 分词
        words = list(jieba.cut(all_text))
        # 过滤掉单字和常见停用词
        stop_words = {
            "的",
            "了",
            "是",
            "在",
            "我",
            "你",
            "他",
            "她",
            "它",
            "们",
            "这",
            "那",
            "有",
            "不",
            "也",
            "就",
            "都",
            "而",
            "吗",
            "呢",
            "啊",
            "吧",
            "么",
            "？",
            "！",
            "，",
            "。",
            "；",
            "：",
            '"',
            '"',
            """, """,
            "（",
            "）",
            "【",
            "】",
            "、",
        }
        words = [w for w in words if len(w) > 1 and w not in stop_words]

        word_freq = Counter(words)

        return {
            "total_words": len(words),
            "unique_words": len(set(words)),
            "most_common_words": word_freq.most_common(20),
            "word_diversity": len(set(words)) / len(words) if words else 0,
        }

    def analyze_sentence_patterns(self) -> Dict[str, Any]:
        """句式模式分析"""
        cleaned_dialogues = [
            self.clean_text(d) for d in self.dialogues if self.clean_text(d)
        ]

        # 分析句式特征
        question_patterns = 0
        exclamation_patterns = 0
        conditional_patterns = 0
        rhetorical_patterns = 0

        for dialogue in cleaned_dialogues:
            # 疑问句
            if "吗" in dialogue or "呢" in dialogue or "？" in dialogue:
                question_patterns += 1
            # 感叹句
            if "！" in dialogue or dialogue.endswith("啊") or dialogue.endswith("吧"):
                exclamation_patterns += 1
            # 条件句
            if "如果" in dialogue or "那么" in dialogue or "既然" in dialogue:
                conditional_patterns += 1
            # 反问句
            if (
                "难道" in dialogue or "怎么" in dialogue or "为什么" in dialogue
            ) and "？" in dialogue:
                rhetorical_patterns += 1

        return {
            "question_sentences": question_patterns,
            "exclamation_sentences": exclamation_patterns,
            "conditional_sentences": conditional_patterns,
            "rhetorical_sentences": rhetorical_patterns,
            "question_ratio": question_patterns / len(cleaned_dialogues)
            if cleaned_dialogues
            else 0,
            "exclamation_ratio": exclamation_patterns / len(cleaned_dialogues)
            if cleaned_dialogues
            else 0,
        }

    def analyze_personality_traits(self) -> Dict[str, Any]:
        """性格特征分析"""
        cleaned_dialogues = [
            self.clean_text(d) for d in self.dialogues if self.clean_text(d)
        ]

        # 性格相关关键词
        traits = {
            "理性/逻辑": [
                "逻辑",
                "理性",
                "分析",
                "推理",
                "假设",
                "前提",
                "结论",
                "证明",
            ],
            "哲学/思辨": ["存在", "本质", "意义", "真理", "宇宙", "神", "绝对", "相对"],
            "好奇/探索": ["为什么", "如何", "怎样", "什么", "探索", "发现", "研究"],
            "自信/权威": ["当然", "显然", "毫无疑问", "必须", "一定", "绝对"],
            "惊讶/意外": ["惊喜", "意外", "没想到", "居然", "竟然"],
            "质疑/挑战": ["难道", "怎么", "为什么", "真的吗", "确定吗"],
        }

        trait_scores = {}
        for trait, keywords in traits.items():
            count = 0
            for dialogue in cleaned_dialogues:
                for keyword in keywords:
                    if keyword in dialogue:
                        count += 1
            trait_scores[trait] = count

        return trait_scores

    def analyze_emotional_tone(self) -> Dict[str, Any]:
        """情感语调分析"""
        cleaned_dialogues = [
            self.clean_text(d) for d in self.dialogues if self.clean_text(d)
        ]

        # 情感词汇
        emotions = {
            "平静/中性": ["嗯", "哦", "好", "是的", "没错", "当然"],
            "好奇/兴趣": ["有趣", "有意思", "想知道", "告诉我", "说说"],
            "惊讶/意外": ["哇", "啊", "真的", "居然", "没想到"],
            "思考/沉思": ["让我想想", "有意思", "嗯...", "原来如此"],
            "挑战/质疑": ["真的吗", "确定", "为什么", "怎么可能"],
            "自信/肯定": ["当然", "必须", "一定", "绝对", "毫无疑问"],
        }

        emotion_scores = {}
        for emotion, keywords in emotions.items():
            count = 0
            for dialogue in cleaned_dialogues:
                for keyword in keywords:
                    if keyword in dialogue:
                        count += 1
            emotion_scores[emotion] = count

        return emotion_scores

    def generate_character_profile(self) -> str:
        """生成角色特征档案"""
        stats = self.analyze_basic_statistics()
        vocab = self.analyze_vocabulary()
        patterns = self.analyze_sentence_patterns()
        personality = self.analyze_personality_traits()
        emotions = self.analyze_emotional_tone()

        profile = f"""
=== 普瑞赛斯角色特征档案 ===

## 基础统计
- 总对话数: {stats["total_dialogues"]}
- 平均句长: {stats["avg_length"]:.1f} 字
- 最长句: {stats["max_length"]} 字
- 最短句: {stats["min_length"]} 字

## 语言特征
- 词汇总量: {vocab["total_words"]}
- 独特词汇: {vocab["unique_words"]}
- 词汇多样性: {vocab["word_diversity"]:.3f}
- 疑问句比例: {patterns["question_ratio"]:.1%}
- 感叹句比例: {patterns["exclamation_ratio"]:.1%}

## 性格特征 (关键词频次)
"""
        for trait, score in sorted(
            personality.items(), key=lambda x: x[1], reverse=True
        ):
            profile += f"- {trait}: {score} 次\n"

        profile += "\n## 情感语调 (关键词频次)\n"
        for emotion, score in sorted(
            emotions.items(), key=lambda x: x[1], reverse=True
        ):
            profile += f"- {emotion}: {score} 次\n"

        profile += f"\n## 高频词汇 (前20个)\n"
        for word, freq in vocab["most_common_words"][:20]:
            profile += f"- {word}: {freq} 次\n"

        return profile

    def save_analysis_report(self, output_path: str):
        """保存分析报告"""
        profile = self.generate_character_profile()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(profile)

        print(f"分析报告已保存到: {output_path}")
        print(profile)


def main():
    dialogues_file = (
        "/Users/bowen/Codes/ArknightsStoryJson/preset_ai_assistant/preset_dialogues.csv"
    )
    output_path = "/Users/bowen/Codes/ArknightsStoryJson/preset_ai_assistant/preset_character_profile.txt"

    analyzer = PresetLanguageAnalyzer(dialogues_file)
    analyzer.save_analysis_report(output_path)


if __name__ == "__main__":
    main()
