# Slack 側セットアップ手順

このドキュメントは Slack Agent Bot を使うために **Slack 側で必要な操作** をまとめたものです。

---

## STEP 1: Slack App の作成

### 1-1. アプリ作成ページを開く

[https://api.slack.com/apps](https://api.slack.com/apps) にアクセス

→ **「新しいアプリを作成する」** をクリック

→ **「マニフェストからアプリを作成する」** を選択

---

### 1-2. マニフェストを貼り付ける

以下の JSON をそのまま貼り付けて **「次」** をクリック

```json
{
    "display_information": {
        "name": "Slack Agent Bot"
    },
    "features": {
        "bot_user": {
            "display_name": "Slack Agent Bot",
            "always_online": true
        }
    },
    "oauth_config": {
        "scopes": {
            "bot": [
                "channels:read",
                "groups:read",
                "channels:history",
                "groups:history",
                "users:read",
                "users:read.email",
                "im:read",
                "im:history",
                "mpim:read",
                "mpim:history"
            ]
        }
    },
    "settings": {
        "org_deploy_enabled": false,
        "socket_mode_enabled": false,
        "is_hosted": false,
        "token_rotation_enabled": false
    }
}
```

→ ワークスペースを選択して **「次」→「作成」**

---

## STEP 2: Bot Token の取得

### 2-1. OAuth & Permissions を開く

左サイドバー → **「OAuth & Permissions」**

### 2-2. ワークスペースにインストール

ページ上部の **「Install to Workspace」** をクリック

→ 権限を確認して **「許可する」**

### 2-3. Bot Token をコピー

```
Bot User OAuth Token
xoxb-xxxxxxxxxx-xxxxxxxxxx-xxxxxxxxxxxxxxxx
```

→ この `xoxb-...` トークンをコピーして `.env` に設定

```env
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxx-xxxxxxxxxx-xxxxxxxxxxxxxxxx
```

---

## STEP 3: DM機能を有効にする

### 3-1. App Home を開く

左サイドバー → **「App Home」**

### 3-2. Messages Tab を有効にする

ページ下部の **「Show Tabs」** セクション

→ **「Messages Tab」** をON

→ **「Allow users to send Slash commands and messages from the messages tab」** をON

→ **「Save Changes」**

---

## STEP 4: ボットをチャンネルに招待する

監視・取得したいチャンネルにボットを招待する必要があります。

### Slack アプリ上での操作

対象チャンネルを開いて以下を入力：

```
/invite @Slack Agent Bot
```

### 招待が必要なチャンネル一覧（例）

| チャンネル | 用途 |
|---|---|
| `#general` | 全体連絡の監視 |
| `#プロジェクト-XXX` | 案件ごとの状況把握 |
| `#障害対応` | インシデント監視 |
| `#保守-XXX` | 顧客問い合わせ監視 |

> ⚠️ 招待しないとそのチャンネルのメッセージは取得できません

---

## STEP 5: ボットに DM を送る（DM機能の有効化）

左サイドバー **「App」セクション** の **「Slack Agent Bot」** をクリック

→ メッセージを送信してDMチャンネルを開通させる

```
こんにちは
```

これで `get_dm_messages` でそのDMが取得できるようになります。

---

## スコープ一覧（付与した権限）

| スコープ | 内容 |
|---|---|
| `channels:read` | パブリックチャンネル一覧の取得 |
| `groups:read` | プライベートチャンネル一覧の取得 |
| `channels:history` | パブリックチャンネルの履歴取得 |
| `groups:history` | プライベートチャンネルの履歴取得 |
| `users:read` | ユーザー情報の取得 |
| `users:read.email` | ユーザーのメールアドレス取得 |
| `im:read` | DM一覧の取得 |
| `im:history` | DMメッセージの履歴取得 |
| `mpim:read` | グループDM一覧の取得 |
| `mpim:history` | グループDMメッセージの履歴取得 |

---

## トラブルシューティング

| エラー・症状 | 原因 | 対処 |
|---|---|---|
| `not_in_channel` | ボットがチャンネルに未参加 | `/invite @Slack Agent Bot` で招待 |
| `channel_not_found` | チャンネル名が間違っている | `#` なしのチャンネル名を確認 |
| `missing_scope` | スコープが不足 | OAuth & Permissions でスコープを追加して再インストール |
| DMが取得できない | ボットにDMを送っていない | App セクションからボットにDMを送る |
| `このアプリへのメッセージ送信はオフ` | Messages Tab が無効 | STEP 3 の設定を確認 |

---

## スコープ追加が必要になった場合

1. [https://api.slack.com/apps](https://api.slack.com/apps) → アプリを選択
2. 左サイドバー → **「OAuth & Permissions」**
3. **「Bot Token Scopes」** → **「Add an OAuth Scope」** でスコープを追加
4. ページ上部の **「Reinstall to Workspace」** をクリック
5. 新しい `xoxb-...` トークンを `.env` に更新して ADK を再起動
