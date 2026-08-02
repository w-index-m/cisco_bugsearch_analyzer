# 🔍 Cisco Bug Search Analyzer

Cisco のバグ情報を検索・分析するための Web アプリケーション。機能とバージョンからマッチするバグを検索し、リリースノート情報を日本語で表示します。

## 機能

- 🔎 **Cisco バグ検索** - CSV / Excel（.csv / .xls / .xlsx）をアップロードし、機能名・バージョン・Severityで検索。Nexus など Catalyst と列名が異なるエクスポートも自動認識
- 📝 **リリースノート表示** - 症状・条件・回避策を日本語（機械翻訳 または AI要約）で表示
- 🏷️ **自動分類** - バグ見出しから「利用機能」「素因」「発生しやすさ（推定）」をキーワード・ステータスから自動推定
- 🌍 **翻訳エンジン選択** - Google 翻訳 / DeepL / NVIDIA Riva から選択可能
- 🤖 **AI 分析** - Groq / Gemini / OpenRouter を使った発生可能性判定と、長いリリースノートの要約
- 🌐 **Cisco 以外のベンダー対応** - Palo Alto / YAMAHA / FortiGate 等を NVD（脆弱性データベース）でキーワード検索、または公式ページのテキストを貼り付けて既知の問題を解析
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

## Streamlit Cloud へのデプロイ

### 1. Streamlit Community Cloud アカウントを作成
https://streamlit.io/cloud にアクセスして、GitHub アカウントで新規登録

### 2. デプロイ
1. Streamlit Cloud ダッシュボードにログイン
2. **「New app」** をクリック
3. リポジトリ選択
   - Repository: `w-index-m/cisco_bugsearch_analyzer`
   - Branch: `main`
   - Main file path: `app.py`
4. **「Deploy」** をクリック

### 3. API キーの自動入力（任意）
毎回画面で手入力する代わりに、Settings → Secrets に登録しておくと自動入力されます（`.streamlit/secrets.toml.example` 参照）。
```toml
DEEPL_API_KEY = "xxx"
NVIDIA_API_KEY = "xxx"
GROQ_API_KEY = "xxx"
GEMINI_API_KEY = "xxx"
OPENROUTER_API_KEY = "xxx"
```

### 4. デプロイ後
- アプリが自動的に起動します
- URL が発行されます
- 共有可能な Web URL で利用可能に

## ファイル構成

```
.
├── app.py                 # メイン Streamlit アプリケーション
├── bugSearch.csv          # Cisco バグデータ（2,777 件）
├── requirements.txt       # Python 依存ライブラリ
├── .streamlit/
│   └── config.toml       # Streamlit 設定ファイル
└── README.md             # このファイル
```

## 使用方法

### 1. Cisco バグ検索
1. **CSV / Excel ファイルをアップロード**（.csv / .xls / .xlsx。デフォルトで読み込まれるファイルは無いため、必ずアップロードが必要）
2. **翻訳エンジン**（Google / DeepL / NVIDIA Riva）を選択
3. **「IOS バージョンから検索」** でドロップダウンからバージョンを選ぶか、**「機能を入力」「バージョンを入力」** で条件を指定して **「🔎 バグを検索」** をクリック
   - 「機能を入力」はカンマ/スペース区切りでOR検索、ダブルクォートで囲むとスペース込み1語として扱われます
   - 上部のチェックボックス（重大障害系・監視系）でよく使うキーワードを一括追加できます
4. 検索結果一覧で日本語訳された見出し・自動分類（利用機能／素因／発生しやすさ（推定））・指定バージョンへの影響有無を確認
5. 一覧からバグを選択すると、症状・条件・回避策（日本語）、AI分析、Cisco公式リリースノートへのリンクなど詳細情報を表示
6. 発生の可能性・関連機能タグ・コメントを入力して分析データとして保存可能（JSONでダウンロード/アップロードして再利用）

### 2. Cisco 以外のベンダー（Palo Alto / YAMAHA / FortiGate 等）
- **CVE検索**: キーワード（例:「PAN-OS 11.1.2」「FortiOS 7.4.8」）でNVDを検索し、深刻度（CVSS）順に一覧表示。バージョンを指定すると影響有無も判定
- **既知の問題の貼り付け解析**: Palo Alto の「Known and Addressed Issues」や YAMAHA のリリースノートなど、自動取得できない公式ページの本文をブラウザでコピーして貼り付けると、ID単位に分解してカテゴリ分け・日本語訳

### 3. EOL（サポート終了日）の調査
- **バージョン系統ごとのEOL自動取得**: endoflife.date のプロダクトスラッグ（例: `pan-os`, `fortios`, `cisco-ios-xe`）を入力して取得
- **OS名+バージョンで直接表示（貼り付け不要）**: 検証済みの Cisco IOS XE / NX-OS はOSを選んでバージョンを入力するだけで即座に表示
- **Cisco公式EOL通知の貼り付け解析**: 上記でカバーされないバージョンや Firepower/FTD/FMC 等は、Cisco公式のEOL/EOS通知ページの本文を貼り付けると IOS XE形式/NX-OS形式を自動判定して解析
- ⚠️ endoflife.date の Cisco系データは推定値の場合があるため、重要な判断の前には貼り付け解析または公式ページで必ず裏取りしてください

### 4. 結果のエクスポート
- 各セクションにその場でExcel/CSV/JSONダウンロードボタンがあります
- 画面下部の **「🗂️ 全ベンダーまとめてExcel出力」** で、その画面で実行済みの全検索結果（Cisco/CVE/貼り付け解析/EOL）を1つのExcelファイルにシート分けしてまとめてダウンロード可能

### 5. CLI から利用
Web UI を開かず、`cli.py` から同じ操作をコマンドラインで実行することもできます。詳細は下記の「CLI ツール」セクションを参照してください。

## CLI ツール

Web UI を介さず、`cli.py` から直接コマンドラインで呼び出すこともできます（他のスクリプトへのパイプや自動実行向け）。

```bash
# バグを検索して表で表示
python cli.py search --feature "Catalyst 9300" --version 17.12.4

# 検索して Excel でエクスポート
python cli.py search --feature multicast --severity 1 2 3 --format excel --output result.xlsx

# JSON で標準出力に出す（他のエージェント/スクリプトへパイプ）
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
python cli.py eol-info fortios

# OS名+バージョンで検証済みのCisco EOL情報を直接取得（貼り付け不要）
python cli.py eol-lookup cisco-ios-xe 17.17
python cli.py eol-lookup nxos 10.6

# Cisco公式EOL通知ページのテキストを貼り付けて解析（IOS XE/NX-OS自動判定）
python cli.py cisco-eol-parse --file eol_notice.txt
pbpaste | python cli.py cisco-eol-parse --format json

# Palo Alto / YAMAHA 等の「既知の問題」ページを貼り付けて解析
python cli.py parse-issues --file known_issues.txt --translate google
```

各コマンドの詳細は `python cli.py <コマンド> --help` を参照してください。

## バグデータについて

### データソース
- Cisco Bug Search: https://bst.cisco.com/bugsearch

### 含まれる情報
- **BUG Id**: バグの一意識別子
- **BUG headline**: バグのタイトル
- **Bug Status**: 修正状況（Fixed/Open など）
- **Bug Severity**: 重要度（1-5）
- **Known Affected Release(s)**: 影響を受けるバージョン
- **Known Fixed Releases**: 修正されたバージョン
- **Release Note Enclosure**: リリースノート詳細情報

### バージョン例
- 17.18.x, 17.15.x, 17.12.x
- 16.12.x, 16.10.x, 16.1.x

## 技術スタック

- **Framework**: Streamlit 1.40.0
- **Data Processing**: Pandas 2.2.3
- **Language**: Python 3.11+

## トラブルシューティング

### CSV ファイルのアップロードエラー
- ファイル形式が UTF-8 でエンコードされているか確認
- カラム名が正しいか確認

### リリースノート URL が生成されない
- Catalyst 9200/9300/9400 以外の製品の場合、URL は生成されません
- 手動で Cisco Bug Search で確認してください

## ライセンス

このプロジェクトはオープンソースです。

## 更新履歴

### v1.0.0 (2026-08-01)
- 初回リリース
- Streamlit Web UI の実装
- CSV アップロード機能
- IOS バージョン選択機能
- リリースノート日本語対応
- Cisco 公式ドキュメントリンク自動生成

## サポート

問題が発生した場合は、GitHub Issues で報告してください。

---

**Built with ❤️ using Streamlit**
