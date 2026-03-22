"""
Slack API ツール群

【トークン取得の優先順位】
1. Agentspace OAuth: tool_context.state["temp:<AUTH_ID>"] から取得
2. 環境変数: SLACK_BOT_TOKEN から取得（ローカル・geminni-dev Agent Engine）

AUTH_ID は環境変数 SLACK_AUTH_ID で指定（デフォルト: "auth-slack-agent"）
"""

import os
from datetime import datetime, timedelta
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:
    raise ImportError("slack_sdk が見つかりません。pip install slack-sdk を実行してください。")


# ------------------------------------------------------------------ #
# トークン取得ヘルパー
# ------------------------------------------------------------------ #

def _get_token(tool_context: ToolContext | None = None) -> str:
    """
    Slack Bot Token を取得する。
    Agentspace 環境では tool_context.state から、
    それ以外は環境変数 SLACK_BOT_TOKEN から取得する。
    """
    # 1. Agentspace OAuth トークン（tool_context.state["temp:<AUTH_ID>"]）
    if tool_context is not None:
        auth_id = os.environ.get("SLACK_AUTH_ID", "auth-slack-agent")
        state_key = f"temp:{auth_id}"
        agentspace_token = tool_context.state.get(state_key)
        if agentspace_token:
            return agentspace_token

    # 2. 環境変数フォールバック（ローカル・geminni-dev）
    token = os.environ.get("SLACK_BOT_TOKEN")
    if token:
        return token

    raise ValueError(
        "Slack トークンが取得できません。\n"
        "- ローカル/geminni-dev: .env に SLACK_BOT_TOKEN を設定してください\n"
        "- Agentspace: Authorization リソース（AUTH_ID）を設定してください"
    )


def _get_client(tool_context: ToolContext | None = None) -> WebClient:
    """Slack WebClient を返す"""
    return WebClient(token=_get_token(tool_context))


# ユーザー名キャッシュ
_user_name_cache: dict = {}


def _resolve_user_name(client: WebClient, user_id: str) -> str:
    if not user_id or user_id == "unknown":
        return user_id
    if user_id in _user_name_cache:
        return _user_name_cache[user_id]
    try:
        resp = client.users_info(user=user_id)
        profile = resp["user"].get("profile", {})
        name = profile.get("display_name") or profile.get("real_name") or user_id
    except Exception:
        name = user_id
    _user_name_cache[user_id] = name
    return name


def _enrich_messages(client: WebClient, messages: list) -> list:
    for msg in messages:
        msg["user_name"] = _resolve_user_name(client, msg.get("user_id", "unknown"))
    return messages


# ------------------------------------------------------------------ #
# ツール関数（tool_context を追加）
# ------------------------------------------------------------------ #

def list_channels(tool_context: ToolContext, exclude_archived: bool = True) -> dict:
    """
    Slackワークスペースのチャンネル一覧を取得する。

    Args:
        exclude_archived: アーカイブ済みチャンネルを除外するか (デフォルト: True)
    """
    client = _get_client(tool_context)
    try:
        channels = []
        cursor = None
        while True:
            resp = client.conversations_list(
                exclude_archived=exclude_archived,
                limit=200,
                cursor=cursor,
                types="public_channel,private_channel"
            )
            for ch in resp["channels"]:
                channels.append({
                    "id": ch["id"],
                    "name": ch["name"],
                    "topic": ch.get("topic", {}).get("value", ""),
                    "is_private": ch.get("is_private", False),
                    "num_members": ch.get("num_members", 0),
                })
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        return {"status": "ok", "channels": channels, "total": len(channels)}
    except SlackApiError as e:
        return {"status": "error", "error": str(e)}


def get_channel_messages(
    tool_context: ToolContext,
    channel_name: str,
    hours_ago: int = 24,
    limit: int = 50
) -> dict:
    """
    指定チャンネルのメッセージを取得する。

    Args:
        channel_name: チャンネル名 (例: "general")
        hours_ago: 何時間前から取得するか (デフォルト: 24時間)
        limit: 取得件数上限 (デフォルト: 50件)
    """
    client = _get_client(tool_context)
    ch_name = channel_name.lstrip("#")
    try:
        channels_resp = client.conversations_list(
            types="public_channel,private_channel", limit=1000
        )
        channel_id = None
        for ch in channels_resp["channels"]:
            if ch["name"] == ch_name:
                channel_id = ch["id"]
                break
        if not channel_id:
            return {"status": "error", "error": f"チャンネル '{ch_name}' が見つかりません。"}

        oldest = (datetime.utcnow() - timedelta(hours=hours_ago)).timestamp()
        resp = client.conversations_history(
            channel=channel_id, oldest=str(oldest), limit=limit
        )
        messages = []
        for msg in resp.get("messages", []):
            if msg.get("subtype"):
                continue
            ts_dt = datetime.fromtimestamp(float(msg["ts"]))
            messages.append({
                "ts": msg["ts"],
                "datetime": ts_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "user_id": msg.get("user", "unknown"),
                "text": msg.get("text", ""),
                "reply_count": msg.get("reply_count", 0),
            })
        messages.sort(key=lambda x: x["ts"])
        messages = _enrich_messages(client, messages)
        return {
            "status": "ok", "channel": ch_name, "channel_id": channel_id,
            "messages": messages, "count": len(messages), "period_hours": hours_ago,
        }
    except SlackApiError as e:
        return {"status": "error", "error": str(e)}


def get_thread_replies(tool_context: ToolContext, channel_name: str, thread_ts: str) -> dict:
    """
    指定メッセージのスレッド返信を取得する。

    Args:
        channel_name: チャンネル名 (例: "general")
        thread_ts: 親メッセージのタイムスタンプ
    """
    client = _get_client(tool_context)
    ch_name = channel_name.lstrip("#")
    try:
        channels_resp = client.conversations_list(
            types="public_channel,private_channel", limit=1000
        )
        channel_id = None
        for ch in channels_resp["channels"]:
            if ch["name"] == ch_name:
                channel_id = ch["id"]
                break
        if not channel_id:
            return {"status": "error", "error": f"チャンネル '{ch_name}' が見つかりません。"}

        resp = client.conversations_replies(channel=channel_id, ts=thread_ts)
        replies = []
        for msg in resp.get("messages", []):
            ts_dt = datetime.fromtimestamp(float(msg["ts"]))
            replies.append({
                "ts": msg["ts"],
                "datetime": ts_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "user_id": msg.get("user", "unknown"),
                "text": msg.get("text", ""),
            })
        replies = _enrich_messages(client, replies)
        return {"status": "ok", "thread_ts": thread_ts, "replies": replies, "count": len(replies)}
    except SlackApiError as e:
        return {"status": "error", "error": str(e)}


def search_messages(tool_context: ToolContext, query: str, count: int = 20) -> dict:
    """
    ワークスペース全体でキーワード検索する。User Token が必要。

    Args:
        query: 検索クエリ
        count: 取得件数上限 (デフォルト: 20)
    """
    # search は User Token が必要なため別途取得
    token = os.environ.get("SLACK_USER_TOKEN") or _get_token(tool_context)
    client = WebClient(token=token)
    try:
        resp = client.search_messages(query=query, count=count, sort="timestamp", sort_dir="desc")
        matches = resp.get("messages", {}).get("matches", [])
        results = []
        for m in matches:
            ts_dt = datetime.fromtimestamp(float(m.get("ts", 0)))
            results.append({
                "channel": m.get("channel", {}).get("name", ""),
                "datetime": ts_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "user": m.get("username", ""),
                "text": m.get("text", ""),
                "permalink": m.get("permalink", ""),
            })
        return {"status": "ok", "query": query, "results": results, "count": len(results)}
    except SlackApiError as e:
        return {"status": "error", "error": str(e)}


def get_user_info(tool_context: ToolContext, user_id: str) -> dict:
    """
    ユーザーIDから表示名・メール等を取得する。

    Args:
        user_id: Slack ユーザーID (例: "U01ABCDEF")
    """
    client = _get_client(tool_context)
    try:
        resp = client.users_info(user=user_id)
        user = resp["user"]
        profile = user.get("profile", {})
        return {
            "status": "ok",
            "user_id": user_id,
            "display_name": profile.get("display_name") or profile.get("real_name", ""),
            "real_name": profile.get("real_name", ""),
            "email": profile.get("email", ""),
            "title": profile.get("title", ""),
            "is_bot": user.get("is_bot", False),
        }
    except SlackApiError as e:
        return {"status": "error", "error": str(e)}


# ------------------------------------------------------------------ #
# DM関連ツール
# ------------------------------------------------------------------ #

def list_dms(tool_context: ToolContext) -> dict:
    """ボットが参加しているDM一覧を取得する。"""
    client = _get_client(tool_context)
    try:
        dms = []
        cursor = None
        while True:
            resp = client.conversations_list(types="im", limit=200, cursor=cursor)
            for ch in resp["channels"]:
                dms.append({
                    "channel_id": ch["id"],
                    "user_id": ch.get("user", ""),
                    "is_open": ch.get("is_open", False),
                })
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        for dm in dms:
            dm["user_name"] = _resolve_user_name(client, dm["user_id"])
        return {"status": "ok", "dms": dms, "total": len(dms)}
    except SlackApiError as e:
        return {"status": "error", "error": str(e)}


def get_dm_messages(tool_context: ToolContext, user_id: str, hours_ago: int = 24, limit: int = 100) -> dict:
    """
    特定ユーザーとのDM履歴を取得する。

    Args:
        user_id: 相手のSlackユーザーID
        hours_ago: 何時間前から取得するか (デフォルト: 24時間)
        limit: 取得件数上限 (デフォルト: 100件)
    """
    client = _get_client(tool_context)
    try:
        resp = client.conversations_list(types="im", limit=1000)
        channel_id = None
        for ch in resp["channels"]:
            if ch.get("user") == user_id:
                channel_id = ch["id"]
                break
        if not channel_id:
            return {"status": "error", "error": f"ユーザー '{user_id}' とのDMが見つかりません。"}

        oldest = (datetime.utcnow() - timedelta(hours=hours_ago)).timestamp()
        messages = []
        cursor = None
        while True:
            kwargs = {"channel": channel_id, "oldest": str(oldest), "limit": min(limit, 200)}
            if cursor:
                kwargs["cursor"] = cursor
            history = client.conversations_history(**kwargs)
            for msg in history.get("messages", []):
                if msg.get("subtype"):
                    continue
                ts_dt = datetime.fromtimestamp(float(msg["ts"]))
                messages.append({
                    "ts": msg["ts"],
                    "datetime": ts_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "user_id": msg.get("user", "unknown"),
                    "text": msg.get("text", ""),
                })
            cursor = history.get("response_metadata", {}).get("next_cursor")
            if not cursor or len(messages) >= limit:
                break

        messages.sort(key=lambda x: x["ts"])
        messages = messages[:limit]
        messages = _enrich_messages(client, messages)
        return {
            "status": "ok", "with_user_id": user_id,
            "messages": messages, "count": len(messages), "period_hours": hours_ago,
        }
    except SlackApiError as e:
        return {"status": "error", "error": str(e)}


def list_group_dms(tool_context: ToolContext) -> dict:
    """ボットが参加しているグループDM一覧を取得する。"""
    client = _get_client(tool_context)
    try:
        group_dms = []
        cursor = None
        while True:
            resp = client.conversations_list(types="mpim", limit=200, cursor=cursor)
            for ch in resp["channels"]:
                group_dms.append({
                    "channel_id": ch["id"],
                    "name": ch.get("name", ""),
                    "num_members": ch.get("num_members", 0),
                })
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        return {"status": "ok", "group_dms": group_dms, "total": len(group_dms)}
    except SlackApiError as e:
        return {"status": "error", "error": str(e)}


def get_group_dm_messages(tool_context: ToolContext, channel_id: str, hours_ago: int = 24, limit: int = 50) -> dict:
    """
    グループDMのメッセージ履歴を取得する。

    Args:
        channel_id: グループDMのチャンネルID
        hours_ago: 何時間前から取得するか (デフォルト: 24時間)
        limit: 取得件数上限 (デフォルト: 50件)
    """
    client = _get_client(tool_context)
    try:
        oldest = (datetime.utcnow() - timedelta(hours=hours_ago)).timestamp()
        resp = client.conversations_history(channel=channel_id, oldest=str(oldest), limit=limit)
        messages = []
        for msg in resp.get("messages", []):
            if msg.get("subtype"):
                continue
            ts_dt = datetime.fromtimestamp(float(msg["ts"]))
            messages.append({
                "ts": msg["ts"],
                "datetime": ts_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "user_id": msg.get("user", "unknown"),
                "text": msg.get("text", ""),
            })
        messages.sort(key=lambda x: x["ts"])
        messages = _enrich_messages(client, messages)
        return {
            "status": "ok", "channel_id": channel_id,
            "messages": messages, "count": len(messages), "period_hours": hours_ago,
        }
    except SlackApiError as e:
        return {"status": "error", "error": str(e)}


# ------------------------------------------------------------------ #
# ADK FunctionTool ラッパー
# ------------------------------------------------------------------ #

slack_list_channels_tool = FunctionTool(list_channels)
slack_get_messages_tool = FunctionTool(get_channel_messages)
slack_get_thread_tool = FunctionTool(get_thread_replies)
slack_search_tool = FunctionTool(search_messages)
slack_user_info_tool = FunctionTool(get_user_info)
slack_list_dms_tool = FunctionTool(list_dms)
slack_get_dm_messages_tool = FunctionTool(get_dm_messages)
slack_list_group_dms_tool = FunctionTool(list_group_dms)
slack_get_group_dm_messages_tool = FunctionTool(get_group_dm_messages)
