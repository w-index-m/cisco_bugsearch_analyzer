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

st.title("🔍 Cisco Bug Search Analyzer")
st.markdown("Cisco バグ検索システム - 機能とバージョンから該当するバグを検索")


@st.cache_data
def load_csv(file_path):
    """CSV ファイルを読み込み（Streamlit キャッシュ付き）"""
    try:
        return analyzer.load_csv(file_path)
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
        return None


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


# CSV ファイル読み込み（デフォルト）
default_csv = "bugSearch.csv"

# ファイルアップロード or デフォルトを使用
uploaded_file = st.file_uploader("CSV ファイルをアップロード（オプション）", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()
else:
    df = load_csv(default_csv)

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
    with col1:
        st.subheader("IOS バージョンから検索")
    with col2:
        st.subheader("翻訳設定 & Severity")

    col1, col2 = st.columns([2, 1])
    with col2:
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
                deepl_api_key = st.text_input(
                    "DeepL API キー",
                    type="password",
                    value=deepl_secret or "",
                    placeholder="API キーを入力"
                )
                if deepl_secret:
                    st.caption("✓ Secrets から読み込み済み（手入力で上書き可能）")
                if not deepl_api_key:
                    st.warning("DeepL API キーを入力してください")
            else:
                st.warning("deepl ライブラリがインストールされていません")
                translation_engine = "Google"

        elif translation_engine == "NVIDIA Riva":
            nvidia_secret = get_secret("NVIDIA_API_KEY")
            nvidia_api_key = st.text_input(
                "NVIDIA API キー",
                type="password",
                value=nvidia_secret or "",
                placeholder="API キーを入力"
            )
            if nvidia_secret:
                st.caption("✓ Secrets から読み込み済み（手入力で上書き可能）")
            if not nvidia_api_key:
                st.warning("NVIDIA API キーを入力してください")

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
            st.markdown("API キーを入力（持っているもののみ）:")

            groq_secret = get_secret("GROQ_API_KEY")
            groq_api_key = st.text_input(
                "Groq API キー",
                type="password",
                value=groq_secret or "",
                placeholder="gsk_...",
                label_visibility="collapsed"
            )
            if groq_secret:
                st.caption("✓ Secrets から読み込み済み（手入力で上書き可能）")

            gemini_secret = get_secret("GEMINI_API_KEY")
            gemini_api_key = st.text_input(
                "Gemini API キー",
                type="password",
                value=gemini_secret or "",
                placeholder="AIza...",
                label_visibility="collapsed"
            )
            if gemini_secret:
                st.caption("✓ Secrets から読み込み済み（手入力で上書き可能）")

            open_router_secret = get_secret("OPENROUTER_API_KEY")
            open_router_api_key = st.text_input(
                "Open Router キー",
                type="password",
                value=open_router_secret or "",
                placeholder="sk-or-...",
                label_visibility="collapsed"
            )
            if open_router_secret:
                st.caption("✓ Secrets から読み込み済み（手入力で上書き可能）")

    st.markdown("---")
    st.subheader("IOS バージョンから検索")

    sorted_releases = list_affected_releases(df)

    selected_ios_version = st.selectbox(
        "IOS バージョンを選択",
        [""] + sorted_releases,
        format_func=lambda x: "バージョンを選択..." if x == "" else x
    )

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        feature = st.text_input(
            "機能を入力（Product / Headline）",
            placeholder='例：VPN Multicast BGP、または "Catalyst 9300" VPN',
            help="カンマまたはスペース（全角/半角）区切りで複数キーワードを指定するとOR検索になります。"
                 "スペースを含む語をそのまま1語で検索したい場合はダブルクォートで囲んでください"
                 "（例: '\"Catalyst 9300\" VPN' なら Catalyst 9300 を1語として、VPNを別語としてOR検索）。"
        )

    with col2:
        version = st.text_input(
            "バージョンを入力（Known Affected Release）",
            placeholder="例：17.12.4, 17.15.2, etc."
        )

    search_button = st.button("🔎 バグを検索", type="primary")

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

    if search_button or (feature or version):
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
            display_results = results.copy()
            display_results["BUG headline (日本語)"] = display_results["BUG headline"].apply(
                lambda x: translate_headline(x, engine=translation_engine, deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key)
            )

            display_cols = ["BUG Id", "BUG headline (日本語)", "Bug Severity", "Bug Status",
                          "Known Affected Release(s)", "Known Fixed Releases"]

            st.dataframe(
                display_results[display_cols],
                use_container_width=True,
                hide_index=True
            )

            st.markdown("### 詳細情報")
            selected_idx = st.selectbox(
                "詳細を見るバグを選択",
                range(len(results)),
                format_func=lambda x: f"{results.iloc[x]['BUG Id']} - {translate_headline(results.iloc[x]['BUG headline'], engine=translation_engine, deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key)}"
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
                headline_ja = translate_headline(headline_en, engine=translation_engine, deepl_api_key=deepl_api_key, nvidia_api_key=nvidia_api_key)

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
                    st.markdown("### 📋 リリースノート情報")

                    for section_name, content in sections.items():
                        st.write(f"**{section_name}:**")
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

            st.markdown("---")
            st.markdown("### 📥 結果のエクスポート")

            export_results = display_results[display_cols].copy()
            export_results["発生可能性"] = export_results["BUG Id"].apply(
                lambda x: st.session_state.bug_analysis.get(x, {}).get("possibility", "-")
            )
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

            # Excel ファイルを生成（display_results には翻訳済み見出し列が入っている）
            excel_data = create_excel_report(display_results, st.session_state.bug_analysis, search_params)

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
        else:
            st.warning("該当するバグが見つかりませんでした")
else:
    st.error("CSV ファイルを読み込めません")

st.markdown("---")

with st.expander("🌐 Cisco 以外のベンダー（Palo Alto / YAMAHA 等）を検索"):
    st.caption(
        "Cisco のような構造化データが無いベンダーは、NVD（米国立脆弱性データベース）を"
        "キーワード検索します。バージョンを指定すると、NVD のバージョン範囲データから"
        "「影響あり / 対象外・修正済みの可能性」を判定します（データが無い場合は判定不可）。"
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
    nvd_api_key_input = st.text_input(
        "NVD API キー（任意、無くても検索可・レート制限が緩和される）",
        type="password",
        value=nvd_secret or "",
        key="nvd_api_key_input"
    )
    if nvd_secret:
        st.caption("✓ Secrets から読み込み済み（手入力で上書き可能）")

    if st.button("🔎 CVE を検索", key="cve_search_btn"):
        if not cve_keyword:
            st.warning("検索キーワードを入力してください")
        else:
            with st.spinner("NVD を検索中..."):
                cve_results = analyzer.search_cve_with_translation(
                    cve_keyword,
                    engine="google",
                    api_key=nvd_api_key_input or None,
                    target_version=cve_target_version or None,
                )

            if isinstance(cve_results, dict) and "error" in cve_results:
                st.error(f"NVD への問い合わせに失敗しました: {cve_results['error']}")
            elif not cve_results:
                st.warning("該当する CVE が見つかりませんでした")
            else:
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
