# CLAUDE.md

このリポジトリで Claude Code が作業する際の運用ルールをまとめる。

## 外部サイトへのアクセス確認は「Claude（サンドボックス）」と「GitHub」の両方で行う

このプロジェクトの開発・実行環境（Claude Code のサンドボックス）は、アウトバウンド
通信がプロキシ経由でホワイトリスト制御されており、多くの外部サイトへの通信が
`EGRESS_BLOCKED` / `403 Forbidden` としてブロックされる。実際にブロックが確認された
例:

- `services.nvd.nist.gov`（NVD API）
- `cdn.f5.com`（F5公式バグトラッカー）
- `www.cisa.gov`（CISA KEV カタログ）
- `api.first.org`（FIRST EPSS API）
- `www.cvedetails.com`

**「Claude Code のサンドボックスから到達できない」ことは、「本番環境
（GitHub Actions / Streamlit Cloud）でも到達できない」ことを意味しない。**
サンドボックスからの疎通確認だけをもって「このサイトにはアクセスできない」
「この機能は動かない」と判断・報告してはいけない。

外部サイトへの実際のアクセス可否・機能の動作確認が必要な場合は、必ず以下の
**両方**を確認すること。

1. **Claude Code サンドボックスから**（`curl` / `WebFetch` 等）
   参考程度の一次確認に留める。ここでブロックされていても、それはこの
   サンドボックス固有のネットワークポリシーによるものであり、本番環境の
   制約とは限らない。
2. **GitHub Actions から**（実際にワークフローを動かして確認する）
   `.github/workflows/collect-vendor-bugs.yml` を `workflow_dispatch` で
   手動実行し（GitHub MCP の `mcp__github__actions_run_trigger` /
   `method: run_workflow` で実行可能）、`mcp__github__get_job_logs` で
   ジョブログを確認する。GitHub-hosted runner（`ubuntu-latest`）は通常
   フルインターネットアクセスを持ち、このリポジトリのワークフローにも
   特別なネットワーク制限は設定していないため、サンドボックスでブロック
   されているサイトも GitHub Actions からは到達できることが多い。

このプロジェクトが NVD / CISA KEV / FIRST EPSS / F5公式サイト等の外部APIに
依存する機能（`analyzer.py` の各 `collect_*` / `fetch_*` 関数）を持つ理由は、
まさにこのサンドボックス制約を回避するため（GitHub Actions での事前収集 +
`data/vendor_bugs/` へのキャッシュにより、Streamlit アプリはキャッシュを
即座に表示しつつ、必要に応じてライブ検索もできるようにしている）。

今後、新しい外部サイトへの依存を追加する場合や、既存の外部API連携が
「動かない」ように見える場合も、同じ考え方で **サンドボックスでの疎通確認**
と **実際の実行環境（GitHub Actions / Streamlit Cloud）での疎通確認** の
両方を行ってから結論を出すこと。
