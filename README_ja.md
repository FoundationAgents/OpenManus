<p align="center">
  <img src="assets/logo.jpg" width="200"/>
</p>

[English](README.md) | [中文](README_zh.md) | [한국어](README_ko.md) | 日本語

[![GitHub stars](https://img.shields.io/github/stars/FoundationAgents/OpenManus?style=social)](https://github.com/FoundationAgents/OpenManus/stargazers)
&ensp;
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) &ensp;
[![Discord Follow](https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat)](https://discord.gg/DYn29wFk9z)
[![Demo](https://img.shields.io/badge/Demo-Hugging%20Face-yellow)](https://huggingface.co/spaces/lyh-917/OpenManusDemo)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15186407.svg)](https://doi.org/10.5281/zenodo.15186407)

# 👋 OpenManus

Manusは素晴らしいですが、OpenManusは*招待コード*なしでどんなアイデアも実現できます！🛫

私たちのチームメンバー [@Xinbing Liang](https://github.com/mannaandpoem) と [@Jinyu Xiang](https://github.com/XiangJinyu)（主要開発者）、そして [@Zhaoyang Yu](https://github.com/MoshiQAQ)、[@Jiayi Zhang](https://github.com/didiforgithub)、[@Sirui Hong](https://github.com/stellaHSR) は [@MetaGPT](https://github.com/geekan/MetaGPT) から来ました。プロトタイプは3時間以内に立ち上げられ、継続的に開発を進めています！

これはシンプルな実装ですので、どんな提案、貢献、フィードバックも歓迎します！

OpenManusで自分だけのエージェントを楽しみましょう！

また、UIUCとOpenManusの研究者が共同開発した[OpenManus-RL](https://github.com/OpenManus/OpenManus-RL)をご紹介できることを嬉しく思います。これは強化学習（RL）ベース（GRPOなど）のLLMエージェントチューニング手法に特化したオープンソースプロジェクトです。

## プロジェクトデモ

<video src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" data-canonical-src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" controls="controls" muted="muted" class="d-block rounded-bottom-2 border-top width-fit" style="max-height:640px; min-height: 200px"></video>

## インストール方法

インストール方法は2つ提供しています。方法2（uvを使用）は、より高速なインストールと優れた依存関係管理のため推奨されています。

### 方法1：condaを使用

1. 新しいconda環境を作成します：

```bash
conda create -n open_manus python=3.12
conda activate open_manus
```

2. リポジトリをクローンします：

```bash
git clone https://github.com/FoundationAgents/OpenManus.git
cd OpenManus
```

3. 依存関係をインストールします：

```bash
pip install -r requirements.txt
```

### 方法2：uvを使用（推奨）

1. uv（高速なPythonパッケージインストーラーと管理機能）をインストールします：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. リポジトリをクローンします：

```bash
git clone https://github.com/FoundationAgents/OpenManus.git
cd OpenManus
```

3. 新しい仮想環境を作成してアクティベートします：

```bash
uv venv --python 3.12
source .venv/bin/activate  # Unix/macOSの場合
# Windowsの場合：
# .venv\Scripts\activate
```

4. 依存関係をインストールします：

```bash
uv pip install -r requirements.txt
```

### ブラウザ自動化ツール（オプション）
```bash
playwright install
```

## 設定

OpenManusを使用するには、LLM APIの設定が必要です。以下の手順に従って設定してください：

1. `config`ディレクトリに`config.toml`ファイルを作成します（サンプルからコピーできます）：

```bash
cp config/config.example.toml config/config.toml
```

2. `config/config.toml`を編集してAPIキーを追加し、設定をカスタマイズします：

```toml
# グローバルLLM設定
[llm]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # 実際のAPIキーに置き換えてください
max_tokens = 4096
temperature = 0.0

# 特定のLLMモデル用のオプション設定
[llm.vision]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # 実際のAPIキーに置き換えてください
```

## クイックスタート

OpenManusを実行する一行コマンド：

```bash
python main.py
```

その後、ターミナルからプロンプトを入力してください！

MCP ツールバージョンを使用する場合は、以下を実行します：
```bash
python run_mcp.py
```

開発中のマルチエージェントバージョンを試すには、以下を実行します：

```bash
python run_flow.py
```

## OrcaRouter

[OrcaRouter](https://www.orcarouter.ai) は OpenAI 互換の AI ゲートウェイです。OpenManus は他の OpenAI 互換プロバイダーと同じ `api_type` の仕組みで接続します。認証方法ごとに 2 つの provider エントリがあり、どちらも最終的に同じ `sk-orca-...` キーで `https://api.orcarouter.ai/v1` を利用します。

| `api_type` | 認証方法 |
| --- | --- |
| `orcarouter` | 既存の `sk-orca-...` キーを `api_key` に記入、または `ORCAROUTER_API_KEY` を設定。 |
| `orcarouter-oauth` | `orcarouter login` を実行し、ブラウザーで承認（OAuth 2.0 + PKCE）。 |

```bash
# 方法 1 - 既存のキーを使う
export ORCAROUTER_API_KEY=sk-orca-...
# 方法 2 - OrcaRouter アカウントでサインイン（ブラウザーが開き、キーのコピーは不要）
orcarouter login
```

```toml
[llm]
api_type = "orcarouter"          # `orcarouter login` 後は "orcarouter-oauth"
model = "orcarouter/auto"
base_url = "https://api.orcarouter.ai/v1"
api_key = "your OrcaRouter api key"   # 空のままにすると保存済み／環境変数のキーを使用
max_tokens = 16000
temperature = 0.0

[llm.vision]
api_type = "orcarouter"
model = "google/gemini-3.5-flash"     # カタログ内の画像入力対応モデル
base_url = "https://api.orcarouter.ai/v1"
api_key = "your OrcaRouter api key"
```

キーはあなたの OrcaRouter アカウントに属し、課金もあなたに帰属し、<https://www.orcarouter.ai/console/authorized-apps> からいつでも失効できます。保存先は `~/.openmanus/orcarouter.json`（パーミッション `0600`）で、本リポジトリには書き込まれません。

```bash
orcarouter login            # 認証（API キー、またはブラウザーによる PKCE）
orcarouter login --code X   # 同意画面にコードが表示された場合の PKCE 完了
orcarouter status           # 保存済みクレデンシャルと再認証の要否を確認
orcarouter models           # GET /v1/models から、そのキーで利用可能なモデルを一覧
orcarouter logout           # 保存済みクレデンシャルを削除
```

セルフホストの OrcaRouter は `ORCA_BASE_URL`（単一の共有オリジン）、または `ORCA_AUTH_BASE_URL` / `ORCA_API_BASE_URL`（認証と推論を分離）で自前のオリジンに向けられます。ループバック以外では HTTPS が必須です。

モデル ID はカタログの表記そのまま、vendor 名前空間付きで扱います（`orcarouter/auto`、`google/gemini-3.5-flash`）。すべての入口が同じモデルカタログサービスを通して候補を解決するため、セレクタが提示する選択肢は常にカタログが裏付けたモデルです。chat 入口は画像・動画・rerank モデルを除外し、スクリーンショットを送る入口はカタログ記録で `image` 入力を明示しているモデルだけを提示します。テキスト専用モデルに画像を添付した場合は、画像を黙って捨てずにモデル ID と対処方法を示して拒否します。`orcarouter models` は同じ絞り込み結果を能力ごとに表示し、現在の能力では許可されなくなった保存済みモデルに印を付けます。


## カスタムマルチエージェントの追加

現在、一般的なOpenManusエージェントに加えて、データ分析とデータ可視化タスクに適したDataAnalysisエージェントが組み込まれています。このエージェントを`config.toml`の`run_flow`に追加することができます。

```toml
# run-flowのオプション設定
[runflow]
use_data_analysis_agent = true     # デフォルトでは無効、trueに変更すると有効化されます
```

これに加えて、エージェントが正常に動作するために必要な依存関係をインストールする必要があります：[具体的なインストールガイド](app/tool/chart_visualization/README_ja.md##インストール)


## 貢献方法

我々は建設的な意見や有益な貢献を歓迎します！issueを作成するか、プルリクエストを提出してください。

または @mannaandpoem に📧メールでご連絡ください：mannaandpoem@gmail.com

**注意**: プルリクエストを送信する前に、pre-commitツールを使用して変更を確認してください。`pre-commit run --all-files`を実行してチェックを実行します。

## コミュニティグループ
Feishuのネットワーキンググループに参加して、他の開発者と経験を共有しましょう！

<div align="center" style="display: flex; gap: 20px;">
    <img src="assets/community_group.jpg" alt="OpenManus 交流群" width="300" />
</div>

## スター履歴

[![Star History Chart](https://api.star-history.com/svg?repos=FoundationAgents/OpenManus&type=Date)](https://star-history.com/#FoundationAgents/OpenManus&Date)

## 謝辞

このプロジェクトの基本的なサポートを提供してくれた[anthropic-computer-use](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo)
と[browser-use](https://github.com/browser-use/browser-use)に感謝します！

さらに、[AAAJ](https://github.com/metauto-ai/agent-as-a-judge)、[MetaGPT](https://github.com/geekan/MetaGPT)、[OpenHands](https://github.com/All-Hands-AI/OpenHands)、[SWE-agent](https://github.com/SWE-agent/SWE-agent)にも感謝します。

また、Hugging Face デモスペースをサポートしてくださった阶跃星辰 (stepfun)にも感謝いたします。

OpenManusはMetaGPTのコントリビューターによって構築されました。このエージェントコミュニティに大きな感謝を！

## 引用
```bibtex
@misc{openmanus2025,
  author = {Xinbing Liang and Jinyu Xiang and Zhaoyang Yu and Jiayi Zhang and Sirui Hong and Sheng Fan and Xiao Tang},
  title = {OpenManus: An open-source framework for building general AI agents},
  year = {2025},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.15186407},
  url = {https://doi.org/10.5281/zenodo.15186407},
}
```
