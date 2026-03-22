#!/usr/bin/env python3
"""
deploy_slack.py - Slack Agent を Agent Engine にデプロイするスクリプト

使用方法:
    python deploy_slack.py
    python deploy_slack.py --display-name "Slack Agent v1"
    python deploy_slack.py --project geminni-dev --region us-central1
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path


def get_project_id() -> str:
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID")
    if not project_id:
        try:
            result = subprocess.run(
                ["gcloud", "config", "get", "project"],
                capture_output=True, text=True, check=True
            )
            project_id = result.stdout.strip()
        except subprocess.CalledProcessError:
            pass
    return project_id


def get_project_number(project_id: str) -> str:
    try:
        result = subprocess.run(
            ["gcloud", "projects", "describe", project_id, "--format=value(projectNumber)"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ プロジェクト番号の取得に失敗: {e}")
        sys.exit(1)

def ensure_staging_bucket(project_id: str, region: str, bucket: str = None) -> str:
    """ステージングバケットを確認・作成して返す"""
    staging_bucket = bucket or f"gs://{project_id}-adk-staging"
    try:
        check = subprocess.run(
            ["gcloud", "storage", "buckets", "describe", staging_bucket],
            capture_output=True, text=True
        )
        if check.returncode != 0:
            print(f"   バケットを作成中: {staging_bucket}")
            subprocess.run(
                ["gcloud", "storage", "buckets", "create", staging_bucket,
                 f"--project={project_id}", f"--location={region}"],
                check=True
            )
            print(f"   ✅ バケット作成完了")
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  バケット作成に失敗: {e}")
    return staging_bucket


def inject_slack_token(agent_dir: str) -> bool:
    """
    SLACK_BOT_TOKEN が環境変数に設定されているか確認する。
    Agent Engine では環境変数を直接渡せないため、
    デプロイ前に .env から読み込まれていることを確認する。
    """
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("❌ SLACK_BOT_TOKEN が環境変数に設定されていません。")
        print("   .env に SLACK_BOT_TOKEN=xoxb-... を追加してください。")
        return False
    print(f"   ✅ SLACK_BOT_TOKEN を確認 ({token[:20]}...)")
    return True


def create_env_file(agent_dir: str, project_id: str, region: str) -> str:
    """
    Agent Engine 用の .env ファイルを Slack_agent/ 配下に生成して返す。
    SLACK_BOT_TOKEN など機密情報もここに書き込む。
    """
    env_path = Path(agent_dir) / ".env"
    lines = [
        "GOOGLE_GENAI_USE_VERTEXAI=1\n",
        f"GOOGLE_CLOUD_PROJECT={project_id}\n",
        f"GOOGLE_CLOUD_LOCATION={region}\n",
    ]
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if token:
        lines.append(f"SLACK_BOT_TOKEN={token}\n")
    user_token = os.environ.get("SLACK_USER_TOKEN", "")
    if user_token:
        lines.append(f"SLACK_USER_TOKEN={user_token}\n")
    # Agentspace Authorization リソースID
    auth_id = os.environ.get("SLACK_AUTH_ID", "auth-slack-agent")
    lines.append(f"SLACK_AUTH_ID={auth_id}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)

    print(f"   ✅ {env_path} を生成しました")
    return str(env_path)


def deploy_agent(project_id: str, region: str, agent_dir: str,
                 display_name: str, env_file: str) -> bool:
    cmd = [
        "adk", "deploy", "agent_engine",
        f"--project={project_id}",
        f"--region={region}",
        f"--display_name={display_name}",
        f"--env_file={env_file}",
        agent_dir,
    ]

    print(f"\n🚀 Agent Engine にデプロイ中...")
    print(f"   エージェント: {display_name}")
    print(f"   プロジェクト: {project_id}")
    print(f"   リージョン  : {region}")
    print()

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        output_lines = []
        for line in process.stdout:
            print(line, end='')
            output_lines.append(line)
        process.wait()
        output = ''.join(output_lines)

        if "Deploy failed" in output or process.returncode != 0:
            print(f"\n❌ デプロイに失敗しました")
            return False
        return True
    except Exception as e:
        print(f"❌ デプロイ中にエラー: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Slack Agent を Agent Engine にデプロイ")
    parser.add_argument("--project", "-p", help="Google Cloud プロジェクトID")
    parser.add_argument("--region", "-r", default="us-central1", help="リージョン (デフォルト: us-central1)")
    parser.add_argument("--display-name", "-n", default="Slack Agent", help="エージェント表示名")
    parser.add_argument("--agent-dir", default="./Slack_agent", help="エージェントディレクトリ")
    parser.add_argument("--skip-token-check", action="store_true", help="Slackトークン確認をスキップ")
    args = parser.parse_args()

    print("=" * 50)
    print("  Slack Agent - Agent Engine デプロイ")
    print("=" * 50)

    # .env 読み込み
    env_path = Path(".env")
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
        print("✅ .env を読み込みました")

    # プロジェクトID
    project_id = args.project or get_project_id()
    if not project_id:
        print("❌ プロジェクトIDが指定されていません")
        sys.exit(1)

    region = args.region
    print(f"\n📁 プロジェクト: {project_id}")
    print(f"📍 リージョン  : {region}")
    print(f"📂 エージェント: {args.agent_dir}")

    # エージェントディレクトリ確認
    agent_path = Path(args.agent_dir)
    if not agent_path.exists():
        print(f"❌ エージェントディレクトリが見つかりません: {args.agent_dir}")
        sys.exit(1)
    if not (agent_path / "agent.py").exists():
        print(f"❌ agent.py が見つかりません")
        sys.exit(1)

    # Slackトークン確認
    if not args.skip_token_check:
        print(f"\n🔑 Slackトークン確認中...")
        if not inject_slack_token(args.agent_dir):
            sys.exit(1)

    # ステージングバケット（不要になったが念のため残す）
    print(f"\n🪣 ステージングバケット: 不要（ADK v1.23以降は自動管理）")

    # .env ファイル生成
    print(f"\n📝 デプロイ用 .env を生成中...")
    env_file = create_env_file(args.agent_dir, project_id, region)

    # デプロイ実行
    success = deploy_agent(
        project_id=project_id,
        region=region,
        agent_dir=args.agent_dir,
        display_name=args.display_name,
        env_file=env_file,
    )

    if success:
        print("\n" + "=" * 50)
        print("✅ デプロイ完了！")
        print("=" * 50)
        print("\n確認コマンド:")
        print(f"  gcloud ai reasoning-engines list --project={project_id} --region={region}")
        print("\n⚠️  SLACK_BOT_TOKEN は Agent Engine の環境変数に設定済みです。")
        print("   トークンをローテーションした場合は再デプロイが必要です。")
    else:
        print("\n❌ デプロイに失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
