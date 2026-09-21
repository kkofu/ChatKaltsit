#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import random
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import requests
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


@dataclass
class CharacterProfile:
    """角色特征档案"""

    name: str = "普瑞赛斯"
    personality_traits: Dict[str, float] = None
    language_patterns: Dict[str, float] = None
    vocabulary_style: Dict[str, float] = None
    emotional_tone: Dict[str, float] = None

    def __post_init__(self):
        if self.personality_traits is None:
            self.personality_traits = {
                "哲学思辨": 0.8,
                "理性逻辑": 0.6,
                "好奇探索": 0.7,
                "自信权威": 0.5,
                "惊讶意外": 0.3,
            }

        if self.language_patterns is None:
            self.language_patterns = {
                "疑问句比例": 0.186,
                "感叹句比例": 0.011,
                "平均句长": 22.5,
                "词汇多样性": 0.453,
            }

        if self.vocabulary_style is None:
            self.vocabulary_style = {
                "正式程度": 0.7,
                "抽象概念": 0.8,
                "技术术语": 0.6,
                "哲学词汇": 0.9,
            }

        if self.emotional_tone is None:
            self.emotional_tone = {
                "平静中性": 0.6,
                "好奇兴趣": 0.3,
                "自信肯定": 0.2,
                "思考沉思": 0.4,
            }


class PresetDialogueSystem:
    """普瑞赛斯对话系统核心"""

    def __init__(self, dialogues_file: str):
        self.character_profile = CharacterProfile()
        self.dialogues_df = self._load_dialogues(dialogues_file)
        self.response_templates = self._build_response_templates()
        self.api_config = self._load_api_config()

    def _load_dialogues(self, file_path: str) -> Any:
        """加载对话数据"""
        import pandas as pd

        return pd.read_csv(file_path)

    def _load_api_config(self) -> Dict[str, str]:
        """加载API配置"""
        return {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "claude_api_key": os.getenv("CLAUDE_API_KEY", ""),
            "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
            "huggingface_api_key": os.getenv("HUGGINGFACE_API_KEY", ""),
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        }

    def _build_response_templates(self) -> Dict[str, List[str]]:
        """构建响应模板库"""
        return {
            "哲学思辨": [
                "这让我想到了一个有趣的问题：{topic}的本质是什么？",
                "从存在的角度来看，{topic}似乎具有更深层的意义。",
                "也许我们应该重新审视{topic}这个概念本身。",
                "这涉及到一个根本性的问题：{topic}。",
            ],
            "好奇探索": [
                "关于{topic}，我很想知道你的看法。",
                "{topic}确实值得深入研究，你觉得呢？",
                "让我们一起来探索{topic}的奥秘吧。",
                "你对{topic}的理解是什么？",
            ],
            "理性分析": [
                "从逻辑上分析，{topic}可以这样理解...",
                "基于现有信息，{topic}的结论似乎是...",
                "让我们理性地看待{topic}这个问题。",
                "关于{topic}，我们需要更多的数据来验证。",
            ],
            "自信权威": [
                "关于{topic}，答案是很明确的。",
                "毫无疑问，{topic}就是如此。",
                "从我的角度来看，{topic}的答案是确定的。",
                "关于{topic}，我可以肯定地告诉你...",
            ],
            "惊讶意外": [
                "这真的很有趣！{topic}居然会这样。",
                "没想到{topic}会是这样的发展。",
                "这确实让我感到意外，{topic}。",
                "哇，{topic}的结果真是出人意料。",
            ],
            "疑问质疑": [
                "关于{topic}，你确定吗？",
                "难道{topic}真的是这样吗？",
                "为什么{topic}会是这样？",
                "你怎么能确定{topic}的正确性？",
            ],
        }

    def _extract_keywords(self, user_input: str) -> List[str]:
        """提取用户输入的关键词"""
        import jieba

        words = list(jieba.cut(user_input))
        # 过滤停用词
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
        }
        keywords = [w for w in words if len(w) > 1 and w not in stop_words]
        return keywords[:5]  # 返回前5个关键词

    def _select_response_style(self, user_input: str) -> str:
        """选择响应风格"""
        # 基于用户输入的特征选择合适的响应风格
        if "为什么" in user_input or "怎么" in user_input:
            return "理性分析"
        elif "吗" in user_input or "呢" in user_input:
            return "疑问质疑"
        elif "觉得" in user_input or "认为" in user_input:
            return "哲学思辨"
        elif "告诉" in user_input or "解释" in user_input:
            return "好奇探索"
        elif "确定" in user_input or "肯定" in user_input:
            return "自信权威"
        else:
            # 根据角色特征随机选择
            styles = list(self.response_templates.keys())
            weights = [
                self.character_profile.personality_traits.get("哲学思辨", 0.8),
                self.character_profile.personality_traits.get("好奇探索", 0.7),
                self.character_profile.personality_traits.get("理性逻辑", 0.6),
                self.character_profile.personality_traits.get("自信权威", 0.5),
                self.character_profile.personality_traits.get("惊讶意外", 0.3),
                self.character_profile.personality_traits.get("质疑挑战", 0.4),
            ]
            return random.choices(styles, weights=weights)[0]

    def _generate_template_response(self, user_input: str) -> str:
        """基于模板生成响应"""
        keywords = self._extract_keywords(user_input)
        style = self._select_response_style(user_input)

        templates = self.response_templates[style]
        template = random.choice(templates)

        # 用关键词替换模板中的占位符
        if keywords and "{topic}" in template:
            topic = random.choice(keywords)
            response = template.format(topic=topic)
        else:
            response = template.replace("{topic}", "这个问题")

        return response

    def _call_openai_api(self, user_input: str) -> Optional[str]:
        """调用OpenAI API生成响应"""
        if not self.api_config["openai_api_key"]:
            return None

        try:
            # 构建普瑞赛斯角色提示
            system_prompt = f"""
你是普瑞赛斯，一位来自明日方舟的语言学家和研究者。你的性格特征如下：
{self._get_character_prompt()}

请以普瑞赛斯的身份和语调回应用户的输入。保持角色的哲学思辨风格、理性分析能力和好奇心。
"""

            headers = {
                "Authorization": f"Bearer {self.api_config['openai_api_key']}",
                "Content-Type": "application/json",
            }

            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                "max_tokens": 150,
                "temperature": 0.7,
            }

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            print(f"OpenAI API调用失败: {e}")

        return None

    def _call_openrouter_api(self, user_input: str) -> Optional[str]:
        """调用OpenRouter API生成响应"""
        if not self.api_config["openrouter_api_key"]:
            return None

        try:
            # 构建普瑞赛斯角色提示
            system_prompt = f"""
你是普瑞赛斯，一位来自明日方舟的语言学家和研究者。你的性格特征如下：
{self._get_character_prompt()}

请以普瑞赛斯的身份和语调回应用户的输入。保持角色的哲学思辨风格、理性分析能力和好奇心。
"""

            headers = {
                "Authorization": f"Bearer {self.api_config['openrouter_api_key']}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8080",
                "X-Title": "PresetAIAssistant",
            }

            data = {
                "model": "z-ai/glm-4.5-air:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                "max_tokens": 300,
                "temperature": 0.7,
            }

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=15,
            )

            if response.status_code == 200:
                result = response.json()
                message = result["choices"][0]["message"]

                # 优先使用content，如果为空则使用reasoning
                content = message.get("content", "").strip()
                reasoning = message.get("reasoning", "").strip()

                if content:
                    return content
                elif reasoning:
                    # 如果只有推理过程，提取关键观点
                    return (
                        reasoning[:200] + "..." if len(reasoning) > 200 else reasoning
                    )
                else:
                    return "我在思考这个问题，但还没有得出明确的结论。"
            else:
                print(f"OpenRouter API错误: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"OpenRouter API调用失败: {e}")

        return None

    def _call_gemini_api(self, user_input: str) -> Optional[str]:
        """调用Google Gemini API生成响应"""
        if not self.api_config["gemini_api_key"]:
            return None

        try:
            system_prompt = (
                f"你是普瑞赛斯，请以以下角色特征回应：{self._get_character_prompt()}"
            )

            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"{system_prompt}\n\n用户输入: {user_input}\n\n请以普瑞赛斯的身份回应:"
                            }
                        ]
                    }
                ]
            }

            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.api_config['gemini_api_key']}",
                headers=headers,
                json=data,
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()

        except Exception as e:
            print(f"Gemini API调用失败: {e}")

        return None

    def _get_character_prompt(self) -> str:
        """获取角色特征描述"""
        return f"""
性格特征：
- 哲学思辨倾向：{self.character_profile.personality_traits.get("哲学思辨", 0.8):.1%}
- 理性逻辑思维：{self.character_profile.personality_traits.get("理性逻辑", 0.6):.1%}
- 好奇探索精神：{self.character_profile.personality_traits.get("好奇探索", 0.7):.1%}
- 自信权威态度：{self.character_profile.personality_traits.get("自信权威", 0.5):.1%}

语言风格：
- 倾向使用疑问句（{self.character_profile.language_patterns.get("疑问句比例", 0.186):.1%}）
- 平均句长约{self.character_profile.language_patterns.get("平均句长", 22.5):.1f}字
- 词汇多样性较高（{self.character_profile.language_patterns.get("词汇多样性", 0.453):.1%}）

常用话题：宇宙、存在、真理、逻辑、本质、意义等哲学概念
"""

    def generate_response(self, user_input: str, use_api: bool = True) -> str:
        """生成响应"""
        if not user_input.strip():
            return "请告诉我你想讨论什么？我很想知道你的想法。"

        # 首先尝试使用API
        if use_api:
            # 优先尝试OpenRouter API (GLM-4.5-Air)
            api_response = self._call_openrouter_api(user_input)
            if api_response:
                return api_response

            # 尝试OpenAI API
            api_response = self._call_openai_api(user_input)
            if api_response:
                return api_response

            # 尝试Gemini API
            api_response = self._call_gemini_api(user_input)
            if api_response:
                return api_response

        # 如果API不可用，使用优化的响应生成器
        try:
            from optimized_response_generator import OptimizedPresetResponseGenerator

            if not hasattr(self, "optimized_generator"):
                self.optimized_generator = OptimizedPresetResponseGenerator(
                    self.character_profile
                )
            return self.optimized_generator.generate_response(user_input)
        except ImportError:
            # 如果优化生成器不可用，使用基础模板响应
            return self._generate_template_response(user_input)

    def get_conversation_examples(self) -> List[Dict[str, str]]:
        """获取对话示例"""
        return [
            {
                "user": "你觉得宇宙的本质是什么？",
                "preset": "这让我想到了一个根本性的问题：宇宙的本质是什么？也许我们一直都在用错误的方式试图理解它。",
            },
            {
                "user": "你能解释一下这个现象吗？",
                "preset": "关于这个现象，我很想知道你的看法。从逻辑上分析，它似乎涉及更深层的规律。",
            },
            {
                "user": "你确定这个答案吗？",
                "preset": "关于这个问题，答案是很明确的。但你是否真的理解了其中的本质？",
            },
        ]


# 全局对话系统实例
dialogue_system = None


def init_dialogue_system():
    """初始化对话系统"""
    global dialogue_system
    dialogues_file = (
        "data/kaltsit_dialogues.csv"
    )
    dialogue_system = PresetDialogueSystem(dialogues_file)
