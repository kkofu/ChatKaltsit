#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ケルシー対話コーパス抽出ツール
ArknightsStoryJson (ja_JP) からケルシーの全セリフを抽出する
(旧: 普瑞赛斯/Preset 用スクリプトを日本語ケルシー対応に汎用化)

使い方:
    python extract_kaltsit_dialogues.py
    python extract_kaltsit_dialogues.py --name ケルシー --base-path "ArknightsStoryJson/ja_JP/gamedata/story" --output-dir data
"""

import argparse
import json
import os
import glob
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any


class KaltsitDialogueExtractor:
    """ケルシー(日本語版)のセリフ抽出器"""

    def __init__(self, base_path: str, target_name: str = "ケルシー"):
        self.base_path = Path(base_path)
        self.target_name = target_name
        self.dialogues = []

    def extract_dialogues_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """単一JSONファイルから対象キャラのセリフを抽出"""
        dialogues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # storyList 内の全エントリを走査
            for item in data.get("storyList", []):
                # 対話エントリかつ話者がターゲット名であること
                if (
                    item.get("prop") == "name"
                    and item.get("attributes", {}).get("name") == self.target_name
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
            print(f"ファイル処理エラー {file_path}: {e}")

        return dialogues

    def extract_all_dialogues(self) -> List[Dict[str, Any]]:
        """全ファイルから対象キャラのセリフを抽出"""
        json_files = glob.glob(str(self.base_path / "**/*.json"), recursive=True)

        print(f"{len(json_files)} 件のJSONファイルを検出 (検索対象: {self.base_path})")

        for file_path in json_files:
            file_dialogues = self.extract_dialogues_from_file(file_path)
            self.dialogues.extend(file_dialogues)

        print(f"合計 {len(self.dialogues)} 件の{self.target_name}のセリフを抽出")
        return self.dialogues

    def save_to_csv(self, output_path: str):
        """セリフをCSVファイルに保存"""
        if not self.dialogues:
            print("保存可能なセリフデータがありません")
            return

        df = pd.DataFrame(self.dialogues)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"セリフデータを保存しました: {output_path}")

    def save_to_json(self, output_path: str):
        """セリフをJSONファイルに保存"""
        if not self.dialogues:
            print("保存可能なセリフデータがありません")
            return

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.dialogues, f, ensure_ascii=False, indent=2)
        print(f"セリフデータを保存しました: {output_path}")

    def get_statistics(self) -> Dict[str, Any]:
        """セリフ統計情報を取得"""
        if not self.dialogues:
            return {}

        total_dialogues = len(self.dialogues)
        unique_files = len(set(d["file"] for d in self.dialogues))
        unique_stories = len(set(d["story_code"] for d in self.dialogues))

        # 文字数統計
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
    parser = argparse.ArgumentParser(description="ケルシー対話コーパス抽出ツール")
    parser.add_argument(
        "--name", default="ケルシー", help="抽出対象の話者名 (default: ケルシー)"
    )
    parser.add_argument(
        "--base-path",
        default="ArknightsStoryJson/ja_JP/gamedata/story",
        help="ArknightsStoryJson の story ディレクトリ",
    )
    parser.add_argument(
        "--output-dir", default="data", help="出力ディレクトリ"
    )
    args = parser.parse_args()

    base_path = args.base_path
    output_dir = args.output_dir

    # 出力ディレクトリ作成
    os.makedirs(output_dir, exist_ok=True)

    # セリフ抽出
    extractor = KaltsitDialogueExtractor(base_path, target_name=args.name)
    dialogues = extractor.extract_all_dialogues()

    # データ保存
    extractor.save_to_csv(f"{output_dir}/kaltsit_dialogues.csv")
    extractor.save_to_json(f"{output_dir}/kaltsit_dialogues.json")

    # 統計情報表示
    stats = extractor.get_statistics()
    print(f"\n=== {args.name}セリフ統計 ===")
    for key, value in stats.items():
        print(f"{key}: {value}")

    # サンプル表示
    print("\n=== セリフ例 ===")
    for i, dialogue in enumerate(dialogues[:5]):
        print(f"\n{i + 1}. [{dialogue['story_code']}] {dialogue['story_name']}")
        print(f"   {dialogue['content']}")


if __name__ == "__main__":
    main()
