# グラフ可視化ツール

グラフ可視化ツールは、Pythonを使用してデータ処理コードを生成し、最終的に[@visactor/vmind](https://github.com/VisActor/VMind)を呼び出してグラフのspec結果を得ます。グラフのレンダリングには[@visactor/vchart](https://github.com/VisActor/VChart)を使用します。

## インストール (Mac / Linux)

1. Node >= 18をインストール

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
# nvmを有効化、例としてBashを使用
source ~/.bashrc
# その後、最新の安定版Nodeをインストール
nvm install node
# 使用を有効化、例えば最新の安定版が22の場合、use 22
nvm use 22
```

2. 依存関係をインストール

```bash
cd app/tool/chart_visualization
npm install
```

## インストール (Windows)
1. nvm-windowsをインストール

    [GitHub公式サイト](https://github.com/coreybutler/nvm-windows?tab=readme-ov-file#readme)から最新バージョンの`nvm-setup.exe`をダウンロードしてインストール

2. nvmを使用してNodeをインストール

```powershell
# その後、最新の安定版Nodeをインストール
nvm install node
# 使用を有効化、例えば最新の安定版が22の場合、use 22
nvm use 22
```

3. 依存関係をインストール

```bash
# 現在のリポジトリで適切な位置に移動
cd app/tool/chart_visualization
npm install
```

## ツール
### python_execute

Pythonコードを使用してデータ分析（データ可視化を除く）に必要な部分を実行します。これにはデータ処理、データ要約、レポート生成、および一般的なPythonスクリプトコードが含まれます。

#### 入力
```typescript
{
  // コードタイプ：データ処理/データレポート/その他の一般的なタスク
  code_type: "process" | "report" | "others"
  // 最終実行コード
  code: string;
}
```

#### 出力
Python実行結果、中間ファイルの保存とprint出力結果を含む

### visualization_preparation

データ可視化の準備ツールで、2つの用途があります。

#### Data -> Chart
データから分析に必要なデータ(.csv)と対応する可視化の説明を抽出し、最終的にJSON設定ファイルを出力します。

#### Chart + Insight -> Chart
既存のグラフと対応するデータインサイトを選択し、データインサイトをデータ注釈の形式でグラフに追加し、最終的にJSON設定ファイルを生成します。

#### 入力
```typescript
{
  // コードタイプ：データ可視化またはデータインサイト追加
  code_type: "visualization" | "insight"
  // 最終的なJSONファイルを生成するためのPythonコード
  code: string;
}
```

#### 出力
データ可視化の設定ファイル、`data_visualization tool`で使用

## data_visualization

`visualization_preparation`の内容に基づいて具体的なデータ可視化を生成

### 入力
```typescript
{
  // 設定ファイルのパス
  json_path: string;
  // 現在の用途、データ可視化またはインサイト注釈追加
  tool_type: "visualization" | "insight";
  // 最終成果物pngまたはhtml;htmlではvchartのレンダリングとインタラクションをサポート
  output_type: 'png' | 'html'
  // 言語、現在は中国語と英語をサポート
  language: "zh" | "en"
}
```

## 出力
最終的に'png'または'html'の形式でローカルに保存され、保存されたグラフのパスとグラフ内で発見されたデータインサイトを出力

## VMind設定

### LLM

VMind自体
