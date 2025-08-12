import streamlit as st
import pandas as pd
import json
import random
import numpy as np

# --- 1. 初期設定とデータ読み込み ---

# ページのレイアウトを"wide"に設定して、横幅を広く使います
st.set_page_config(page_title="簿記 精算表ドリル", layout="wide")

st.title("簿記3級 精算表シャッフル問題アプリ")
st.write("決算整理前の試算表と決算整理事項から、精算表を完成させてください。「次の問題へ」ボタンで新しい問題がランダムに表示されます。")

# JSONファイルから問題を読み込む関数 (キャッシュして高速化)
@st.cache_data
def load_problems():
    try:
        with open('problems.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("`problems.json`ファイルが見つかりません。app.pyと同じ階層に配置してください。")
        return []

problems = load_problems()
if not problems:
    st.stop()


# --- 2. セッション状態の初期化 ---
# st.session_stateを使ってアプリの状態を保持します

# 最初にアクセスしたときだけ問題をランダムに選択
if 'current_problem' not in st.session_state:
    st.session_state.current_problem = random.choice(problems)

# --- 3. サイドバーと問題選択 ---

with st.sidebar:
    st.header("コントロールパネル")
    if st.button("次の問題へ (ランダム)"):
        # 現在の問題と違う問題が選ばれるまで再抽選
        new_problem = random.choice(problems)
        while len(problems) > 1 and new_problem['id'] == st.session_state.current_problem['id']:
            new_problem = random.choice(problems)
        st.session_state.current_problem = new_problem
        # ページを再実行して表示を新しい問題に更新
        st.rerun()

    st.write("---")
    st.write("現在の問題:")
    # st.session_stateに問題がなければエラーになるのを防ぐ
    if 'current_problem' in st.session_state:
        st.info(st.session_state.current_problem['title'])


# --- 4. 問題の表示 ---

# 現在の問題をセッションから取得
problem = st.session_state.current_problem

st.header(f"問題: {problem['title']}")

# 2つのカラムを作成して、試算表と整理事項を横に並べる
col1, col2 = st.columns(2)

with col1:
    st.subheader("決算整理前残高試算表")
    trial_balance_df = pd.DataFrame(problem['trial_balance']).set_index('勘定科目')
    st.dataframe(trial_balance_df)

with col2:
    st.subheader("決算整理事項")
    for i, adj in enumerate(problem['adjustments'], 1):
        st.write(f"{i}. {adj}")


# --- 5. ユーザー解答欄 (精算表) の表示 ---

st.header("解答欄: 精算表")
st.write("以下の表に修正記入、損益計算書、貸借対照表の金額を記入してください。")

# 解答用のテンプレートを作成
# まず、正解データからすべての勘定科目のリストを取得
solution_accounts_df = pd.DataFrame(problem['solution']).set_index('勘定科目')
# ユーザー入力用のデータフレームを作成し、入力列を0で初期化
user_df = solution_accounts_df.copy()
columns_to_edit = ['修正記入(借)', '修正記入(貸)', '損益計算書(借)', '損益計算書(貸)', '貸借対照表(借)', '貸借対照表(貸)']
user_df[columns_to_edit] = 0

# 試算表のデータを元の問題から転記
user_df['試算表(借)'] = trial_balance_df['借方']
user_df['試算表(貸)'] = trial_balance_df['貸方']
user_df = user_df.fillna(0).astype(int) # NaNを0で埋める

# 修正1: keyに問題のIDを加えて、問題ごとにdata_editorの状態を独立させる
# 修正2: use_container_width=True を追加して、表がコンテナの幅いっぱいに広がるようにする
edited_df = st.data_editor(
    user_df[['試算表(借)', '試算表(貸)', '修正記入(借)', '修正記入(貸)', '損益計算書(借)', '損益計算書(貸)', '貸借対照表(借)', '貸借対照表(貸)']],
    disabled=['試算表(借)', '試算表(貸)'], # 試算表の列は編集不可に
    use_container_width=True, # ★★★★★ これが列の表示問題を解決します
    key=f"editor_{problem['id']}" # ★★★★★ これがエラーを解決します
)


# --- 6. 採点処理 ---

if st.button("採点する！"):
    # 正解データをデータフレームとして読み込む
    solution_df = pd.DataFrame(problem['solution']).set_index('勘定科目')
    # ユーザーの入力を取得 (edited_dfをそのまま使える)
    user_answer_df = edited_df

    # 比較のためにデータ型をintに揃える
    solution_df = solution_df.astype(int)
    user_answer_df = user_answer_df.astype(int)

    # ユーザーの解答と正解を比較し、間違っているセルをハイライトするためのスタイル関数
    def highlight_diff(data, color='yellow'):
        # 正解データ(solution_df)をグローバルスコープから参照
        is_diff = (data != solution_df)
        return pd.DataFrame(np.where(is_diff, f'background-color: {color}', ''),
                              index=data.index, columns=data.columns)

    # 採点対象の列だけを比較
    user_to_check = user_answer_df[columns_to_edit]
    solution_to_check = solution_df[columns_to_edit]

    # 採点結果の表示
    st.subheader("採点結果")
    if user_to_check.equals(solution_to_check):
        st.success("🎉 全問正解です！おめでとうございます！ 🎉")
        st.balloons()
    else:
        st.error("残念！間違っている箇所があります。")
        st.write("黄色でハイライトされているのが間違っているセルです。")

        # 間違い箇所をハイライトして表示
        styled_df = user_answer_df.style.apply(highlight_diff, axis=None)
        st.dataframe(styled_df, use_container_width=True)

        with st.expander("正解を表示する"):
            st.dataframe(solution_df, use_container_width=True)