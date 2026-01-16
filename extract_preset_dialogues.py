#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
普瑞赛斯对话语料提取器
从ArknightsStoryJson中提取普瑞赛斯的所有对话
"""

import json
import os
import glob
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any


class PresetDialogueExtractor:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.dialogues = []

    def extract_dialogues_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """从单个JSON文件中提取普瑞赛斯的对话"""
        dialogues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 遍历storyList中的所有条目
            for item in data.get("storyList", []):
                # 检查是否为对话条目且说话者是普瑞赛斯
                if (
                    item.get("prop") == "name"
                    and item.get("attributes", {}).get("name") == "普瑞赛斯"
                    and "content" in item.get("attributes", {})
                ):
                    dialogue_data = {
                        "file": os.path.basename(file_path),
                        "story_code": data.get("storyCode", ""),
                        "story_name": data.get("storyName", ""),
                        "event_id": data.get("eventid", ""),
                        "dialogue_id": item.get("id"),
                        "content": item["attributes"]["content"],
                        "figure_art": item.get("figure_art", ""),
                    }
                    dialogues.append(dialogue_data)

        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")

        return dialogues

    def extract_all_dialogues(self) -> List[Dict[str, Any]]:
        """提取所有文件中的普瑞赛斯对话"""
        json_files = glob.glob(str(self.base_path / "**/*.json"), recursive=True)

        print(f"找到 {len(json_files)} 个JSON文件")

        for file_path in json_files:
            file_dialogues = self.extract_dialogues_from_file(file_path)
            self.dialogues.extend(file_dialogues)

        print(f"总共提取到 {len(self.dialogues)} 条普瑞赛斯对话")
        return self.dialogues

    def save_to_csv(self, output_path: str):
        """将对话保存为CSV文件"""
        if not self.dialogues:
            print("没有对话数据可保存")
            return

        df = pd.DataFrame(self.dialogues)
        df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"对话数据已保存到: {output_path}")

    def save_to_json(self, output_path: str):
        """将对话保存为JSON文件"""
        if not self.dialogues:
            print("没有对话数据可保存")
            return

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.dialogues, f, ensure_ascii=False, indent=2)
        print(f"对话数据已保存到: {output_path}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取对话统计信息"""
        if not self.dialogues:
            return {}

        total_dialogues = len(self.dialogues)
        unique_files = len(set(d["file"] for d in self.dialogues))
        unique_stories = len(set(d["story_code"] for d in self.dialogues))

        # 字符统计
        total_chars = sum(len(d["content"]) for d in self.dialogues)
        avg_chars = total_chars / total_dialogues if total_dialogues > 0 else 0

        return {
            "total_dialogues": total_dialogues,
            "unique_files": unique_files,
            "unique_stories": unique_stories,
            "total_characters": total_chars,
            "average_characters_per_dialogue": avg_chars,
        }


def main():
    # 设置路径
    base_path = "/Users/bowen/Codes/ArknightsStoryJson/zh_CN/gamedata/story/obt/main"
    output_dir = "/Users/bowen/Codes/ArknightsStoryJson/preset_ai_assistant"

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 提取对话
    extractor = PresetDialogueExtractor(base_path)
    dialogues = extractor.extract_all_dialogues()

    # 保存数据
    extractor.save_to_csv(f"{output_dir}/preset_dialogues.csv")
    extractor.save_to_json(f"{output_dir}/preset_dialogues.json")

    # 打印统计信息
    stats = extractor.get_statistics()
    print("\n=== 普瑞赛斯对话统计 ===")
    for key, value in stats.items():
        print(f"{key}: {value}")

    # 显示前几条对话作为示例
    print("\n=== 对话示例 ===")
    for i, dialogue in enumerate(dialogues[:5]):
        print(f"\n{i + 1}. [{dialogue['story_code']}] {dialogue['story_name']}")
        print(f"   {dialogue['content']}")


if __name__ == "__main__":
    main()
