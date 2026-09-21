#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from flask import Flask, jsonify, request
from core import (
    CharacterProfile,
    KaltsitDialogueSystem
)

__all__ = [
    'app', 'dialogue_system', 'init_dialogue_system', 'CharacterProfile', 'KaltsitDialogueSystem',
]

# Flask Webアプリ
app = Flask(__name__)

# 対話システム
dialogue_system = None

def init_dialogue_system():
    global dialogue_system
    dialogues_file = "data/kaltsit_dialogues.csv"
    dialogue_system = KaltsitDialogueSystem(dialogues_file)


@app.route("/")
def index():
    html_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="https://arknights.wiki.gg/images/Kal'tsit_icon.png" />
    <title>チャット > ケルシー</title>
    <style>
        body { font-family: 'Yu Gothic', 'Hiragino Sans', sans-serif; margin: 0 auto; padding: 3vw 5vw; background: #1a1d21; color: #e0e0e0; }
        .container { background: #24282e; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.5); border: 1px solid #3a4048; height: 82vh; }
        .chat-bg-wrap { position: relative; margin-bottom: 15px; }
        .chat-bg { position: absolute; inset: 0; background-image: url("https://arknights.wiki.gg/images/thumb/Kal'tsit.png/1024px-Kal'tsit.png"); background-size: 1200px 1200px; background-position-x: calc(100% + 300px); background-position-y: top; background-repeat: no-repeat; opacity: 0.3; pointer-events: none; border-radius: 5px; }
        .chat-box { border: 1px solid #3a4048; height: 72vh; overflow-y: auto; padding: 15px; background: transparent; border-radius: 5px; position: relative; }
        .message { margin-bottom: 10px; }
        .message div { white-space: pre-wrap; }
        .user-message { background: #2f6db3; color: white; margin-left: auto; text-align: right; padding: 8px 12px; border-radius: 5px; max-width: 80%; width: fit-content; overflow-wrap: break-word; }
        .kaltsit-message { background: #3d4a3a; color: #f0f0e6; border: 1px solid #5a6b57; margin-right: auto; padding: 8px 12px; border-radius: 5px; max-width: 80%; width: fit-content; overflow-wrap: break-word; }
        .typing { opacity: 0.65; font-style: italic; }
        .typing .dots::after { content: ''; animation: typing-dots 1.2s steps(1) infinite; }
        @keyframes typing-dots { 0% { content: ''; } 25% { content: '.'; } 50% { content: '..'; } 75% { content: '...'; } }
        .input-area { display: flex; gap: 10px; }
        input[type="text"] { flex: 1; padding: 10px; border: 1px solid #3a4048; border-radius: 5px; background: #1e2228; color: #e0e0e0; }
        button { padding: 10px 20px; background: #2bbe65; color: #111213; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #e1e86f; }
    </style>
</head>
<body>
    <div class="container">
        <div class="chat-bg-wrap">
            <div class="chat-bg"></div>
            <div class="chat-box" id="chatBox">
                <div class="message">
                    <div class="kaltsit-message">ドクター、君か。用件は何だ？　簡潔に報告してくれ。</div>
                </div>
            </div>
        </div>

        <div class="input-area">
            <input type="text" id="userInput" placeholder="メッセージを入力" onkeypress="if(event.keyCode==13) sendMessage()">
            <button onclick="sendMessage()">送信</button>
        </div>
    </div>

    <script>
        // 40文字超の送信文を均等な長さに分割 (表示用。送信は全文1回のみ)
        function splitBalanced(text, limit) {
            const chars = [...text];  // サロゲートペア(絵文字等)対応
            if (chars.length <= limit) return [text];
            const n = Math.ceil(chars.length / limit);
            const size = Math.ceil(chars.length / n);
            const parts = [];
            for (let i = 0; i < n; i++) {
                parts.push(chars.slice(i * size, (i + 1) * size).join(''));
            }
            return parts;
        }

        function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;

            const chatBox = document.getElementById('chatBox');

            // 吹き出し追加 (.message > .user-message/.kaltsit-message の入れ子)
            function addMessage(role, text) {
                const wrap = document.createElement('div');
                wrap.className = 'message';
                const bubble = document.createElement('div');
                bubble.className = role;
                bubble.textContent = text;
                wrap.appendChild(bubble);
                chatBox.appendChild(wrap);
                return wrap;
            }

            // ユーザーメッセージ追加 (40文字超は均等分割して複数吹き出しに)
            splitBalanced(message, 40).forEach(part => {
                addMessage('user-message', part);
            });

            // 入力欄クリア
            input.value = '';

            // 入力中表示 (応答が来たら消す)
            const typingMsg = document.createElement('div');
            typingMsg.className = 'message';
            const typingBubble = document.createElement('div');
            typingBubble.className = 'kaltsit-message typing';
            typingBubble.innerHTML = 'ケルシーが入力中<span class="dots"></span>';
            typingMsg.appendChild(typingBubble);
            chatBox.appendChild(typingMsg);
            chatBox.scrollTop = chatBox.scrollHeight;

            // バックエンドに送信
            fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({'message': message})
            })
            .then(response => response.json())
            .then(data => {
                typingMsg.remove();
                // ケルシーの返答追加
                const kaltsitMsg = addMessage('kaltsit-message', data.response);
                kaltsitMsg.title = 'via ' + (data.provider || '?') + ' / ' + (data.elapsed_ms || 0) + 'ms';
                console.log('[chat] provider=' + data.provider + ' ' + data.elapsed_ms + 'ms');

                // 最下部にスクロール
                chatBox.scrollTop = chatBox.scrollHeight;
            })
            .catch(error => {
                console.error('Error:', error);
                typingMsg.remove();
                addMessage('kaltsit-message', 'すまない、今は応答できない。後でまた報告しろ。');
                chatBox.scrollTop = chatBox.scrollHeight;
            });
        }

        function setInput(text) {
            document.getElementById('userInput').value = text;
        }
    </script>
</body>
</html>
    """
    return html_template


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")

        if not dialogue_system:
            return jsonify({"error": "対話システムが初期化されていません"}), 500

        msg_stripped = user_message.strip()
        if msg_stripped == "/debug" or msg_stripped.startswith("/debug "):
            info = dialogue_system.handle_debug_command(msg_stripped)
            return jsonify({"response": info, "provider": "debug", "elapsed_ms": 0})

        if msg_stripped == "/clear":
            dialogue_system.clear_history()
            return jsonify({"response": "わかった、ここまでの話は忘れる。また新たに報告してくれ。", "provider": "fixed", "elapsed_ms": 0})

        if msg_stripped == "👋":
            time.sleep(12)
            return jsonify({"response": "……ドクター、何か用があるなら口で言え。", "provider": "debug", "elapsed_ms": 12000})

        response = dialogue_system.generate_response(user_message)
        return jsonify(
            {
                "response": response,
                "provider": dialogue_system.last_provider,
                "elapsed_ms": dialogue_system.last_elapsed_ms,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/character_profile")
def character_profile():
    if not dialogue_system:
        return jsonify({"error": "対話システムが初期化されていません"}), 500

    profile = dialogue_system.character_profile
    return jsonify(
        {
            "name": profile.name,
            "personality_traits": profile.personality_traits,
            "language_patterns": profile.language_patterns,
            "vocabulary_style": profile.vocabulary_style,
            "emotional_tone": profile.emotional_tone,
            "style_guide": profile.style_guide,
            "signature_phrases": profile.signature_phrases,
            "few_shots": profile.few_shots,
            "dialogue_acts": profile.dialogue_acts,
            "source_meta": profile.source_meta,
        }
    )


@app.route("/examples")
def examples():
    if not dialogue_system:
        return jsonify({"error": "対話システムが初期化されていません"}), 500

    return jsonify({"examples": dialogue_system.get_conversation_examples()})


if __name__ == "__main__":
    init_dialogue_system()
    print("ケルシーAI対話アシスタントを起動しました")
    print("http://localhost:8080 にアクセスして対話を開始")
    app.run(host="0.0.0.0", port=8080, debug=False)
