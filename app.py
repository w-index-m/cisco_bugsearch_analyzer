import streamlit as st
import pandas as pd
import json
from datetime import datetime

import analyzer
from analyzer import (
    clean_html_tags,
    parse_release_note,
    get_cisco_release_notes_url,
    translate_headline,
    save_analysis_to_json,
    assess_bug_possibility,
    create_excel_report,
    search_bugs,
    list_affected_releases,
    version_affects_bug,
    DEEPL_AVAILABLE,
)

st.set_page_config(page_title="Cisco Bug Search Analyzer", layout="wide")

# 「機能を入力」欄にチェックボックスでまとめて追記できる用語カテゴリ。
# 増やす場合はここに 1 行追加するだけでチェックボックスも増える
FEATURE_KEYWORD_CATEGORIES = {
    "重大障害系": ["leak", "panic", "crash", "exception", "reboot", "reload", "memory",
              "cpu", "cam", "tcam", "static route", "snmp", "syslog", "snmppolling",
              "stack", "traceback", "iosd", "linu", "cause", "core", "dump"],
    "監視系": ["syslog", "snmp", "snmp polling", "snmp trap", "netflow"],
}


def _rebuild_feature_keywords():
    """チェックされているカテゴリの用語をすべて集めて「機能を入力」欄を再構成する"""
    terms = []
    for cat, keywords in FEATURE_KEYWORD_CATEGORIES.items():
        if st.session_state.get(f"feature_cat_{cat}"):
            terms.extend(keywords)
    st.session_state["feature"] = ", ".join(terms)


if "feature" not in st.session_state:
    st.session_state["feature_cat_重大障害系"] = True
    _rebuild_feature_keywords()

st.title("🔍 Cisco Bug Search Analyzer")
st.markdown("Cisco バグ検索システム - 機能とバージョンから該当するバグを検索")


def get_secret(key):
    """Streamlit Cloud の Settings → Secrets から API キーを取得（未設定なら None）"""
    try:
        return st.secrets.get(key)
    except Exception:
        return None


def load_analysis_from_json_ui(json_str):
    """JSON から分析結果を読み込み。失敗時は画面にエラー表示"""
    try:
        json.loads(json_str)
    except Exception as e:
        st.error(f"JSON 読み込みエラー: {e}")
        return {}
    return analyzer.load_analysis_from_json(json_str)


# ファイルアップロード（必須。デフォルトのバグ一覧は読み込まない）
uploaded_file = st.file_uploader(
    "CSV / Excel ファイルをアップロード",
    type=["csv", "xls", "xlsx"],
    help="Nexus 等、Catalyst と列名が異なるエクスポートも自動で列名を認識します"
)

if uploaded_file is not None:
    try:
        filename = uploaded_file.name.lower()
        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip()
        df = analyzer.normalize_bug_columns(df)
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
        df = None
else:
    df = None

if df is not None:
    st.success(f"✓ {len(df)} 件のバグ情報を読み込みました")

    if "bug_analysis" not in st.session_state:
        st.session_state.bug_analysis = {}

    st.markdown("---")

    with st.expander("💾 分析データの管理"):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**分析データをアップロード**")
            uploaded_json = st.file_uploader(
                "JSON ファイルを選択",
                type=["json"],
                key="analysis_uploader"
            )
            if uploaded_json is not None:
                json_content = uploaded_json.read().decode('utf-8')
                loaded_analysis = load_analysis_from_json_ui(json_content)
                if loaded_analysis:
                    st.session_state.bug_analysis.update(loaded_analysis)
                    st.success(f"✓ {len(loaded_analysis)} 件の分析データを読み込みました")

        with col2:
            st.write("**分析データをダウンロード**")
            analysis_json = save_analysis_to_json(st.session_state.bug_analysis)
            st.download_button(
                label="📥 分析結果を JSON でダウンロード",
                data=analysis_json,
                file_name=f"bug_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col2:
        st.subheader("翻訳設定 & Severity")
        st.markdown("**翻訳エンジン**")
        translation_engine = st.radio(
            "翻訳エンジン",
            ["Google", "DeepL", "NVIDIA Riva"],
            horizontal=False,
            index=0,
            label_visibility="collapsed"
        )

        deepl_api_key = None
        nvidia_api_key = None

        if translation_engine == "DeepL":
            if DEEPL_AVAILABLE:
                deepl_secret = get_secret("DEEPL_API_KEY")
                if deepl_secret:
                    st.caption("✓ Secrets から読み込み済み")
                    deepl_api_key = deepl_secret
                else:
                    deepl_api_key = st.text_input(
                        "DeepL API キー", type="password", placeholder="API キーを入力"
                    )
                if not deepl_api_key:
                    st.warning("DeepL API キーを入力してください")
            else:
                st.warning("deepl ライブラリがインストールされていません")
                translation_engine = "Google"

        elif translation_engine == "NVIDIA Riva":
            nvidia_secret = get_secret("NVIDIA_API_KEY")
            if nvidia_secret:
                st.caption("✓ Secrets から読み込み済み")
                nvidia_api_key = nvidia_secret
            else:
                nvidia_api_key = st.text_input(
                    "NVIDIA API キー", type="password", placeholder="API キーを入力"
                )
            if not nvidia_api_key:
                st.warning("NVIDIA API キーを入力してください")

        # 表示ラベル（"Google"/"DeepL"/"NVIDIA Riva"）を translate_headline() が期待する
        # 内部キー（'google'/'deepl'/'nvidia'）に変換する
        engine_key_map = {"Google": "google", "DeepL": "deepl", "NVIDIA Riva": "nvidia"}
        translation_engine_key = engine_key_map.get(translation_engine, "google")

        st.markdown("**Severity フィルタ**")
        severity_filter = st.multiselect(
            "Severity を選択",
            options=[1, 2, 3, 4, 5],
            default=[1, 2, 3],
            label_visibility="collapsed"
        )

        st.markdown("**AI 分析エンジン**")
        use_ai_analysis = st.checkbox("AI による可能性判定を使用", value=False)

        groq_api_key = None
        gemini_api_key = None
        open_router_api_key = None

        if use_ai_analysis:
            groq_secret = get_secret("GROQ_API_KEY")
            gemini_secret = get_secret("GEMINI_API_KEY")
            open_router_secret = get_secret("OPENROUTER_API_KEY")

            if not (groq_secret and gemini_secret and open_router_secret):
                st.markdown("API キーを入力（持っているもののみ）:")

            if groq_secret:
                st.caption("✓ Groq: Secrets から読み込み済み")
                groq_api_key = groq_secret
            else:
                groq_api_key = st.text_input(
                    "Groq API キー", type="password", placeholder="gsk_...",
                    label_visibility="collapsed"
                )

            if gemini_secret:
                st.caption("✓ Gemini: Secrets から読み込み済み")
                gemini_api_key = gemini_secret
            else:
                gemini_api_key = st.text_input(
                    "Gemini API キー", type="password", placeholder="AIza...",
                    label_visibility="collapsed"
                )

            if open_router_secret:
                st.caption("✓ Open Router: Secrets から読み込み済み")
                open_router_api_key = open_router_secret
            else:
                open_router_api_key = st.text_input(
                    "Open Router キー", type="password", placeholder="sk-or-...",
                    label_visibility="collapsed"
                )

    st.markdown("---")
    st.subheader("IOS バージョンから検索")

    sorted_releases = list_affected_releases(df)

    selected_ios_version = st.selectbox(
        "IOS バージョンを選択",
        [""] + sorted_releases,
        format_func=lambda x: "バージョンを選択..." if x == "" else x
    )

    st.markdown("---")

    st.caption("キーワードを一括追加:")
    cat_cols = st.columns(len(FEATURE_KEYWORD_CATEGORIES))
    for cat_col, cat in zip(cat_cols, FEATURE_KEYWORD_CATEGORIES):
        with cat_col:
            st.checkbox(
                cat,
                key=f"feature_cat_{cat}",
                on_change=_rebuild_feature_keywords,
                help=", ".join(FEATURE_KEYWORD_CATEGORIES[cat]),
            )

    col1, col2 = st.columns(2)

    with col1:
        feature = st.text_input(
            "機能を入力（Product / Headline）",
            key="feature",
            placeholder='例：VPN Multicast BGP、または "Catalyst 9300" VPN',
            help="カンマまたはスペース（全角/半角）区切りで複数キーワードを指定するとOR検索になります。"
                 "スペースを含む語をそのまま1語で検索したい場合はダブルクォートで囲んでください"
                 "（例: '\"Catalyst 9300\" VPN' なら Catalyst 9300 を1語として、VPNを別語としてOR検索）。"
                 "上のチェックボックスでカテゴリ用語を一括追加できます（手入力した内容は消えます）。"
        )

    with col2:
        version = st.text_input(
            "バージョンを入力（Known Affected Release）",
            placeholder="例：17.12.4, 17.15.2, etc."
        )

    search_button = st.button("🔎 バグを検索", type="primary")
    if search_button:
        st.session_state["has_run_search"] = True

    st.markdown("---")

    if selected_ios_version:
        st.info(f"📋 **IOS {selected_ios_version} のリリースノート情報**")

        ios_mask = df.apply(
            lambda row: version_affects_bug(
                row["Known Affected Release(s)"], row.get("Known Fixed Releases"), selected_ios_version
            ),
            axis=1,
        )
        ios_bugs = df[ios_mask].copy()

        if len(ios_bugs) > 0:
            st.write(f"**このバージョンに影響するバグ: {len(ios_bugs)} 件**")
            st.caption(
                "⚠️ 旧バージョンから未修正のまま続いている推測分を含みます。"
                "中間バージョンで実際に発生するとは限りません。"
            )

            with st.expander("🔍 このバージョンのリリースノート内のバグ情報"):
                for idx, bug in ios_bugs.head(10).iterrows():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**{bug['BUG Id']}** - {bug['BUG headline'][:60]}")
                    with col2:
                        severity = bug['Bug Severity']
                        st.write(f"Severity: {severity}")
                    with col3:
                        st.write(f"Status: {bug['Bug Status']}")

                if len(ios_bugs) > 10:
                    st.caption(f"... 他 {len(ios_bugs) - 10} 件")
        else:
            st.write("このバージョンのバグ情報がありません")

        st.markdown("---")

    if st.session_state.get("has_run_search", False):
        sort_by_ui = st.selectbox(
            "ソート順",
            ["Bug Severity (高い順)", "Last Modified (新しい順)", "Bug ID"]
        )
        sort_by_map = {
            "Bug Severity (高い順)": "severity",
            "Last Modified (新しい順)": "last_modified",
            "Bug ID": "bug_id",
        }

        results = search_bugs(
            df,
            feature=feature,
            version=version,
            severity=severity_filter,
            ios_version=selected_ios_version,
            sort_by=sort_by_map[sort_by_ui],
        )

        st.subheader(f"検索結果: {len(results)} 件")

        if version or selected_ios_version:
            st.caption(
                "⚠️ バージョン検索は「これ以前のバージョンから影響していて、まだ修正版が"
                "出ていない」バグも推測で含めています。中間バージョン（例: 17.15.2 のみ"
                "記載されている場合の 17.15.4 など）で実際に発生するとは限らないため、"
                "重要な判断の前に各バグページで実際の影響バージョンを確認してください。"
            )

        if len(results) > 0:
            _default_show_notes = len(results) <= 15
            show_release_note_cols = st.checkbox(
                f"「症状/回避策/詳細説明」の日本語訳（またはAI要約）をこの一覧に表示する"
                f"（{len(results)} 件 - バグ1件につき翻訳APIを最大3回呼ぶため、件数が多いと数分かかることがあります）",
                value=_default_show_notes,
                key="show_release_note_cols"
            )

            display_results = results.copy()
            total_rows = len(display_results)

            def _translate_or_summarize_ja(text):
                if not text:
                    return ""
                if use_ai_analysis and (groq_api_key or gemini_api_key or open_router_api_key):
                    summary = analyzer.summarize_technical_text_ja(
                        text, groq_key=groq_api_key, gemini_key=gemini_api_key,
                        open_router_key=open_router_api_key
                    )
                    if summary:
                        return summary
                return translate_headline(
                    text, engine=translation_engine_key,
                    deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key
                )

            def _extract_ja_release_note_fields(note):
                if pd.isna(note):
                    note = ""
                sections = parse_release_note(note)
                symptom_ja = _translate_or_summarize_ja(sections.get("症状", ""))
                workaround_ja = _translate_or_summarize_ja(sections.get("回避策", ""))
                detail_ja = _translate_or_summarize_ja(sections.get("詳細説明", ""))
                return pd.Series({
                    "症状 (日本語)": symptom_ja,
                    "回避策 (日本語)": workaround_ja,
                    "詳細説明 (日本語)": detail_ja,
                })

            # 見出しの翻訳（バグ1件につき翻訳API 1回）: 進捗バー付きで1件ずつ処理する
            progress_bar = st.progress(0.0, text=f"見出しを翻訳中... (0/{total_rows})")
            headlines_ja = []
            for i, headline in enumerate(display_results["BUG headline"], 1):
                headlines_ja.append(translate_headline(
                    headline, engine=translation_engine_key,
                    deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key
                ))
                progress_bar.progress(i / total_rows, text=f"見出しを翻訳中... ({i}/{total_rows})")
            progress_bar.empty()

            display_results["BUG headline (日本語)"] = headlines_ja
            display_results["BUG headline (英語原文)"] = display_results["BUG headline"]
            display_results["発生可能性"] = display_results["BUG Id"].apply(
                lambda x: st.session_state.bug_analysis.get(x, {}).get("possibility", "-")
            )

            if show_release_note_cols:
                # 症状/回避策/詳細説明の翻訳（バグ1件につき翻訳API 最大3回）: こちらも進捗バー付き
                progress_bar2 = st.progress(0.0, text=f"症状/回避策/詳細説明を翻訳中... (0/{total_rows})")
                release_note_rows = []
                for i, note in enumerate(display_results["Release Note Enclosure"], 1):
                    release_note_rows.append(_extract_ja_release_note_fields(note))
                    progress_bar2.progress(i / total_rows, text=f"症状/回避策/詳細説明を翻訳中... ({i}/{total_rows})")
                progress_bar2.empty()

                display_results = pd.concat(
                    [display_results.reset_index(drop=True), pd.DataFrame(release_note_rows).reset_index(drop=True)],
                    axis=1
                )
                display_results.index = results.index
            else:
                display_results["症状 (日本語)"] = ""
                display_results["回避策 (日本語)"] = ""
                display_results["詳細説明 (日本語)"] = ""

            display_results["利用機能"] = display_results["BUG headline"].apply(analyzer.classify_bug_feature)
            display_results["素因"] = display_results["BUG headline"].apply(analyzer.classify_bug_symptom)

            # 指定バージョンへの影響有無（IOSバージョン選択 or バージョン入力のいずれか）を
            # 「発生しやすさ」推定の補足情報として使う
            _impact_target = selected_ios_version or version or None
            if _impact_target:
                display_results["_target_affected"] = display_results.apply(
                    lambda row: version_affects_bug(
                        row["Known Affected Release(s)"], row.get("Known Fixed Releases"), _impact_target
                    ), axis=1
                )
                impact_col_name = f"{_impact_target}影響"
                display_results[impact_col_name] = display_results["_target_affected"].map(
                    {True: "影響あり", False: "対象外"}
                )
            else:
                impact_col_name = None

            display_results["発生しやすさ (推定)"] = display_results.apply(
                lambda row: analyzer.estimate_occurrence_likelihood(
                    row["Bug Status"], row["BUG headline"],
                    target_affected=(row["_target_affected"] if _impact_target else None)
                ), axis=1
            )

            display_cols = ["BUG Id", "BUG headline (日本語)", "BUG headline (英語原文)", "Bug Severity", "Bug Status",
                          "Known Affected Release(s)", "Known Fixed Releases",
                          "利用機能", "素因"]
            if impact_col_name:
                display_cols.append(impact_col_name)
            display_cols += ["症状 (日本語)", "回避策 (日本語)", "詳細説明 (日本語)",
                              "発生可能性", "発生しやすさ (推定)", "URL"]

            ai_summary_note = (
                "「AI による可能性判定を使用」がONでキー設定済みの場合、これらはログの詳細を除いた"
                "AI要約（そのキーのAPI利用量を消費）になります。OFFの場合は通常の機械翻訳です。"
                if (use_ai_analysis and (groq_api_key or gemini_api_key or open_router_api_key))
                else "「AI による可能性判定を使用」をONにしキーを設定すると、これらをAIが生ログを除いた"
                     "要点のみに要約するようになります（そのキーのAPI利用量を消費）。"
            )
            st.caption(
                "「発生可能性」は下の「詳細情報」でバグを選択して手動評価するか、AI分析を行うと更新されます"
                "（未評価は「-」）。実際のヒット件数に基づく統計値ではなく、目安としてご利用ください。"
                "「症状」「回避策」「詳細説明」はリリースノートから抽出したものです（無い場合は空欄）。"
                "「利用機能」「素因」「発生しやすさ(推定)」はヘッドラインのキーワードとステータスからの"
                "自動推定であり、統計的根拠のある値ではありません。"
                "件数が多いと翻訳に時間がかかることがあります。 " + ai_summary_note
            )
            st.dataframe(
                display_results[display_cols],
                use_container_width=True,
                hide_index=True
            )

            st.markdown("---")
            st.markdown("### 📥 結果のエクスポート")

            export_results = display_results[display_cols].copy()
            export_results["関連機能"] = export_results["BUG Id"].apply(
                lambda x: ", ".join(st.session_state.bug_analysis.get(x, {}).get("tags", []))
            )
            export_results["コメント"] = export_results["BUG Id"].apply(
                lambda x: st.session_state.bug_analysis.get(x, {}).get("comment", "")
            )

            csv_data = export_results.to_csv(index=False)

            # Excel エクスポート用パラメータ
            search_params = {
                "feature": feature,
                "version": version,
                "severity": severity_filter
            }

            # 上の一覧表の「症状/回避策/詳細説明を表示する」チェックボックス（show_release_note_cols）
            # の結果をそのまま使う。display_results に既に日本語訳/AI要約が入っているため、
            # Excel側で二重に翻訳APIを呼び直すことはしない（以前は別チェックボックスで
            # 独立に再翻訳しており、両方ONの場合に翻訳が2倍走っていた）
            if show_release_note_cols:
                st.caption("Excelにも上の「症状/回避策/詳細説明」列を含めます（一覧表と同じ内容、再翻訳はしません）。")

            # Excel ファイルを生成（display_results には翻訳済み見出し列・症状等が入っている）
            excel_data = create_excel_report(
                display_results, st.session_state.bug_analysis, search_params,
                include_release_notes=show_release_note_cols,
                translation_engine=translation_engine_key,
                deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key,
                groq_api_key=groq_api_key, gemini_api_key=gemini_api_key,
                open_router_api_key=open_router_api_key,
                target_version=_impact_target,
            )

            # 統合Excel出力（Palo Alto / YAMAHA 等との合体）用に、最新の検索結果を保持しておく
            st.session_state["combined_export_cisco"] = {
                "results": display_results,
                "analysis_data": dict(st.session_state.bug_analysis),
                "search_params": search_params,
                "include_release_notes": show_release_note_cols,
                "translation_engine": translation_engine_key,
                "deepl_api_key": deepl_api_key,
                "nvidia_api_key": nvidia_api_key,
                "groq_api_key": groq_api_key,
                "gemini_api_key": gemini_api_key,
                "open_router_api_key": open_router_api_key,
                "target_version": _impact_target,
            }

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.download_button(
                    label="📊 Excel でダウンロード",
                    data=excel_data,
                    file_name=f"cisco_bug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            with col2:
                st.download_button(
                    label="📄 CSV でダウンロード",
                    data=csv_data,
                    file_name=f"bug_search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

            with col3:
                analysis_json = save_analysis_to_json(st.session_state.bug_analysis)
                st.download_button(
                    label="📋 分析結果を JSON で",
                    data=analysis_json,
                    file_name=f"bug_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

            with col4:
                combined_export = {
                    "timestamp": datetime.now().isoformat(),
                    "search_params": search_params,
                    "results": export_results.to_dict('records')
                }
                st.download_button(
                    label="📦 完全レポート",
                    data=json.dumps(combined_export, ensure_ascii=False, indent=2),
                    file_name=f"bug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

            st.markdown("---")
            st.markdown("### 詳細情報")
            selected_idx = st.selectbox(
                "詳細を見るバグを選択",
                range(len(results)),
                format_func=lambda x: f"{results.iloc[x]['BUG Id']} - {translate_headline(results.iloc[x]['BUG headline'], engine=translation_engine_key, deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key)}"
            )

            if selected_idx is not None:
                bug = results.iloc[selected_idx]

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Bug ID", bug["BUG Id"])
                with col2:
                    severity = int(bug["Bug Severity"]) if pd.notna(bug["Bug Severity"]) else 0
                    st.metric("重要度", severity)
                with col3:
                    st.metric("ステータス", bug["Bug Status"])

                headline_en = bug["BUG headline"]
                headline_ja = translate_headline(headline_en, engine=translation_engine_key, deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key)

                st.write("**タイトル（日本語）:**", headline_ja)
                st.caption(f"英語: {headline_en}")
                if translation_engine != "Google":
                    st.caption(f"翻訳エンジン: {translation_engine}")

                st.markdown("---")
                st.markdown("### 📊 バグ分析")

                bug_id = bug["BUG Id"]
                if bug_id not in st.session_state.bug_analysis:
                    st.session_state.bug_analysis[bug_id] = {
                        "possibility": "Medium",
                        "tags": [],
                        "comment": "",
                        "ai_assessment": None
                    }

                analysis = st.session_state.bug_analysis[bug_id]

                release_note = bug["Release Note Enclosure"]

                col1, col2 = st.columns(2)
                with col1:
                    if use_ai_analysis and (groq_api_key or gemini_api_key or open_router_api_key):
                        if st.button("🤖 AI で分析", key=f"ai_btn_{bug_id}"):
                            with st.spinner("AI が分析中..."):
                                assessment = assess_bug_possibility(
                                    headline_ja,
                                    release_note,
                                    analysis["comment"],
                                    groq_key=groq_api_key,
                                    gemini_key=gemini_api_key,
                                    open_router_key=open_router_api_key
                                )

                                if assessment:
                                    st.session_state.bug_analysis[bug_id]["ai_assessment"] = assessment
                                    st.success(f"✓ {assessment['engine']} で分析完了")
                                else:
                                    st.error("AI による分析に失敗しました。API キーを確認してください。")

                    if analysis["ai_assessment"]:
                        st.info(f"**AI 分析結果（{analysis['ai_assessment']['engine']}）:**\n\n{analysis['ai_assessment']['result']}")

                with col2:
                    pass

                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    possibility = st.selectbox(
                        "発生の可能性",
                        ["Low", "Medium", "High"],
                        index=["Low", "Medium", "High"].index(analysis["possibility"]),
                        key=f"possibility_{bug_id}"
                    )
                    analysis["possibility"] = possibility

                with col2:
                    tags = st.multiselect(
                        "関連機能タグ",
                        ["VPN", "Routing", "Multicast", "Security", "DHCP", "Access List", "QoS", "OSPF", "BGP", "その他"],
                        default=analysis["tags"],
                        key=f"tags_{bug_id}"
                    )
                    analysis["tags"] = tags

                comment = st.text_area(
                    "このバグについてのコメント",
                    value=analysis["comment"],
                    height=80,
                    key=f"comment_{bug_id}"
                )
                analysis["comment"] = comment

                sections = parse_release_note(release_note)

                if sections:
                    st.markdown("### 📋 リリースノート情報（日本語）")

                    for section_name, content in sections.items():
                        content_ja = translate_headline(
                            content, engine=translation_engine_key,
                            deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key
                        )
                        st.write(f"**{section_name}:**")
                        st.caption(content_ja)
                        with st.expander("英語原文"):
                            st.caption(content)

                    # Cisco 公式ドキュメントへのリンク
                    affected_releases = str(bug["Known Affected Release(s)"]).split()
                    if affected_releases:
                        first_version = affected_releases[0]
                        product = bug["Product - Series"].split(',')[0].strip()
                        release_url = get_cisco_release_notes_url(product, first_version)

                        if release_url:
                            st.info(
                                f"📚 **参考資料**: "
                                f"[Cisco 公式リリースノート - {product} {first_version}]({release_url})"
                            )

                st.markdown("---")
                st.write("**製品:**", bug["Product - Series"])
                st.write("**影響を受けるバージョン:**", bug["Known Affected Release(s)"])
                st.write("**修正バージョン:**", bug["Known Fixed Releases"])
                st.write("**最終更新:**", bug["Last Modified"])

                col1, col2 = st.columns(2)
                with col1:
                    st.write("**参照リンク:**")
                    st.write(f"[Cisco Bug Search で詳細を確認]({bug['URL']})")

                with st.expander("📄 リリースノート全体"):
                    clean_note = clean_html_tags(release_note)
                    st.text(clean_note)
        else:
            st.warning("該当するバグが見つかりませんでした")
elif uploaded_file is None:
    st.info("👆 CSV / Excel ファイルをアップロードしてください。")

st.markdown("---")

st.markdown("### 🌐 Cisco 以外のベンダー（Palo Alto / YAMAHA 等）を検索")
st.caption(
    "Cisco のような構造化データが無いベンダーは、NVD（米国立脆弱性データベース）を"
    "キーワード検索します。バージョンを指定すると、NVD のバージョン範囲データから"
    "「影響あり / 対象外・修正済みの可能性」を判定します（データが無い場合は判定不可）。"
)
st.caption(
    "💡 検索キーワード・バージョンの確認先（参考）: "
    "PAN-OS リリースノート一覧 → https://docs.paloaltonetworks.com/pan-os ／ "
    "YAMAHA リリースノート・ファームウェア情報 → https://network.yamaha.com/"
)

cve_col1, cve_col2 = st.columns(2)
with cve_col1:
    cve_keyword = st.text_input(
        "検索キーワード",
        placeholder="例: PAN-OS 11.1.2 / Yamaha RTX830",
        key="cve_keyword"
    )
with cve_col2:
    cve_target_version = st.text_input(
        "バージョン（任意、影響有無を判定したい場合）",
        placeholder="例: 11.1.2",
        key="cve_target_version"
    )

nvd_secret = get_secret("NVD_API_KEY")
if nvd_secret:
    st.caption("✓ NVD API キー: Secrets から読み込み済み")
    nvd_api_key = nvd_secret
else:
    nvd_api_key = st.text_input(
        "NVD API キー（任意、無くても検索可・レート制限が緩和される）",
        type="password",
        key="nvd_api_key_input"
    )

if st.button("🔎 CVE を検索", key="cve_search_btn"):
    if not cve_keyword:
        st.warning("検索キーワードを入力してください")
    else:
        with st.spinner("NVD を検索中..."):
            cve_results = analyzer.search_cve_with_translation(
                cve_keyword,
                engine=translation_engine_key,
                deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key,
                api_key=nvd_api_key or None,
                target_version=cve_target_version or None,
            )

        if isinstance(cve_results, dict) and "error" in cve_results:
            st.error(f"NVD への問い合わせに失敗しました: {cve_results['error']}")
        elif not cve_results:
            st.warning("該当する CVE が見つかりませんでした")
        else:
            # 深刻度（CVSS）の高い順に並べ替える。CVSS 不明のものは末尾へ
            cve_results = sorted(
                cve_results,
                key=lambda r: r["cvss_score"] if r["cvss_score"] is not None else -1,
                reverse=True,
            )

            st.success(f"✓ {len(cve_results)} 件見つかりました")
            for r in cve_results:
                label = f"[{r['severity_ja']}] {r['cve_id']}"
                if cve_target_version:
                    label += f" - {r['affected_ja']}"
                with st.expander(label):
                    st.write(r["description_ja"])
                    st.caption(f"英語原文: {r['description_en']}")
                    published = r["published"][:10] if r["published"] else "-"
                    st.write(f"CVSS: {r['cvss_score'] if r['cvss_score'] is not None else '-'}　公開日: {published}")
                    st.write(f"[参考リンク]({r['url']})")

            # 統合Excel出力用に、CVE検索結果を保持しておく（日本語訳をメイン列、英語原文は参考列として末尾に）
            cve_rows = [
                [
                    r["cve_id"], r["severity_ja"], r["cvss_score"],
                    r.get("affected_ja", "-"), r["description_ja"],
                    r["published"][:10] if r["published"] else "-", r["url"],
                    r["description_en"],
                ]
                for r in cve_results
            ]
            st.session_state["combined_export_cve"] = {
                "name": f"CVE検索({cve_keyword[:15]})",
                "headers": ["CVE ID", "深刻度", "CVSS", "影響有無", "概要(日本語)", "公開日", "参考リンク",
                            "概要(英語原文・参考)"],
                "rows": cve_rows,
            }

st.markdown("---")
st.markdown("**一般的な既知の問題を貼り付けて分析**")
st.caption(
    "Palo Alto の「Known and Addressed Issues」ページ等、自動取得できない公式ドキュメントの"
    "内容をブラウザからコピーしてここに貼り付けると、ID単位に分解してカテゴリ分け・日本語訳します。"
    "NVD検索はセキュリティ脆弱性（CVE）のみが対象のため、こちらは一般的な不具合情報を扱います。"
)
st.info(
    "💡 **お願い**: 以下のような公式ページはこちらで自動取得できないため、"
    "ご自身のブラウザで開いてページ内のテキストをコピーし、下の欄に貼り付けてください。\n\n"
    "- Palo Alto（PAN-OS Known and Addressed Issues、バージョンごとに存在）例:\n"
    "  👉 https://docs.paloaltonetworks.com/ngfw/release-notes/12-2/pan-os-12-2-2-known-and-addressed-issues\n"
    "- YAMAHA（RTX/RTシリーズ リリースノート）例: 該当バージョンの「ファームウェアリビジョン」ページ\n\n"
    "他のバージョン・製品を調べたい場合も、同様に該当ページを開いて本文をコピーしてお知らせください。"
)

pasted_issues_text = st.text_area(
    "「ISSUE ID」+ 説明文の形式で貼り付け（例: PAN-332943 の下に説明文、その下に次のID...）",
    height=180,
    key="pasted_issues_text"
)

if st.button("📋 貼り付けたテキストを解析", key="parse_pasted_issues_btn"):
    if not pasted_issues_text.strip():
        st.warning("テキストを貼り付けてください")
    else:
        parsed_issues = analyzer.parse_vendor_known_issues(pasted_issues_text)
        if not parsed_issues:
            st.warning(
                "ID（例: PAN-332943, [12]）を検出できませんでした。"
                "各IDが単独の行になっているか、行頭が角括弧の連番になっているか確認してください。"
            )
        else:
            st.success(f"✓ {len(parsed_issues)} 件検出しました")

            has_sections = any(issue["section"] for issue in parsed_issues)

            grouped = {}
            if has_sections:
                # YAMAHA形式で "■バグ修正" 等の見出しが検出できた場合は、
                # ベンダー自身の分類（新機能/バグ修正等）を優先してグループ化する
                # （キーワード推測より確実なため）。見出しが無い項目は最後にまとめる
                for issue in parsed_issues:
                    key = issue["section"] or "（見出し無し）"
                    grouped.setdefault(key, []).append(issue)
                category_order = [k for k in grouped.keys() if k != "（見出し無し）"] + ["（見出し無し）"]
            else:
                for issue in parsed_issues:
                    for cat in analyzer.categorize_vendor_issue(issue["description"]):
                        grouped.setdefault(cat, []).append(issue)
                # カテゴリの表示順を固定（一般/その他は最後）
                category_order = list(analyzer.VENDOR_ISSUE_CATEGORY_KEYWORDS.keys()) + ["一般 / その他"]

            # カテゴリ順にフラット化してから、1件ずつ翻訳（進捗バー付き）。
            # 1件ごとの展開表示はせず、まとめて一覧表として表示する
            ordered_issues = []
            for cat in category_order:
                if cat not in grouped:
                    continue
                for issue in grouped[cat]:
                    ordered_issues.append((cat, issue))

            total_issues = len(ordered_issues)
            progress_bar3 = st.progress(0.0, text=f"翻訳中... (0/{total_issues})")
            vendor_issue_rows = []
            for i, (cat, issue) in enumerate(ordered_issues, 1):
                desc_ja = translate_headline(
                    issue["description"], engine=translation_engine_key,
                    deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key
                )
                wa_ja = ""
                if issue["workaround"]:
                    wa_ja = translate_headline(
                        issue["workaround"], engine=translation_engine_key,
                        deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key
                    )
                original_ref = issue["description"]
                if issue["workaround"]:
                    original_ref += f" / Workaround: {issue['workaround']}"

                vendor_issue_rows.append([
                    issue["id"], issue["section"] or cat, desc_ja, wa_ja, original_ref,
                ])
                progress_bar3.progress(i / total_issues, text=f"翻訳中... ({i}/{total_issues})")
            progress_bar3.empty()

            vendor_issue_cols = ["ID", "分類", "概要(日本語)", "回避策(日本語)", "原文(英語・参考)"]
            st.dataframe(
                pd.DataFrame(vendor_issue_rows, columns=vendor_issue_cols),
                use_container_width=True,
                hide_index=True
            )

            # 統合Excel出力用に、貼り付け解析結果を保持しておく（日本語訳をメイン列、英語原文は参考列として末尾に）
            st.session_state["combined_export_vendor_issues"] = {
                "name": "貼り付け解析結果",
                "headers": vendor_issue_cols,
                "rows": vendor_issue_rows,
            }

            vendor_excel_data = analyzer.create_combined_excel_report(
                extra_sheets=[st.session_state["combined_export_vendor_issues"]]
            )
            st.download_button(
                label="📊 この解析結果をExcelでダウンロード",
                data=vendor_excel_data,
                file_name=f"vendor_issues_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="vendor_issues_excel_download_btn"
            )

st.markdown("---")
st.markdown("**バージョン系統ごとのEOL（サポート終了日）を調べる**")
st.caption(
    "endoflife.date のデータを使い、メジャーバージョン系統ごとのリリース日・EOL日・"
    "最新パッチと関連リンクを一覧表示します。"
)

eol_product = st.text_input(
    "プロダクトスラッグ",
    value="pan-os",
    placeholder="例: pan-os",
    help="endoflife.date 上のプロダクト識別子（一覧: https://endoflife.date/）",
    key="eol_product"
)

if st.button("📅 EOL情報を取得", key="eol_info_btn"):
    if not eol_product.strip():
        st.warning("プロダクトスラッグを入力してください")
    else:
        with st.spinner("EOL情報を取得中..."):
            eol_results = analyzer.get_eol_info(eol_product.strip())

        if isinstance(eol_results, dict) and "error" in eol_results:
            st.error(f"EOL情報の取得に失敗しました: {eol_results['error']}")
        elif not eol_results:
            st.warning("該当するEOL情報が見つかりませんでした")
        else:
            # 対応期限（EOL）が近い順に並べ替える。EOL未定（現役）は最後に回す
            eol_results = sorted(eol_results, key=lambda r: r["eol"] or "9999-99-99")

            eol_table = pd.DataFrame([
                {
                    "対応期限(EOL)": r["eol"] or "未定（現役）",
                    "状態": "🔴 EOL済み" if r["is_eol"] else "🟢 サポート中",
                    "系統": r["release_cycle"],
                    "リリース日": r["release_date"],
                    "最新パッチ": r["latest"],
                    "リンク": r["link"],
                }
                for r in eol_results
            ])
            st.dataframe(eol_table, use_container_width=True, hide_index=True)

            # 統合Excel出力用に、EOL情報を保持しておく（対応期限を先頭列にして優先度を分かりやすく）
            eol_rows = [
                [
                    r["eol"] or "未定（現役）",
                    "EOL済み" if r["is_eol"] else "サポート中",
                    r["release_cycle"], r["release_date"], r["latest"], r["link"],
                ]
                for r in eol_results
            ]
            st.session_state["combined_export_eol"] = {
                "name": f"EOL情報({eol_product.strip()[:15]})",
                "headers": ["対応期限(EOL)", "状態", "系統", "リリース日", "最新パッチ", "リンク"],
                "rows": eol_rows,
            }

            eol_excel_data = analyzer.create_combined_excel_report(
                extra_sheets=[st.session_state["combined_export_eol"]]
            )
            st.download_button(
                label="📊 このEOL情報をExcelでダウンロード",
                data=eol_excel_data,
                file_name=f"eol_report_{eol_product.strip()[:15]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="eol_excel_download_btn"
            )

            st.info(
                "💡 **お願い**: 上表の「リンク」先ページ（バグ一覧・Known and Addressed Issues等）は"
                "自動取得できません。お手数ですが、リンクをブラウザで開いて該当箇所をコピーし、"
                "上の「一般的な既知の問題を貼り付けて分析」欄に貼り付けてください。"
            )

st.markdown("---")
st.markdown("### 🗂️ 全ベンダーまとめてExcel出力")

_combined_sources = []
if "combined_export_cisco" in st.session_state:
    _combined_sources.append(f"Cisco（{len(st.session_state['combined_export_cisco']['results'])} 件）")
if "combined_export_cve" in st.session_state:
    _combined_sources.append(f"{st.session_state['combined_export_cve']['name']}（{len(st.session_state['combined_export_cve']['rows'])} 件）")
if "combined_export_vendor_issues" in st.session_state:
    _combined_sources.append(f"貼り付け解析結果（{len(st.session_state['combined_export_vendor_issues']['rows'])} 件）")
if "combined_export_eol" in st.session_state:
    _combined_sources.append(f"{st.session_state['combined_export_eol']['name']}（{len(st.session_state['combined_export_eol']['rows'])} 件）")

if not _combined_sources:
    st.caption("Cisco検索・CVE検索・貼り付け解析・EOL取得のいずれかを実行すると、ここでまとめてExcel出力できるようになります。")
else:
    st.caption("この画面で今までに実行した検索結果を、1つのExcelファイルにシート分けして出力します: " + " / ".join(_combined_sources))

    if st.button("📦 統合Excelを生成", key="combined_excel_btn"):
        combined_extra_sheets = []
        if "combined_export_cve" in st.session_state:
            combined_extra_sheets.append(st.session_state["combined_export_cve"])
        if "combined_export_vendor_issues" in st.session_state:
            combined_extra_sheets.append(st.session_state["combined_export_vendor_issues"])
        if "combined_export_eol" in st.session_state:
            combined_extra_sheets.append(st.session_state["combined_export_eol"])

        combined_excel_data = analyzer.create_combined_excel_report(
            cisco=st.session_state.get("combined_export_cisco"),
            extra_sheets=combined_extra_sheets or None,
        )

        st.download_button(
            label="📦 統合Excelをダウンロード",
            data=combined_excel_data,
            file_name=f"combined_vendor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="combined_excel_download_btn",
        )
