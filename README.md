# 🔍 Cisco Bug Search Analyzer

Cisco のバグ情報を検索・分析するための Web アプリケーション。機能とバージョンからマッチするバグを検索し、リリースノート情報を日本語で表示します。

## 機能

- 🔎 **バグ検索** - 機能とバージョンで検索
- 📋 **IOS バージョン選択** - ドロップダウンからバージョンを選択
- 📝 **リリースノート表示** - 日本語対応で症状・条件・回避策を表示
- 🔗 **公式ドキュメントリンク** - Cisco 公式リリースノートへの自動リンク
- 📥 **CSV アップロード** - カスタム CSV ファイルのアップロード対応
- 📤 **CSV エクスポート** - 検索結果を CSV でダウンロード

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
   - Branch: `claude/test-uaolb3` または `main`
   - Main file path: `app.py`
4. **「Deploy」** をクリック

### 3. デプロイ後
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

### 1. IOS バージョンから検索
1. **「IOS バージョンから検索」** セクションで、ドロップダウンからバージョンを選択
2. 自動的にそのバージョンのリリースノート情報が表示されます

### 2. 機能で検索
- **機能を入力**: 「Catalyst 9300」「multicast」など
- **バージョンを入力**: 「17.12.4」など
- **「🔎 バグを検索」** をクリック

### 3. 結果から詳細を確認
- テーブルから バグを選択
- 詳細情報パネルにて以下を表示：
  - リリースノート情報（日本語）
  - 症状・条件・回避策
  - Cisco 公式ドキュメントリンク

### 4. 結果をエクスポート
- **「📥 検索結果を CSV でダウンロード」** でデータをダウンロード

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
