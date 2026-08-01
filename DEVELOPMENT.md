# Cisco Bug Search Analyzer - 開発進捗

## 📋 プロジェクト概要

**目的**: Cisco バグ情報を検索・分析する Web アプリケーション  
**フレームワーク**: Streamlit  
**デプロイ**: Streamlit Cloud（準備中）

---

## ✅ 実装済み機能

### 1️⃣ コア機能
- [x] Streamlit Web UI
- [x] CSV ファイルアップロード機能
- [x] Cisco バグデータ読み込み（2,777件）
- [x] 機能とバージョンでのバグ検索
- [x] 検索結果の CSV エクスポート

### 2️⃣ バージョン管理機能
- [x] IOS バージョン選択（ドロップダウン）
- [x] バージョン別リリースノート表示
- [x] バージョン影響バグ数の自動計算
- [x] 最大10件のバグ詳細表示

### 3️⃣ リリースノート機能
- [x] HTML タグの自動削除
- [x] リリースノートをセクション別に解析
  - 症状（Symptom）
  - 条件（Conditions）
  - 回避策（Workaround）
  - 詳細説明（Further Problem Description）
- [x] セクション名の日本語化
- [x] Cisco 公式ドキュメント URL の自動生成
  - Catalyst 9200/9300/9400 対応

### 4️⃣ 翻訳機能（🔄 進行中）

#### 実装済み
- [x] **Google Translate**
  - deep-translator ライブラリ使用
  - 無料・自動利用
  - 翻訳キャッシング機能

- [x] **DeepL API**
  - API キー入力対応
  - 高品質翻訳（日本語特化）
  - セキュアな password input
  - Streamlit Secrets 対応

#### 実装予定
- [ ] **NVIDIA Riva Translation API**
  - エンドポイント: `https://integrate.api.nvidia.com/v1/chat/completions`
  - 認証: Bearer token
  - 37言語対応
  - 無料で利用可能

### 5️⃣ UI/UX 改善
- [x] 日本語ラベル表示
  - Bug ID → Bug ID
  - Severity → 重要度
  - Status → ステータス

- [x] Headline の日本語化表示
  - 翻訳版を主表示
  - 英語原文をキャプション表示

- [x] 翻訳エンジン選択UI
  - ラジオボタンで切り替え
  - API キー入力フォーム

---

## 🔄 今後の実装

### フェーズ 1: NVIDIA Riva 統合（次）
```python
# 翻訳エンジンに追加
translation_engine = st.radio(
    "翻訳エンジン",
    ["Google", "DeepL", "NVIDIA Riva"]
)
```

**実装内容**:
- NVIDIA API 統合
- Bearer token 認証
- リクエスト/レスポンス処理
- エラーハンドリング
- キャッシング機能

### フェーズ 2: Streamlit Cloud デプロイ
```
1. GitHub にプッシュ（完了）
2. Streamlit Cloud にデプロイ
3. Secrets 管理（API キー）
4. 本番環境テスト
```

### フェーズ 3: 追加機能（検討中）
- [ ] Release Note の日本語翻訳
- [ ] PDF エクスポート機能
- [ ] メール送信機能
- [ ] ユーザー認証
- [ ] 検索履歴管理

---

## 📊 技術スタック

### フロントエンド
- **Streamlit** 1.40.0
- **Pandas** 2.2.3

### 翻訳ライブラリ
- **deep-translator** 1.11.4（Google Translate）
- **deepl** 1.17.0（DeepL API）
- **requests**（NVIDIA API 用）

### 設定・管理
- **.streamlit/config.toml** - Streamlit 設定
- **.gitignore** - Git 設定
- **requirements.txt** - 依存ライブラリ

---

## 🗂️ ディレクトリ構成

```
cisco_bugsearch_analyzer/
├── app.py                    # メイン Streamlit アプリケーション
├── bugSearch.csv             # Cisco バグデータ（2,777件）
├── requirements.txt          # Python 依存ライブラリ
├── .streamlit/
│   └── config.toml          # Streamlit 設定
├── .gitignore               # Git 設定
├── README.md                # ユーザードキュメント
└── DEVELOPMENT.md           # 開発ドキュメント（このファイル）
```

---

## 📝 Headline 翻訳フロー

### 現在の実装

```
バグ情報（CSV）
    ↓
検索実行
    ↓
翻訳エンジン選択（Google / DeepL）
    ↓
Headline を翻訳
    ↓
結果表示
  - テーブル: 日本語 Headline
  - 詳細: 日本語 + 英語原文
```

### 翻訳関数

```python
def translate_headline(text, engine='google', deepl_api_key=None):
    """
    翻訳エンジンを指定してヘッドラインを翻訳
    
    Args:
        text: 翻訳対象のテキスト
        engine: 翻訳エンジン ('google', 'deepl', 'nvidia')
        deepl_api_key: DeepL API キー
        
    Returns:
        日本語訳されたテキスト
    """
```

---

## 🔐 API キー管理

### ローカル実行
```bash
# Google Translate（自動）
streamlit run app.py

# DeepL を使用
# → UI で「DeepL」を選択 → API キーを入力
```

### Streamlit Cloud デプロイ時
```
Settings → Secrets → 以下を追加（全て任意項目、設定した分だけ画面への自動入力が有効になる）:

DEEPL_API_KEY = "your-deepl-api-key"
NVIDIA_API_KEY = "your-nvidia-api-key"
GROQ_API_KEY = "your-groq-api-key"
GEMINI_API_KEY = "your-gemini-api-key"
OPENROUTER_API_KEY = "your-openrouter-api-key"
```
テンプレートは `.streamlit/secrets.toml.example` を参照。

---

## 📊 翻訳エンジン比較表

| 項目 | Google | DeepL | NVIDIA Riva |
|------|--------|-------|-------------|
| **言語数** | 100+ | 26 | 37 |
| **翻訳品質** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **費用** | 無料 | 有料 | 無料 |
| **速度** | ⚡⚡⚡ | ⚡⚡ | ⚡⚡⚡ |
| **導入難度** | 簡単 | 普通 | 普通 |
| **キャッシング** | ✅ | ✅ | ✅ |

---

## 🚀 次のステップ

### 優先度 1: NVIDIA Riva 統合
```
1. API エンドポイント: https://integrate.api.nvidia.com/v1/chat/completions
2. 認証方式: Bearer token
3. リクエスト形式: OpenAI Chat API 互換
4. 実装予定: 本日
```

### 優先度 2: Streamlit Cloud デプロイ
```
1. API キー設定
2. Secrets 管理
3. デプロイテスト
4. 本番公開
```

### 優先度 3: ドキュメント整備
```
1. ユーザーマニュアル更新
2. API ドキュメント作成
3. トラブルシューティングガイド
```

---

## 📝 コミット履歴

| Commit | 説明 |
|--------|------|
| `ee54b31` | Implement Cisco Bug Search Analyzer with Streamlit |
| `d92501c` | Add IOS version selection and release note bug checking |
| `d771495` | Enhance release notes with Japanese localization |
| `1ce3593` | Prepare for Streamlit Cloud deployment |
| `b5186c2` | Remove redundant comments to improve code readability |
| `f86dcf5` | Add Japanese translation for bug headlines |
| `ed77cbc` | Add DeepL API support for improved Japanese translation |

---

## 🎯 デプロイ予定

### Streamlit Cloud へのデプロイ手順

```bash
# 1. GitHub に最終プッシュ
git push -u origin main

# 2. Streamlit Cloud にサインアップ
# https://streamlit.io/cloud

# 3. アプリをデプロイ
# Repository: w-index-m/cisco_bugsearch_analyzer
# Branch: main
# Main file: app.py

# 4. Secrets を設定（任意、設定した分だけ画面への自動入力が有効になる）
# Settings → Secrets
DEEPL_API_KEY = "xxx"
NVIDIA_API_KEY = "xxx"
GROQ_API_KEY = "xxx"
GEMINI_API_KEY = "xxx"
OPENROUTER_API_KEY = "xxx"
```

---

## 📞 サポート・トラブルシューティング

### Q: 翻訳が遅い
**A**: Google Translate のキャッシング機能により、初回のみ時間がかかります。その後は高速化されます。

### Q: DeepL API キーがない
**A**: https://www.deepl.com/pro?cta=header-pro から取得できます（無料版も利用可能）

### Q: NVIDIA API キーの取得方法
**A**: https://build.nvidia.com から登録して取得します

### Q: Streamlit Cloud でうまく動作しない
**A**: 
1. Secrets が正しく設定されているか確認
2. API キーの有効期限を確認
3. ネットワークプロキシの設定を確認

---

## 🔄 更新履歴

**2026-08-01**
- [x] コア機能実装
- [x] Google Translate 統合
- [x] DeepL API 統合
- [x] NVIDIA Riva API 統合予定
- [x] Streamlit Cloud デプロイ準備

---

**最終更新**: 2026-08-01  
**状態**: 開発中 🚀  
**次のマイルストーン**: NVIDIA Riva 統合 → Streamlit Cloud デプロイ
