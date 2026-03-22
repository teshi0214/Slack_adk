#!/bin/bash
# ============================================================
# enterprise_search_agent デプロイスクリプト
# 使い方:
#   ./deploy_enterprise_agent.sh deploy
#   ./deploy_enterprise_agent.sh test <resource_name>
#   ./deploy_enterprise_agent.sh delete <resource_name>
# ============================================================

set -e

# ------------------------------------------------------------
# 設定
# ------------------------------------------------------------
PROJECT_ID="geminni-dev"
LOCATION="europe-west1"
STAGING_BUCKET="gs://geminni-dev-agent-staging"  # 要変更

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ------------------------------------------------------------
# カラー出力
# ------------------------------------------------------------
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

# ------------------------------------------------------------
# 使い方
# ------------------------------------------------------------
usage() {
  echo "Usage: $0 <command> [options]"
  echo ""
  echo "Commands:"
  echo "  deploy               Agent Engine へデプロイ"
  echo "  test <resource_name> デプロイ済みエージェントをテスト"
  echo "  delete <resource_name> エージェントを削除"
  echo ""
  echo "Example:"
  echo "  $0 deploy"
  echo "  $0 test projects/geminni-dev/locations/europe-west1/reasoningEngines/123456"
  echo "  $0 delete projects/geminni-dev/locations/europe-west1/reasoningEngines/123456"
  exit 1
}

# ------------------------------------------------------------
# 前提チェック
# ------------------------------------------------------------
check_prerequisites() {
  info "前提条件を確認中..."

  command -v python3 &>/dev/null || error "python3 が見つかりません"
  command -v gcloud &>/dev/null || error "gcloud CLI が見つかりません"

  # ADC 確認
  gcloud auth application-default print-access-token &>/dev/null \
    || error "ADC が設定されていません。'gcloud auth application-default login' を実行してください"

  # GCSバケット確認
  gcloud storage buckets describe "$STAGING_BUCKET" &>/dev/null \
    || {
      warn "バケット $STAGING_BUCKET が存在しないため作成します..."
      gcloud storage buckets create "$STAGING_BUCKET" \
        --project="$PROJECT_ID" \
        --location="$LOCATION"
      success "バケット作成完了: $STAGING_BUCKET"
    }

  success "前提条件チェック完了"
}

# ------------------------------------------------------------
# deploy
# ------------------------------------------------------------
cmd_deploy() {
  check_prerequisites

  info "デプロイを開始します..."
  info "Project : $PROJECT_ID"
  info "Location: $LOCATION"
  info "Bucket  : $STAGING_BUCKET"
  echo ""

  cd "$SCRIPT_DIR"

  python3 deploy_enterprise_agent.py deploy

  success "デプロイ完了！"
}

# ------------------------------------------------------------
# test
# ------------------------------------------------------------
cmd_test() {
  local resource_name="$1"
  [[ -z "$resource_name" ]] && error "resource_name が必要です"

  info "テスト実行: $resource_name"

  cd "$SCRIPT_DIR"
  python3 deploy_enterprise_agent.py test "$resource_name"
}

# ------------------------------------------------------------
# delete
# ------------------------------------------------------------
cmd_delete() {
  local resource_name="$1"
  [[ -z "$resource_name" ]] && error "resource_name が必要です"

  warn "削除しますか？: $resource_name"
  read -rp "本当に削除しますか？ (yes/no): " confirm
  [[ "$confirm" != "yes" ]] && { info "削除をキャンセルしました"; exit 0; }

  cd "$SCRIPT_DIR"
  python3 deploy_enterprise_agent.py delete "$resource_name"

  success "削除完了"
}

# ------------------------------------------------------------
# メイン処理
# ------------------------------------------------------------
[[ $# -lt 1 ]] && usage

COMMAND="$1"
shift

case "$COMMAND" in
  deploy)  cmd_deploy ;;
  test)    cmd_test "$@" ;;
  delete)  cmd_delete "$@" ;;
  *)       usage ;;
esac
