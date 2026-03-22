#!/bin/bash
# deploy_slack.sh - Slack Agent を Agent Engine にデプロイ
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  Slack Agent - Agent Engine デプロイ"
echo "========================================"

# 前提チェック
[ ! -d ".venv" ] && error "仮想環境が見つかりません"
[ ! -f "Slack_agent/agent.py" ] && error "Slack_agent/agent.py が見つかりません"
[ ! -f ".env" ] && error ".env ファイルが見つかりません"

# 環境変数読み込み
info "環境変数を読み込み中..."
set -a; source .env; set +a

[ -z "$GOOGLE_CLOUD_PROJECT" ] && error "GOOGLE_CLOUD_PROJECT が設定されていません"
[ -z "$SLACK_BOT_TOKEN" ] && error "SLACK_BOT_TOKEN が設定されていません"

info "プロジェクト: $GOOGLE_CLOUD_PROJECT"
info "リージョン  : ${GOOGLE_CLOUD_LOCATION:-us-central1}"
info "Slackトークン: ${SLACK_BOT_TOKEN:0:20}..."

# 仮想環境有効化
source .venv/bin/activate
command -v adk &> /dev/null || error "adk コマンドが見つかりません"

# デプロイ実行
echo ""
info "デプロイ開始..."
python deploy_slack.py \
    --project "$GOOGLE_CLOUD_PROJECT" \
    --region "${GOOGLE_CLOUD_LOCATION:-us-central1}" \
    "$@"

# デプロイ確認
echo ""
info "デプロイ済みエージェント一覧:"
gcloud ai reasoning-engines list \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --region="${GOOGLE_CLOUD_LOCATION:-us-central1}" \
    --format="table(name.basename(), displayName, createTime)" \
    2>/dev/null || warn "一覧取得に失敗"

echo ""
echo "========================================"
echo -e "${GREEN}完了${NC}"
echo "========================================"
