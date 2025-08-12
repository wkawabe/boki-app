import streamlit as st
import pandas as pd
import numpy as np
import json
import random

# --- 1. 初期設定とデータ読み込み ---

st.set_page_config(page_title="簿記 精算表ドリル", layout="wide")

st.title("簿記 精算表シャッフル問題アプリ")
st.write("決算整理前の試算表と決算整理事項から、精算表を完成させてください。「次の問題へ」ボタンで新しい問題がランダムに表示されます。")

# JSONファイルから問題を読み込む関数
@st.cache_data
def load_problems():
    with open('problems.json', 'r', encoding='utf-8') as f:
        return json.load(f)

problems = load_problems()

# --- 2. セッション状態の初期化 ---
# Streamlitはスクリプトが再実行されるたびに変数がリセットされるため、
# st.session_stateを使ってアプリの状態を保持します。

if 'current_problem' not in st.session_state:
    st.session_state.current_problem = random.choice(problems)
    st.session_state.user_input_df = None

# --- 3. サイドバーと問題選択 ---

with st.sidebar:
    st.header("問題選択")
    if st.button("次の問題へ (ランダム)"):
        st.session_state.current_problem = random.choice(problems)
        # 新しい問題が選択されたら、ユーザーの入力と採点結果をリセット
        st.session_state.user_input_df = None
        st.session_state.result_df = None
        st.experimental_rerun() # ページを再読み込みして表示を更新

    st.write("---")
    st.write("現在の問題:")
    st.info(st.session_state.current_problem['title'])


# --- 4. 問題の表示 ---

problem = st.session_state.current_problem

st.header(f"問題: {problem['title']}")

# 決算整理前試算表の表示
st.subheader("決算整理前残高試算表")
trial_balance_df = pd.DataFrame(problem['trial_balance'])
st.dataframe(trial_balance_df.set_index('勘定科目'))

# 決算整理事項の表示
st.subheader("決算整理事項")
for adj in problem['adjustments']:
    st.write(f"- {adj}")


# --- 5. ユーザー解答欄 (精算表) の表示 ---

st.header("解答欄: 精算表")
st.write("以下の表に修正記入、損益計算書、貸借対照表の金額を記入してください。")

# 解答用の空の精算表データフレームを作成
# 試算表の勘定科目に、決算整理で新たに出てくる科目を追加
solution_template_df = pd.DataFrame(problem['solution']).set_index('勘定科目')
user_df = solution_template_df.copy()

# ユーザーには試算表の列は表示するが、編集はさせない
# ユーザーが入力すべき列だけを抽出して空にする
columns_to_edit = ['修正記入(借)', '修正記入(貸)', '損益計算書(借)', '損益計算書(貸)', '貸借対照表(借)', '貸借対照表(貸)']
for col in columns_to_edit:
    user_df[col] = 0 # 0で初期化

# 試算表のデータは元の問題から持ってくる
user_df['試算表(借)'] = trial_balance_df.set_index('勘定科目')['借方']
user_df['試算表(貸)'] = trial_balance_df.set_index('勘定科目')['貸方']
user_df = user_df.fillna(0).astype(int) # NaNを0で埋める

# st.data_editorでユーザーが編集可能な表を表示
# `key`を設定することで、入力内容をsession_stateに保存する
edited_df = st.data_editor(
    user_df[['試算表(借)', '試算表(貸)', '修正記入(借)', '修正記入(貸)', '損益計算書(借)', '損益計算書(貸)', '貸借対照表(借)', '貸借対照表(貸)']],
    disabled=['試算表(借)', '試算表(貸)'], # 試算表の列は編集不可に
    num_rows="dynamic", # ユーザーが行を追加できるようにする（今回は不要かも）
    key="user_input_df"
)


# --- 6. 採点処理 ---

if st.button("採点する！"):
    # 正解データをデータフレームとして読み込む
    solution_df = pd.DataFrame(problem['solution']).set_index('勘定科目')
    
    # ユーザーの入力を取得
    user_answer_df = st.session_state.user_input_df
    
    # 正解とユーザーの解答を比較し、間違っているセルをハイライトするためのスタイル関数
    def highlight_diff(data, other, color='yellow'):
        attr = f'background-color: {color}'
        # otherのインデックスとカラムをdataに合わせる
        other = other.reindex(index=data.index, columns=data.columns)
        is_diff = (data != other) & ~(data.isnull() & other.isnull())
        return pd.DataFrame(np.where(is_diff, attr, ''),
                              index=data.index, columns=data.columns)

    # ユーザーの解答を比較用に準備（勘定科目をインデックスに）
    user_answer_for_comparison = pd.DataFrame(user_answer_df).set_index(solution_df.index)
    
    # 採点結果の表示
    st.subheader("採点結果")
    if user_answer_for_comparison[columns_to_edit].equals(solution_df[columns_to_edit]):
        st.success("🎉 全問正解です！おめでとうございます！ 🎉")
    else:
        st.error("残念！間違っている箇所があります。")
        st.write("黄色でハイライトされているのが間違っているセルです。")
        
        # 間違い箇所をハイライトして表示
        styled_df = user_answer_for_comparison.style.apply(
            highlight_diff,
            other=solution_df,
            axis=None
        )
        st.dataframe(styled_df)

        # 解答も表示
        st.subheader("正解")
        st.dataframe(solution_df)