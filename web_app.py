#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, jsonify, request
from core import (
    CharacterProfile,
    PresetDialogueSystem
)

__all__ = [
    'app', 'dialogue_system', 'init_dialogue_system', 'CharacterProfile', 'PresetDialogueSystem',
]

# Flask Web应用
app = Flask(__name__)


@app.route("/")
def index():
    """主页"""
    html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>普瑞赛斯AI对话助手</title>
    <style>
        body { font-family: 'Microsoft YaHei', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .character-info { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .chat-box { border: 1px solid #ddd; height: 400px; overflow-y: auto; padding: 15px; margin-bottom: 15px; background: #fafafa; }
        .message { margin-bottom: 10px; padding: 8px 12px; border-radius: 5px; max-width: 80%; }
        .user-message { background: #007bff; color: white; margin-left: auto; text-align: right; }
        .preset-message { background: #28a745; color: white; }
        .input-area { display: flex; gap: 10px; }
        input[type="text"] { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .examples { margin-top: 20px; }
        .example-item { background: #e9ecef; padding: 10px; margin: 5px 0; border-radius: 5px; cursor: pointer; }
        .example-item:hover { background: #dee2e6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>普瑞赛斯AI对话助手</h1>
        
        <div class="character-info">
            <h3>角色特征</h3>
            <p><strong>性格：</strong>哲学思辨、理性逻辑、好奇探索</p>
            <p><strong>语言风格：</strong>倾向疑问句，词汇丰富，善于抽象思考</p>
            <p><strong>常用话题：</strong>宇宙、存在、真理、逻辑、本质等哲学概念</p>
        </div>
        
        <div class="chat-box" id="chatBox">
            <div class="message preset-message">
                你来了。我很想知道你对这个世界本质的理解。
            </div>
        </div>
        
        <div class="input-area">
            <input type="text" id="userInput" placeholder="请输入你想和普瑞赛斯讨论的话题..." onkeypress="if(event.keyCode==13) sendMessage()">
            <button onclick="sendMessage()">发送</button>
        </div>
        
        <div class="examples">
            <h3>对话示例</h3>
            <div class="example-item" onclick="setInput('你觉得宇宙的本质是什么？')">
                你觉得宇宙的本质是什么？
            </div>
            <div class="example-item" onclick="setInput('你能解释一下这个现象吗？')">
                你能解释一下这个现象吗？
            </div>
            <div class="example-item" onclick="setInput('为什么我们会存在？')">
                为什么我们会存在？
            </div>
        </div>
    </div>
    
    <script>
        function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;
            
            const chatBox = document.getElementById('chatBox');
            
            // 添加用户消息
            const userMsg = document.createElement('div');
            userMsg.className = 'message user-message';
            userMsg.textContent = message;
            chatBox.appendChild(userMsg);
            
            // 清空输入框
            input.value = '';
            
            // 发送到后端
            fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({'message': message})
            })
            .then(response => response.json())
            .then(data => {
                // 添加普瑞赛斯回复
                const presetMsg = document.createElement('div');
                presetMsg.className = 'message preset-message';
                presetMsg.textContent = data.response;
                chatBox.appendChild(presetMsg);
                
                // 滚动到底部
                chatBox.scrollTop = chatBox.scrollHeight;
            })
            .catch(error => {
                console.error('Error:', error);
                const errorMsg = document.createElement('div');
                errorMsg.className = 'message preset-message';
                errorMsg.textContent = '抱歉，我现在无法回应。请稍后再试。';
                chatBox.appendChild(errorMsg);
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
    """对话接口"""
    try:
        data = request.get_json()
        user_message = data.get("message", "")

        if not dialogue_system:
            return jsonify({"error": "对话系统未初始化"}), 500

        response = dialogue_system.generate_response(user_message)
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/character_profile")
def character_profile():
    """获取角色特征档案"""
    if not dialogue_system:
        return jsonify({"error": "对话系统未初始化"}), 500

    profile = dialogue_system.character_profile
    return jsonify(
        {
            "name": profile.name,
            "personality_traits": profile.personality_traits,
            "language_patterns": profile.language_patterns,
            "vocabulary_style": profile.vocabulary_style,
            "emotional_tone": profile.emotional_tone,
        }
    )


@app.route("/examples")
def examples():
    """获取对话示例"""
    if not dialogue_system:
        return jsonify({"error": "对话系统未初始化"}), 500

    return jsonify({"examples": dialogue_system.get_conversation_examples()})


if __name__ == "__main__":
    init_dialogue_system()
    print("普瑞赛斯AI对话助手已启动")
    print("访问 http://localhost:8080 开始对话")
    app.run(host="0.0.0.0", port=8080, debug=False)
