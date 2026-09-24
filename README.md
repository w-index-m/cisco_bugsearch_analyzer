# 🔍 Cisco Bug Search Analyzer

**[🇯🇵 日本語](#日本語) | [🇬🇧 English](#english)**

Cisco / F5 / Palo Alto / FortiGate 等のネットワーク機器のバグ・脆弱性情報を検索・分析するための Web アプリケーション。
A web app for searching and triaging bug / vulnerability data for Cisco, F5, Palo Alto, and FortiGate network devices.

---

# 日本語

Cisco のバグ情報（CSV/Excel）だけでなく、F5 BIG-IP / Palo Alto (PAN-OS) / FortiGate (FortiOS) など主要ベンダーのバグ・CVE情報を NVD（米国立脆弱性データベース）やベンダー公式サイトから収集し、日本語訳・重大度・実際の悪用状況（KEV/EPSS）付きで一覧表示します。

## 機能

### Cisco バグ検索
- 🔎 **Cisco バグ検索** - CSV / Excel（.csv / .xls / .xlsx）をアップロードし、機能名・バージョン・Severityで検索。Nexus など Catalyst と列名が異なるエクスポートも自動認識
- 📝 **リリースノート表示** - 症状・条件・回避策を日本語（機械翻訳 または AI要約）で表示
- 🏷️ **自動分類** - バグ見出しから「利用機能」「素因」「発生しやすさ（推定）」をキーワード・ステータスから自動推定

### 他ベンダー（F5 / Palo Alto / FortiGate）のバグ・CVE検索
- 🔧 **F5 BIG-IP バグ検索** - NVD（CVE/CVSS）と F5公式バグトラッカー（CVEにならない一般的な既知の問題）の両方から収集。バグトラッカー側は全件一覧ページから最新のBug IDを動的に発見し、対象製品（BIG-IP Next(BNK) 等）・対象OS（バージョン）・見出しを取得
- 🔥 **Palo Alto (PAN-OS)** / 🛡️ **FortiGate (FortiOS)** バグ検索 - NVDキーワード検索（スペース区切りでOR、ダブルクォートでAND句）。対象バージョンを指定すると影響有無を判定
- ⚡ **3ベンダーまとめて検索（並列実行）** - F5 / Palo Alto / FortiGate を並列でNVD検索し、待ち時間を短縮
- 🛡️ **KEV / EPSS 表示** - CISA KEV（実際に悪用が確認された既知の脆弱性）と FIRST EPSS（悪用予測確率スコア）を各CVE行に自動付与し、CVSSだけに頼らない優先度判断が可能
- 🌐 **Shodan 露出数チェック（任意）** - `SHODAN_API_KEY` を設定すると、対象バージョンの機器が実際に何台インターネットに露出しているかをワンクリックで確認（クエリクレジットを消費しない `/shodan/host/count` を使用）
- 📦 **GitHub Actions によるキャッシュ収集** - `.github/workflows/collect-vendor-bugs.yml` が毎日自動でF5/PaloAlto/FortiGateのデータを収集し `data/vendor_bugs/` にコミット。アプリはまずこのキャッシュを即座に表示し、必要ならライブ検索も可能
- 🔍 **表の絞り込み検索ボックス** - 結果テーブルは Canvas 描画のため、ブラウザ標準のCtrl+F検索が効かない。アプリ内の専用テキストボックスでCVE ID・バージョン・見出し等を絞り込み可能

### 翻訳・AI分析
- 🌍 **翻訳エンジン選択** - Google 翻訳を既定とし、失敗時は DeepL → Groq → OpenRouter の順に自動フォールバック（Google翻訳はGitHub Actionsランナー等の共有IPからブロックされることがあるため）
- 🤖 **AI 分析** - Groq / Gemini / OpenRouter を使った発生可能性判定、長いリリースノートの要約、Excel出力への「AI解説（内容の解釈）」列自動追加

### その他
- 📅 **EOL（サポート終了日）調査** - endoflife.date からの自動取得、検証済み Cisco データ（IOS XE / NX-OS）をOS名+バージョン入力だけで直接表示、Cisco公式EOL通知の貼り付け解析の3通りに対応
- 📊 **進捗バー表示** - 翻訳・解析処理の進捗をリアルタイム表示
- 💾 **分析データの保存/読込** - バグごとの評価・タグ・コメントをJSONで保存し再利用可能
- 📤 **柔軟なエクスポート** - CSV / Excel / JSON、ベンダー横断でシート分けした統合Excel出力に対応
- 💻 **CLI ツール** - Web UI を介さず `cli.py` からコマンドラインで同等の操作が可能

## セットアップ

### ローカル実行

```bash
# リポジトリをクローン
git clone https://github.com/w-index-m/cisco_bugsearch_analyzer.git
cd cisco_bugsearch_analyzer

# 依存ライブラリをインストール
pip install -r requirements.txt

# Streamlit アプリを実行
streamlit run app.py
```

ブラウザで `http://localhost:8501` を開いてください。

### Streamlit Cloud へのデプロイ

1. https://streamlit.io/cloud にアクセスして、GitHub アカウントで新規登録
2. Streamlit Cloud ダッシュボードで **「New app」** をクリック
   - Repository: `w-index-m/cisco_bugsearch_analyzer`
   - Branch: `main`
   - Main file path: `app.py`
3. **「Deploy」** をクリック

#### API キーの自動入力（任意）

毎回画面で手入力する代わりに、Settings → Secrets に登録しておくと自動入力されます（`.streamlit/secrets.toml.example` 参照）。全て任意項目で、設定した分だけ画面への自動入力が有効になります。

```toml
DEEPL_API_KEY = "xxx"
NVIDIA_API_KEY = "xxx"
GROQ_API_KEY = "xxx"
GEMINI_API_KEY = "xxx"
OPENROUTER_API_KEY = "xxx"
NVD_API_KEY = "xxx"
SHODAN_API_KEY = "xxx"
```

> **Streamlit Secrets と GitHub Actions Secrets は別物です。** ライブ検索（アプリ画面からの検索）には Streamlit Secrets、`.github/workflows/collect-vendor-bugs.yml` の自動収集には GitHub リポジトリの Secrets（Settings → Secrets and variables → Actions）が必要です。同じキーでも両方に登録してください。

## ファイル構成

```
.
├── app.py                          # メイン Streamlit アプリケーション
├── analyzer.py                     # 検索・翻訳・NVD/KEV/EPSS/Shodan連携などのコアロジック
├── cli.py                          # コマンドラインツール
├── f5_bigip_tmm_bugs.py            # F5 BIG-IP バグ検索の単体CLI
├── bugSearch.csv                   # Cisco バグデータ（サンプル）
├── data/vendor_bugs/               # GitHub Actionsが自動収集したF5/PaloAlto/FortiGateのキャッシュ(JSON)
├── scripts/
│   ├── collect_vendor_bug_cache.py # data/vendor_bugs/ を生成する収集スクリプト
│   └── check_api_keys.py           # NVD/DeepL/Groq/OpenRouterの疎通を短時間で診断
├── .github/workflows/
│   └── collect-vendor-bugs.yml     # 毎日自動でバグ/CVEキャッシュを収集・コミットするワークフロー
├── .streamlit/
│   ├── config.toml                 # Streamlit 設定ファイル
│   └── secrets.toml.example        # Secretsのテンプレート
├── CLAUDE.md                       # 開発運用ルール（外部サイト疎通確認の方針等）
├── requirements.txt                # Python 依存ライブラリ
└── README.md                       # このファイル
```

## 使用方法

### 1. Cisco バグ検索
1. **CSV / Excel ファイルをアップロード**（.csv / .xls / .xlsx。デフォルトで読み込まれるファイルは無いため、必ずアップロードが必要）
2. **翻訳エンジン**（Google / DeepL / NVIDIA Riva 等）を選択
3. **「IOS バージョンから検索」** でドロップダウンからバージョンを選ぶか、**「機能を入力」「バージョンを入力」** で条件を指定して **「🔎 バグを検索」** をクリック
   - 「機能を入力」はカンマ/スペース区切りでOR検索、ダブルクォートで囲むとスペース込み1語として扱われます
   - 上部のチェックボックス（重大障害系・インターフェース/L2/L3系・監視系）で下記のおすすめキーワードを一括追加できます
4. 検索結果一覧で日本語訳された見出し・自動分類・指定バージョンへの影響有無を確認
5. 一覧からバグを選択すると、症状・条件・回避策（日本語）、AI分析、Cisco公式リリースノートへのリンクなど詳細情報を表示
6. 発生の可能性・関連機能タグ・コメントを入力して分析データとして保存可能（JSONでダウンロード/アップロードして再利用）

#### デフォルトおすすめキーワード
- **重大障害系**: reload, reboot, crash, traceback, dump, leak, stuck, stop, remove, down, hung, deadlock, watchdog
- **インターフェース/L2/L3系**: 1gbps, 1G, ethernet, 10gbps, 10G, fiber, speed, duplex, lacp, vlan, 802.1q, trunk, ipv4, svi, flowcontrol, mac aging-time, static-route, vrf, access-list 等
- **監視系**: snmp, read, write, trap, syslog, ntp, ssh, netflow, cdp, span, issu

### 2. F5 BIG-IP / Palo Alto (PAN-OS) / FortiGate (FortiOS) のバグ・CVE検索
- 各セクションはまず **GitHub Actionsが毎日収集したキャッシュ**（`data/vendor_bugs/`）を即座に表示します
- **NVD検索キーワード**を指定して **「🔎 検索」** を押すと、キャッシュとは別にその場でライブ検索できます（スペース区切りでOR検索、ダブルクォートで囲むとAND句）
- 対象バージョンを入力すると、NVDのバージョン範囲データから影響有無を判定
- 結果テーブルには CVSS 由来の重大度に加え、**KEV**（実際に悪用が確認された既知の脆弱性）・**EPSS**（悪用予測確率スコア）が自動付与されます
- **F5のみ**: NVD検索に加え、F5公式バグトラッカー（CVEにならない一般的な既知の問題）から対象製品（BIG-IP Next(BNK)等）・対象OS・見出しも収集
- `SHODAN_API_KEY` を設定していれば、**「🌐 Shodanでインターネット露出数を確認」** ボタンで対象バージョンの機器が実際に何台露出しているかを確認可能
- 表の上部にある **「🔍 この表をキーワードで絞り込み」** ボックスでCVE ID・バージョン・見出し等を絞り込み表示（ブラウザ標準のCtrl+Fは表内を検索できないため）
- **「🚀 3ベンダーをまとめて検索（並列実行）」** で3ベンダーのライブ検索を同時実行可能

### 3. その他ベンダー（YAMAHA等）の既知の問題を貼り付けて解析
- Palo Alto の「Known and Addressed Issues」や YAMAHA のリリースノートなど、自動取得できない公式ページの本文をブラウザでコピーして貼り付けると、項目単位に分解してカテゴリ分け・日本語訳
- **テキストを翻訳（単体ツール）**: バグ検索とは独立して、任意の文章を一時的に日本語訳したい場合に使える汎用の翻訳ボックス

### 4. EOL（サポート終了日）の調査
- **バージョン系統ごとのEOL自動取得**: endoflife.date のプロダクトスラッグ（例: `pan-os`, `fortios`, `cisco-ios-xe`）を入力して取得
- **OS名+バージョンで直接表示（貼り付け不要）**: 検証済みの Cisco IOS XE / NX-OS はOSを選んでバージョンを入力するだけで即座に表示
- **Cisco公式EOL通知の貼り付け解析**: 上記でカバーされないバージョンや Firepower/FTD/FMC 等は、Cisco公式のEOL/EOS通知ページの本文を貼り付けると自動判定して解析
- ⚠️ endoflife.date の Cisco系データは推定値の場合があるため、重要な判断の前には貼り付け解析または公式ページで必ず裏取りしてください

### 5. 結果のエクスポート
- 各セクションにその場でExcel/CSV/JSONダウンロードボタンがあります
- 画面下部の **「🗂️ 全ベンダーまとめてExcel出力」** で、その画面で実行済みの全検索結果を1つのExcelファイルにシート分けしてまとめてダウンロード可能

### 6. CLI から利用

```bash
# Cisco バグを検索して表で表示
python cli.py search --feature "Catalyst 9300" --version 17.12.4
python cli.py search --feature multicast --severity 1 2 3 --format excel --output result.xlsx
python cli.py search --version 17.12.4 --format json

# 見出しを翻訳するだけ
python cli.py translate "Device may reload unexpectedly"

# 利用可能な IOS バージョン一覧
python cli.py versions

# Cisco 以外のベンダー（Palo Alto / YAMAHA / FortiGate 等）は NVD をキーワード検索
python cli.py cve-search "PAN-OS 11.1.2"
python cli.py cve-search "FortiOS 7.4.8" --format json

# バージョン系統ごとのEOL（サポート終了日）と関連リンクを取得
python cli.py eol-info pan-os
python cli.py eol-lookup cisco-ios-xe 17.17

# Cisco公式EOL通知ページのテキストを貼り付けて解析
python cli.py cisco-eol-parse --file eol_notice.txt

# Palo Alto / YAMAHA 等の「既知の問題」ページを貼り付けて解析
python cli.py parse-issues --file known_issues.txt --translate google

# F5 BIG-IP バグ検索の単体CLI（バグトラッカー全件一覧から動的にBug IDを発見）
python f5_bigip_tmm_bugs.py --nvd-keyword "BIG-IP" --bugtracker-limit 100
```

各コマンドの詳細は `python cli.py <コマンド> --help` を参照してください。

## GitHub Actions によるバグ/CVEキャッシュの自動収集

`analyzer.py` は NVD・F5公式サイト・CISA KEV・FIRST EPSS 等の外部APIに依存していますが、開発環境（サンドボックス）からはこれらの多くがネットワークポリシーでブロックされます。そのため `.github/workflows/collect-vendor-bugs.yml` が **毎日 09:00 JST（cron）または手動実行（workflow_dispatch）** で以下を行います。

1. `scripts/check_api_keys.py` で NVD/DeepL/Groq/OpenRouterの各APIキーが実際に機能するか数秒〜十数秒で診断（診断のみ、失敗してもジョブは継続）
2. `scripts/collect_vendor_bug_cache.py` で F5 BIG-IP / Palo Alto (PAN-OS) / FortiGate (FortiOS) のバグ・CVE情報を収集し、`data/vendor_bugs/*.json` として保存
3. 変更があればリポジトリに自動コミット・push（push競合時はrebaseして自動リトライ）

これにより、Streamlit アプリはまずキャッシュを即座に表示しつつ、必要に応じてライブ検索もできます。このワークフローを実際に使うには、GitHubリポジトリの **Settings → Secrets and variables → Actions** に `NVD_API_KEY` / `DEEPL_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` を登録してください（Streamlit Secretsとは別管理です）。

## バグデータについて

### データソース
- Cisco Bug Search: https://bst.cisco.com/bugsearch（CSV/Excelエクスポートをアップロード）
- NVD（米国立脆弱性データベース）: F5/Palo Alto/FortiGate等のCVE情報
- F5公式バグトラッカー: https://cdn.f5.com/product/bugtracker/（CVEにならない一般的な既知の問題）
- CISA KEV / FIRST EPSS: 実際の悪用状況・悪用予測確率
- endoflife.date: サポート終了日（EOL）情報

### Ciscoデータに含まれる情報
- **BUG Id**: バグの一意識別子
- **BUG headline**: バグのタイトル
- **Bug Status**: 修正状況（Fixed/Open など）
- **Bug Severity**: 重要度（1-5）
- **Known Affected Release(s)**: 影響を受けるバージョン
- **Known Fixed Releases**: 修正されたバージョン
- **Release Note Enclosure**: リリースノート詳細情報

## 技術スタック

- **Framework**: Streamlit 1.40+
- **Data Processing**: Pandas 2.2+
- **翻訳**: deep-translator (Google) / deepl / Groq / OpenRouter
- **AI分析**: Groq / Gemini / OpenRouter
- **外部データ**: NVD REST API v2.0 / CISA KEV / FIRST EPSS / Shodan API
- **Language**: Python 3.11+

## トラブルシューティング

### CSV ファイルのアップロードエラー
- ファイル形式が UTF-8 でエンコードされているか確認
- カラム名が正しいか確認

### リリースノート URL が生成されない
- Catalyst 9200/9300/9400 以外の製品の場合、URL は生成されません
- 手動で Cisco Bug Search で確認してください

### 見出しが日本語訳されない
- Google翻訳は共有IP（GitHub Actionsランナー等）からボット対策でブロックされることがあります
- DeepL / Groq / OpenRouter のいずれかのAPIキーを設定すると自動フォールバックします
- `scripts/check_api_keys.py`（GitHub Actions内で自動実行）でキーの有効性を確認できます

### 「NVD/F5/CISA等の外部サイトに接続できない」と表示される
- 開発環境（サンドボックス）は外部通信がプロキシで制限されており、多くの外部サイトへの接続がブロックされます
- これは本番環境（GitHub Actions / Streamlit Cloud）の制約とは限りません。詳細は `CLAUDE.md` を参照してください

## ライセンス

このプロジェクトはオープンソースです。

## サポート

問題が発生した場合は、[GitHub Issues](https://github.com/w-index-m/cisco_bugsearch_analyzer/issues) で報告してください。

---

# English

**Cisco Bug Search Analyzer** is a Streamlit web app for searching and triaging bugs and vulnerabilities across Cisco and several other network vendors (F5, Palo Alto Networks, Fortinet). It combines a user-supplied Cisco bug export with live vendor/CVE data pulled from NVD and official trackers, adds Japanese machine translation, and enriches CVE results with real-world exploitation signals (CISA KEV, FIRST EPSS) and optional internet-exposure counts (Shodan).

## Features

**Cisco bug search**
- Upload a Cisco Bug Search CSV/Excel export and search by feature keyword, affected version, and severity (auto-detects both Catalyst- and Nexus-style column layouts)
- Release notes are parsed into Symptom / Conditions / Workaround sections and translated to Japanese (or summarized with AI)
- Automatic tagging of "affected feature", "root cause hint", and "estimated likelihood" from headline keywords and status

**Other vendors (F5 BIG-IP / Palo Alto PAN-OS / FortiGate FortiOS)**
- Dedicated search sections that query the NVD (National Vulnerability Database) by keyword (space-separated terms are OR'd; quote a phrase for AND/exact matching), plus F5's official bug tracker for non-CVE known issues (F5's tracker index is crawled dynamically to discover recent Bug IDs, and affected product info such as "BIG-IP Next (BNK)" is captured)
- Every CVE result is enriched with **CVSS**, **CISA KEV** (confirmed real-world exploitation) and **FIRST EPSS** (predicted exploitation probability) so you're not relying on CVSS alone
- Optional **Shodan exposure check**: with a `SHODAN_API_KEY` configured, one click shows how many internet-facing devices match the target version, using Shodan's credit-free `/shodan/host/count` endpoint
- **Parallel combined search** across all three vendors, and an **in-table filter box** (the results table is Canvas-rendered, so browser-native Ctrl+F can't search it — use the app's own search box instead)
- A daily **GitHub Actions job** pre-collects F5/Palo Alto/FortiGate data into `data/vendor_bugs/*.json` so the app can display results instantly even before you run a live search

**Translation & AI analysis**
- Translation engine chain: Google Translate by default, automatically falling back to DeepL → Groq → OpenRouter if Google Translate is blocked (this happens on shared IPs such as GitHub Actions runners)
- Optional AI-assisted likelihood assessment and long release-note summarization via Groq / Gemini / OpenRouter, including an auto-generated "AI interpretation" column in Excel exports

**Other**
- End-of-life (EOL) lookup via endoflife.date, verified built-in data for Cisco IOS XE / NX-OS, and a paste-and-parse mode for official Cisco EOL notices
- Save/load per-bug analysis (assessment, tags, comments) as JSON
- Export to CSV / Excel / JSON, including a combined multi-sheet Excel export across all vendors
- A CLI (`cli.py`) mirrors most app functionality for scripting/automation

## Setup

### Run locally

```bash
git clone https://github.com/w-index-m/cisco_bugsearch_analyzer.git
cd cisco_bugsearch_analyzer
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### Deploy to Streamlit Community Cloud

1. Sign up at https://streamlit.io/cloud with your GitHub account
2. Click **"New app"**, select `w-index-m/cisco_bugsearch_analyzer`, branch `main`, main file `app.py`, then **"Deploy"**
3. (Optional) Add API keys under Settings → Secrets so they auto-fill instead of being typed in the UI each time — see `.streamlit/secrets.toml.example`:

```toml
DEEPL_API_KEY = "xxx"
NVIDIA_API_KEY = "xxx"
GROQ_API_KEY = "xxx"
GEMINI_API_KEY = "xxx"
OPENROUTER_API_KEY = "xxx"
NVD_API_KEY = "xxx"
SHODAN_API_KEY = "xxx"
```

> **Streamlit Secrets and GitHub Actions Secrets are separate stores.** The live app reads from Streamlit Secrets; the scheduled collection workflow (`.github/workflows/collect-vendor-bugs.yml`) reads from the GitHub repository's Actions secrets (Settings → Secrets and variables → Actions). Add the same keys to both if you want both to work.

## Automated data collection (GitHub Actions)

Because the vendor/CVE data sources (NVD, F5's site, CISA, FIRST) are frequently unreachable from restricted sandboxes, a scheduled workflow (`.github/workflows/collect-vendor-bugs.yml`, daily at 00:00 UTC / 09:00 JST, or manually via `workflow_dispatch`) runs on a GitHub-hosted runner (unrestricted network) to:

1. Run `scripts/check_api_keys.py` — a fast (seconds) connectivity check for the NVD/DeepL/Groq/OpenRouter API keys, diagnostic-only (never fails the job)
2. Run `scripts/collect_vendor_bug_cache.py` to fetch F5 BIG-IP / Palo Alto (PAN-OS) / FortiGate (FortiOS) bug and CVE data, writing `data/vendor_bugs/*.json`
3. Commit and push any changes (retrying with a rebase loop if the push is rejected by a concurrent commit)

The Streamlit app reads this cache first for instant results, and can still run a live search on demand.

## Tech stack

- **Framework**: Streamlit 1.40+
- **Data**: Pandas 2.2+
- **Translation**: deep-translator (Google), DeepL, Groq, OpenRouter
- **AI analysis**: Groq / Gemini / OpenRouter
- **External data**: NVD REST API v2.0, CISA KEV, FIRST EPSS, Shodan API
- **Language**: Python 3.11+

## Troubleshooting

- **Headlines aren't translated to Japanese**: Google Translate is sometimes blocked from shared IPs (e.g. GitHub Actions runners). Configure a DeepL, Groq, or OpenRouter API key to enable automatic fallback; `scripts/check_api_keys.py` (run automatically in the collection workflow) diagnoses this in seconds.
- **"Can't reach NVD/F5/CISA"**: the development sandbox's outbound network is restricted and blocks many external sites — this does not necessarily mean production (GitHub Actions / Streamlit Cloud) is affected. See `CLAUDE.md`.

## License

This project is open source.

## Support

Please report issues via [GitHub Issues](https://github.com/w-index-m/cisco_bugsearch_analyzer/issues).

---

**Built with ❤️ using Streamlit**
