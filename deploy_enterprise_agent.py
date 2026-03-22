"""
enterprise_search_agent デプロイスクリプト
Vertex AI Agent Engine へのデプロイ
"""

import vertexai
from vertexai.preview import agent_engines
from google.adk.agent_engines import AdkApp

# ============================================================
# 設定
# ============================================================
PROJECT_ID = "geminni-dev"
LOCATION = "europe-west1"       # EUリージョン（Appと合わせる）
STAGING_BUCKET = "gs://geminni-dev-agent-staging"  # 要変更：実際のバケット名

# ============================================================
# Vertex AI 初期化
# ============================================================
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
)

# ============================================================
# エージェントのインポート
# ============================================================
from agent_enterprise import root_agent

# ============================================================
# デプロイ実行
# ============================================================
def deploy():
    print(f"[INFO] Deploying enterprise_search_agent to Agent Engine...")
    print(f"[INFO] Project : {PROJECT_ID}")
    print(f"[INFO] Location: {LOCATION}")
    print(f"[INFO] Bucket  : {STAGING_BUCKET}")

    app = AdkApp(
        agent=root_agent,
        enable_tracing=True,
    )

    remote_app = agent_engines.create(
        app,
        requirements=[
            "google-cloud-aiplatform[adk,agent_engines]",
            "google-cloud-discoveryengine",
        ],
        display_name="enterprise-search-agent",
        description="Vertex AI Search (Enterprise) エージェント - SharePoint検索対応",
        staging_bucket=STAGING_BUCKET,
    )

    print(f"\n[SUCCESS] デプロイ完了！")
    print(f"[INFO] Resource name: {remote_app.resource_name}")
    print(f"[INFO] Agent Engine ID: {remote_app.resource_name.split('/')[-1]}")
    return remote_app


# ============================================================
# デプロイ済みエージェントのテスト
# ============================================================
def test_remote(resource_name: str, query: str = "就業規則を教えて"):
    print(f"\n[INFO] Testing remote agent: {resource_name}")

    remote_app = agent_engines.get(resource_name)
    session = remote_app.create_session(user_id="test-user")

    for event in remote_app.stream_query(
        user_id="test-user",
        session_id=session["id"],
        message=query,
    ):
        if "content" in event and "parts" in event["content"]:
            for part in event["content"]["parts"]:
                if "text" in part:
                    print(part["text"])


# ============================================================
# 削除（不要になったエージェントの削除）
# ============================================================
def delete(resource_name: str):
    print(f"[INFO] Deleting agent: {resource_name}")
    remote_app = agent_engines.get(resource_name)
    remote_app.delete(force=True)
    print(f"[SUCCESS] 削除完了: {resource_name}")


# ============================================================
# エントリーポイント
# ============================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python deploy_enterprise_agent.py deploy")
        print("  python deploy_enterprise_agent.py test <resource_name>")
        print("  python deploy_enterprise_agent.py delete <resource_name>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "deploy":
        deploy()

    elif command == "test":
        if len(sys.argv) < 3:
            print("[ERROR] resource_name が必要です")
            sys.exit(1)
        test_remote(sys.argv[2])

    elif command == "delete":
        if len(sys.argv) < 3:
            print("[ERROR] resource_name が必要です")
            sys.exit(1)
        delete(sys.argv[2])

    else:
        print(f"[ERROR] 不明なコマンド: {command}")
        sys.exit(1)
