<p align="center">
  <img src="assets/logo.jpg" width="200"/>
</p>

<p align="center">
  <strong>OpenManus: あなたの多機能AIエージェントフレームワーク</strong>
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README_zh.md">中文</a> | <a href="README_ko.md">한국어</a> | 日本語
</p>

<p align="center">
  <a href="https://github.com/mannaandpoem/OpenManus/stargazers"><img src="https://img.shields.io/github/stars/mannaandpoem/OpenManus?style=social" alt="GitHub stars"></a>
  &ensp;
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  &ensp;
  <a href="https://discord.gg/DYn29wFk9z"><img src="https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat" alt="Discord Follow"></a>
  &ensp;
  <a href="https://huggingface.co/spaces/lyh-917/OpenManusDemo"><img src="https://img.shields.io/badge/Demo-Hugging%20Face-yellow" alt="Demo"></a>
</p>

---

## 👋 はじめに

Manusに触発された**OpenManus**は、様々なタスクに取り組むことができる多機能AIエージェントを構築するためのオープンソースフレームワークを提供します。招待コードなしでユーザーがアイデアを実現できるようにすることを目指しています。

**このバージョンでは、インタラクティブなチャットとセッション管理のためのユーザーフレンドリーなWeb UI（Gradioで構築）と、プログラムによるアクセスのためのOpenAI互換API（FastAPIで構築）、そして純粋なコマンドラインインターフェースが統合され、マルチターン会話、セッション管理、履歴の永続化をサポートしています。**

私たちのチームメンバー [@Xinbin Liang](https://github.com/mannaandpoem) と [@Jinyu Xiang](https://github.com/XiangJinyu)（主要開発者）、そして [@Zhaoyang Yu](https://github.com/MoshiQAQ)、[@Jiayi Zhang](https://github.com/didiforgithub)、[@Sirui Hong](https://github.com/stellaHSR) は [@MetaGPT](https://github.com/geekan/MetaGPT) から来ました。プロトタイプは3時間以内に立ち上げられ、継続的に開発を進めています！

これはシンプルな実装ですので、どんな提案、貢献、フィードバックも歓迎します！

OpenManusで自分だけのエージェントを楽しみましょう！

また、UIUCとOpenManusの研究者が共同開発した[OpenManus-RL](https://github.com/OpenManus/OpenManus-RL)をご紹介できることを嬉しく思います。これは強化学習（RL）ベース（GRPOなど）のLLMエージェントチューニング手法に特化したオープンソースプロジェクトです。

## ✨ 特徴 (追加)

*   **マルチターン会話**: コンテキストを保持した拡張対話が可能です。
*   **Web UI (Gradio)**: 直感的なWebインターフェースを通じてエージェントと対話できます。以下の機能が含まれます：
    *   リアルタイム更新のためのストリーミング応答。
    *   セッション管理（会話の作成、名前変更、削除、切り替え）。
    *   ローカルの`chatsHistory/`ディレクトリに自動保存される永続的なチャット履歴。
*   **OpenAI互換API (FastAPI)**: 使い慣れたOpenAI SDK形式（`/v1/chat/completions`エンドポイント）を使用して、OpenManusをアプリケーションに統合できます。ストリーミングモードと非ストリーミングモードの両方をサポートします。
*   **コマンドラインインターフェース (CLI)**: 純粋なターミナルでの対話方法を提供します。
*   **多機能ツール**: 以下のタスクを実行するためのツールを備えています：
    *   Webブラウジング (`BrowserUseTool`)
    *   コード実行（サンドボックス環境でのPython）
    *   ファイル操作（文字列置換エディタ）
    *   Web検索（Google, Bing, DuckDuckGo, Baidu）
    *   Bashコマンド実行（サンドボックス端末経由）
*   **拡張可能なフレームワーク**: 明確なオブジェクト指向構造で構築されています（`BaseAgent` -> `ReActAgent` -> `ToolCallAgent` -> `BrowserAgent` -> `Manus`）。

## 📸 スクリーンショット (追加)

**Web UI:**
![OpenManus Web UI スクリーンショット 1](https://github.com/Hank-Chromela/Hank-Chroela-images/blob/main/1743753144854.png?raw=true)

**セッション管理:**
![OpenManus Web UI スクリーンショット 2](https://github.com/Hank-Chromela/Hank-Chroela-images/blob/main/1743753160804.png?raw=true)

## 🚀 インストール方法

インストール方法は2つ提供しています。方法2（uvを使用）は、より高速なインストールと優れた依存関係管理のため推奨されています。

### 方法1：condaを使用

1.  新しいconda環境を作成します：
    ```bash
    conda create -n open_manus python=3.12 -y
    conda activate open_manus
    ```
2.  リポジトリをクローンします：
    ```bash
    git clone https://github.com/Hank-Chromela/OpenManus-GUI.git # あなたのForkをクローンしてください
    cd OpenManus-GUI
    ```
3.  依存関係をインストールします：
    ```bash
    pip install -r requirements.txt
    ```

### 方法2：uvを使用（推奨）

1.  uv（高速なPythonパッケージインストーラーと管理機能）をインストールします：
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
2.  リポジトリをクローンします：
    ```bash
    git clone https://github.com/Hank-Chromela/OpenManus-GUI.git # あなたのForkをクローンしてください
    cd OpenManus-GUI
    ```
3.  新しい仮想環境を作成してアクティベートします：
    ```bash
    uv venv --python 3.12
    source .venv/bin/activate  # Unix/macOSの場合
    # .venv\Scripts\activate    # Windowsの場合
    ```
4.  依存関係をインストールします：
    ```bash
    uv pip install -r requirements.txt
    ```

### ブラウザ自動化ツール（必須）

```bash
playwright install --with-deps
⚙️ 設定
OpenManusを使用するには、LLM APIの設定が必要です。以下の手順に従って設定してください：

config/config.example.toml ファイルの確認: このファイルは設定テンプレートです。
config/config.toml ファイルの作成:
cp config/config.example.toml config/config.toml
config/config.toml の編集: APIキーを追加し、設定をカスタマイズします：
# グローバルLLM設定 (主に default を使用)
[llm.default]
model = "gpt-4o" # 例: gpt-4o, gpt-3.5-turbo, claude-3-opus-20240229 など
api_type = "openai" # "openai", "azure", "aws" (Bedrock) など、LLM設定に応じてサポート
base_url = "https://api.openai.com/v1" # APIアドレスに置き換えてください
api_key = "sk-..."  # 重要：実際のAPIキーに置き換えてください！
max_tokens = 4096
temperature = 0.0
# api_version = "..." # Azure OpenAI を使用する場合に必要

# 特定のLLMモデル用のオプション設定 (例：ビジョンタスク用)
# [llm.vision]
# model = "gpt-4o"
# base_url = "https://api.openai.com/v1"
# api_key = "sk-..."
注意: config/config.toml ファイルは機密情報を含むため、.gitignore に追加されており、バージョン管理には含まれません。
▶️ アプリケーションの実行 (更新)
異なるエントリーポイントファイルを通じて、異なるモードで起動できるようになりました：

1. Web UI と API サーバーの起動 (推奨)

main.py スクリプトを実行します：

python main.py
# または明示的に all を指定 (デフォルトの動作)
# python main.py --service all
これにより：

Gradio Web UI サーバーが起動します（デフォルトは http://127.0.0.1:7860 でリッスン）。
FastAPI API サーバーが起動します（デフォルトは http://0.0.0.0:8000 でリッスン）。
ブラウザで Web UI が自動的に開かれます。
2. Web UI のみの起動

python main.py --service ui
Gradio Web UI サーバーのみが起動します（デフォルト http://127.0.0.1:7860）。
ブラウザが自動的に開かれます。
3. API サーバーのみの起動

python main.py --service api
FastAPI API サーバーのみが起動します（デフォルト http://0.0.0.0:8000）。
4. コマンドラインインターフェース (CLI) の実行

python cli_main.py
純粋なコマンドライン対話インターフェースを起動します。
💻 Web UIの使用方法 (追加)
ブラウザが自動的に開かない場合は、手動でhttp://127.0.0.1:7860にアクセスしてください。
チャット: 下部のメッセージボックスにリクエストを入力し、Enterキーを押すか「送信」をクリックします。エージェントの思考プロセス、ツールの使用状況、最終的な応答がチャットウィンドウにストリーミング表示されます。
セッション管理:
左側のサイドバーを使用して会話を管理します。
「➕ 新しいチャット」をクリックして新しい会話を開始します。
リストからセッションを選択して、その履歴を読み込みます。
リストの下にある「選択したセッションを管理」セクションを使用して、現在選択されているチャットの名前を変更したり削除したりします（最後のチャットは削除できません）。
永続性: チャット履歴とセッション名は、JSONファイルとしてchatsHistory/ディレクトリに自動的に保存され、アプリケーションを再起動すると再読み込みされます。
🔌 APIの使用方法 (追加)
サーバーは/v1/chat/completionsでOpenAI互換のAPIエンドポイントを公開しています（デフォルトでは http://0.0.0.0:8000 で実行）。標準的なOpenAIクライアントライブラリ（公式のPython openaiライブラリなど）を使用して対話できます。

クライアントの設定:

Base URL: http://<サーバーIPまたはlocalhost>:8000/v1 (例: http://127.0.0.1:8000/v1)
API Key: 任意の空でない文字列（例："not-needed"）。サーバーはこのキーを検証しません。
Model: 任意の空でない文字列（例："openmanus"）。サーバーはこのモデル名を無視し、設定されたManusエージェントを使用します。
openai Pythonライブラリを使用した例:

# test_api.py
import openai

# クライアントを設定 (APIサーバーがローカルの8000ポートで実行されていると仮定)
client = openai.OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="not-needed", # ダミーキーを提供
)

# 非ストリーミングリクエスト
try:
    completion = client.chat.completions.create(
        model="openmanus-local", # モデル名は必須ですが、サーバーに無視されます
        messages=[
            {"role": "user", "content": "フランスの首都はどこですか？"}
        ]
    )
    print("非ストリーミング応答:")
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"APIエラー: {e}")

# ストリーミングリクエスト
try:
    stream = client.chat.completions.create(
        model="openmanus-local",
        messages=[
            {"role": "user", "content": "量子もつれについて簡単に説明してください。"}
        ],
        stream=True
    )
    print("\nストリーミング応答:")
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end="")
    print()
except Exception as e:
    print(f"APIストリーミングエラー: {e}")
🙌 貢献方法
我々は建設的な意見や有益な貢献を歓迎します！issueを作成するか、プルリクエストを提出してください。

または @mannaandpoem に📧メールでご連絡ください：mannaandpoem@gmail.com

注意: プルリクエストを送信する前に、pre-commitツールを使用して変更を確認してください。pre-commit run --all-filesを実行してチェックを実行します。

💬 コミュニティグループ
Feishuのネットワーキンググループに参加して、他の開発者と経験を共有しましょう！

⭐ スター履歴
Star History Chart

🙏 謝辞
このプロジェクトの基本的なサポートを提供してくれたanthropic-computer-use とbrowser-useに感謝します！

さらに、AAAJ、MetaGPT、OpenHands、SWE-agentにも感謝します。

また、Hugging Face デモスペースをサポートしてくださった阶跃星辰 (stepfun)にも感謝いたします。

OpenManusはMetaGPTのコントリビューターによって構築されました。このエージェントコミュニティに大きな感謝を！

📜 引用
研究や業務でOpenManusを使用する場合は、次のように引用してください：

@misc{openmanus2025,
  author = {Xinbin Liang and Jinyu Xiang and Zhaoyang Yu and Jiayi Zhang and Sirui Hong and Hank-Chromela (UI/API Integration)},
  title = {OpenManus: UIとAPIを備えた多機能AIエージェントのためのオープンソースフレームワーク},
  year = {2025},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/mannaandpoem/OpenManus}},
}
