#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChatKaltsit CLI クライアント

使い方:
    python chat_cli.py                  # 通常起動
    python chat_cli.py --no-api         # デバッグ用テンプレート出力
    python chat_cli.py --no-color       # 色なし
    echo -e "/help" | python chat_cli.py --no-api  # パイプ入力
"""

import argparse
import shutil
import sys
import textwrap
import time
import unicodedata
from pathlib import Path

from core import (
    CharacterProfile,
    KaltsitDialogueSystem
)


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GOLD = "\033[33m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"
    RED = "\033[31m"

    @classmethod
    def off(cls):
        for k in ("RESET", "BOLD", "DIM", "GOLD", "GREEN", "CYAN", "GRAY", "RED"):
            setattr(cls, k, "")


def disp_width(s: str) -> int:
    # 全角2・半角1で数えた表示幅
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F", "A") else 1 for ch in s)


def wrap_ja(text: str, width: int, indent: str = "") -> list:
    lines, buf, w = [], "", 0
    for ch in text:
        cw = disp_width(ch)
        if w + cw > width and buf:
            lines.append(buf)
            buf, w = "", 0
        buf += ch
        w += cw
    if buf:
        lines.append(buf)
    if not indent:
        return lines
    return [lines[0]] + [indent + ln for ln in lines[1:]] if lines else lines

def term_width(default: int = 70) -> int:
    try:
        return max(40, min(shutil.get_terminal_size().columns - 4, 100))
    except Exception:
        return default


def center_ja(s: str, width: int) -> str:
    # 全角考慮の中央寄せ
    pad = max(0, width - disp_width(s))
    left = pad // 2
    return " " * left + s + " " * (pad - left)


def print_profile(system: KaltsitDialogueSystem):
    cp = system.character_profile
    print(f"{C.GOLD}{C.BOLD}ケルシー 人物ファイル{C.RESET}")
    traits = sorted((cp.personality_traits or {}).items(), key=lambda kv: -kv[1])
    vmax = max([v for _, v in traits] + [1e-9])
    for k, v in traits:
        bar = "█" * max(1, round(v / vmax * 16))
        print(f"  {k:8s} {bar} {C.GRAY}{v:.0%}{C.RESET}" if v <= 1 else f"  {k:8s} {v:.0f}件")
    lp = cp.language_patterns or {}
    print(f"  平均文長: {lp.get('平均文長', '?'):.1f}字 / 疑問文: {lp.get('疑問文割合', 0):.1%} / "
          f"命令: {lp.get('命令・指示文割合', 0):.1%}")
    if cp.style_guide.get("top_entities"):
        print(f"  固有名: {', '.join(cp.style_guide['top_entities'][:8])}")


def main() -> int:
    ap = argparse.ArgumentParser(description="ChatKaltsit CLI クライアント")
    ap.add_argument("--dialogues", default="data/kaltsit_dialogues.csv")
    ap.add_argument("--profile-json", default="data/kaltsit_character_profile.json")
    ap.add_argument("--no-api", action="store_true", help="テンプレート応答")
    ap.add_argument("--no-color", action="store_true", help="色付けを無効化")
    args = ap.parse_args()

    if args.no_color:
        C.off()
    elif sys.platform == "win32":
        try:
            import os

            os.system("")  # レガシーコンソールの ANSI 有効化
        except Exception:
            pass

    system = KaltsitDialogueSystem(args.dialogues, profile_json=args.profile_json)
    print(f"{C.GOLD}{C.BOLD}╔{'═' * 23}╗")
    print(f"║{center_ja('チャット > ケルシー', 23)}║")
    print(f"╚{'═' * 23}╝{C.RESET}")
    print(f"{C.GREEN}200: 通信ルート確保{C.RESET}")
    print(f"{C.GRAY}/help: コマンド一覧, /debug: デバッグ, /exit|:q: 終了{C.RESET}")

    typing_shown = False
    if sys.stdout.isatty():
        print(f"\n{C.GRAY}ケルシー が入力中...{C.RESET}", flush=True)
        typing_shown = True
    try:
        time.sleep(2)
    finally:
        if typing_shown:
            print("\033[1A\033[2K", end="")
    print(f"{C.GOLD}{C.BOLD}ケルシー{C.RESET}{C.GOLD}›{C.RESET} ドクター、君か。用件は何だ？　簡潔に報告してくれ。")


    width = term_width()
    while True:
        try:
            user = input(f"\n{C.CYAN}{C.BOLD}ドクター{C.RESET}{C.CYAN}›{C.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n{C.GOLD}{C.BOLD}ケルシー{C.RESET}{C.GOLD}›{C.RESET} 通信を終了する。また報告してくれ。\n")
            break

        if not user:
            continue
        if user in ("/quit", "/exit", ":q", "またね", "それくらいだ", "以上だ"):
            if user in ("それくらいだ", "以上だ"):
                print(f"\n{C.GOLD}{C.BOLD}ケルシー{C.RESET}{C.GOLD}›{C.RESET} そうか。")
                print(f"          また連絡してくれ。\n")
            else:
                print(f"\n{C.GOLD}{C.BOLD}ケルシー{C.RESET}{C.GOLD}›{C.RESET} 通信を終了する。また報告してくれ。\n")
            break
        if user.startswith("/") or user.startswith(":"):
            if user == "/help":
                print(f"{C.GRAY}  /profile   : ケルシーの人物ファイルを表示")
                print(f"  /debug     : 直近の実行情報・エラーを表示")
                print(f"  /clear     : 会話履歴を消去")
                print(f"  /exit, :q  : 終了{C.RESET}")
                continue
            if user == "/profile":
                print_profile(system)
                continue
            if user == "/debug":
                for ln in system.get_debug_info().splitlines():
                    print(f"  {C.GRAY}{ln}{C.RESET}")
                continue
            if user == "/clear":
                system.clear_history()
                print(f"\n{C.GOLD}{C.BOLD}ケルシー{C.RESET}{C.GOLD}›{C.RESET} わかった、ここまでの話は忘れる。また新たに報告してくれ。")
                continue
            else:
                print(f"{C.RED}{C.BOLD}  Unknown command.{C.RESET}")
                continue

        text = ""
        typing_shown = False
        if sys.stdout.isatty():
            print(f"{C.GRAY}ケルシー が入力中...{C.RESET}", flush=True)
            typing_shown = True
        try:
            text = system.generate_response(user, use_api=not args.no_api)
        finally:
            if typing_shown:
                print("\033[1A\033[2K", end="")  # 入力中表示を消す
        print(f"\n{C.GOLD}{C.BOLD}ケルシー{C.RESET}{C.GOLD}›{C.RESET}", end=" ")
        for ln in wrap_ja(text, width, indent="          "):
            print(f"{ln}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
