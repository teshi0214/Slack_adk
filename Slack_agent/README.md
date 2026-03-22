# Slack Agent

Slack のチャンネル・メッセージ・スレッドを取得・要約・分析する Google ADK エージェントです。  
Vertex AI (Gemini) を使用し、Google アカウント認証で動作します。

---

## セットアップ

### 1. Slack App の作成と Bot Token 取得

1. [Slack API](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. **OAuth & Permissions** → **Bot Token Scopes** に以下を追加:

   | スコープ | 用途 |
   |---|---|
   | `channels:read` | パブリックチャンネル一覧 |
   | `groups:read` | プライベートチャンネル一覧 |
   | `channels:history` | パブリックチャンネルの履歴 |
   | `groups:history` | プライベートチャンネルの履歴 |
   | `users:read` | ユーザー情報 |
   | `users:read.email` | ユーザーメール |

3. **Install App to Workspace** → `xoxb-...` トークンをコピー

4. **全文検索 (search_messages) を使う場合のみ**: User Token スコープ `search:read` も追加し  
   `xoxp-...` トークンも取得

### 2. ボットをチャンネルに追加

```
/invite @あなたのBotName
```

### 3. 環境変数の設定

プロジェクトルート (`BQ_remote_Ver2`) の `.env` に追記:

```env
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxx
# SLACK_USER_TOKEN=xoxp-...  # 全文検索が必要な場合のみ
```

### 4. 依存ライブラリのインストール

```bash
cd /Users/teshigawaraosamutaira/Desktop/BQ_remote_Ver2
source .venv/bin/activate
pip install slack-sdk
```

---

## 起動方法

```bash
cd /Users/teshigawaraosamutaira/Desktop/BQ_remote_Ver2
source .venv/bin/activate

# ADK Web UI
adk web

# または ADK CLI
adk run Slack_agent
```

---

## 利用例

```
# チャンネル一覧を教えて
# generalチャンネルの過去24時間の投稿を要約して
# devチャンネルの過去3日間（72時間）の投稿を確認して
# "デプロイ" というキーワードで全チャンネルを検索して
# このスレッド（ts: 1234567890.123456）の返信を見せて
```

---

## ファイル構成

```
Slack_agent/
├── __init__.py       # root_agent エクスポート
├── agent.py          # LlmAgent 定義
├── slack_tool.py     # Slack API ツール群 (FunctionTool)
├── pyproject.toml
├── requirements.txt
├── .env.example      # 環境変数サンプル
└── README.md
```

---

## ツール一覧

| ツール名 | 説明 | 必要Token |
|---|---|---|
| `list_channels` | チャンネル一覧取得 | Bot |
| `get_channel_messages` | チャンネルのメッセージ履歴 | Bot |
| `get_thread_replies` | スレッドの返信取得 | Bot |
| `search_messages` | 全文検索 | User Token |
| `get_user_info` | ユーザーID→名前解決 | Bot |
