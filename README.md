# RAG - Claude Code のための知識保持システム

Claude Code (CLI) がローカルのドキュメントを検索・参照できるようにする RAG (Retrieval-Augmented Generation) システム。

## 背景

Claude Code はセッションごとにコンテキストがリセットされるため、プロジェクト固有の知識や過去の意思決定を会話をまたいで保持することが難しい。
このシステムでは `workspace/docs/` に蓄積した Markdown / PDF ドキュメントを ChromaDB にインデックスし、CLAUDE.md の指示によって Claude Code が自動的に検索・参照する仕組みを構築している。

## 仕組み

```
workspace/docs/  ──index──▶  ChromaDB (.chromadb/)
                                  │
CLAUDE.md の指示  ──────────▶  Claude Code
                                  │ query
                                  ▼
                            関連チャンクを取得して回答に活用
```

1. **インデックス**: `workspace/docs/` 内の Markdown / PDF をチャンク分割し、ChromaDB のベクトルストアに格納
2. **検索**: ユーザーの質問に関連するチャンクをベクトル類似度で検索
3. **自動連携**: CLAUDE.md に検索コマンドを記述し、Claude Code が会話中に必要に応じて自動実行

### CLAUDE.md による自動化

Claude Code は `CLAUDE.md` をセッション開始時に読み込む。ここに RAG 検索コマンドと実行条件を記述することで、Claude 自身が判断してドキュメントを検索し、回答に活用する。

## セットアップ

### 1. RAG ツールのインストール

```bash
cd workspace/rag
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. ドキュメントの配置

`workspace/docs/` にナレッジとなる Markdown / PDF ファイルを配置し、初回インデックスを実行する。

```bash
.venv/bin/python rag_cli.py index
```

### 3. CLAUDE.md の設定

Claude Code がRAGを自動利用するには、`CLAUDE.md`（プロジェクトルートまたは `~` に配置）に検索コマンドと運用ルールを記述する必要がある。

記述例:

````markdown
# RAG ドキュメント検索

workspace/docs/ にナレッジベースのドキュメントが蓄積されている。
ユーザーの質問がこのナレッジに関連しそうな場合、以下のコマンドで検索して回答に活用すること。

## 検索コマンド

```bash
cd /path/to/rag && .venv/bin/python rag_cli.py query "検索クエリ" --n-results 5
```

## インデックスの更新

会話の最初にRAGを使う前に、docs の更新日時と ChromaDB の更新日時を比較し、
docs の方が新しければインデックスを再構築すること:

```bash
[ "$(find /path/to/docs -name '*.md' -newer /path/to/.chromadb/chroma.sqlite3 2>/dev/null)" ] && echo "NEEDS_REINDEX" || echo "UP_TO_DATE"
```

NEEDS_REINDEX の場合のみ実行:

```bash
cd /path/to/rag && .venv/bin/python rag_cli.py index
```
````

ポイント:
- **検索の判断を Claude に委ねる**: 「関連しそうな場合」と書くことで、Claude 自身が質問内容を見て検索すべきか判断する
- **インデックスの鮮度管理**: ファイルのタイムスタンプ比較で、必要なときだけ再インデックスする指示を入れる
- パスは環境に合わせて絶対パスで記述する

### 4. パーミッションの設定（推奨）

Claude Code はデフォルトで Bash コマンドの実行時に確認を求める。RAG コマンドを毎回許可するのは煩雑なので、`~/.claude/settings.local.json` に許可ルールを追加しておくとよい。

```json
{
  "permissions": {
    "allow": [
      "Bash(.venv/bin/python rag_cli.py query:*)",
      "Bash(.venv/bin/python rag_cli.py index)",
      "Bash(.venv/bin/python rag_cli.py add-url:*)"
    ]
  }
}
```

これにより、RAG の検索・インデックス・URL追加コマンドが確認なしで実行される。

## 使い方

```bash
# ドキュメントのインデックス
.venv/bin/python rag_cli.py index

# 質問で検索
.venv/bin/python rag_cli.py query "検索クエリ" --n-results 5

# Web ページを追加
.venv/bin/python rag_cli.py add-url "https://example.com/page"
```

## 対応フォーマット

- Markdown (`.md`) - YAML front matter は自動除去
- PDF (`.pdf`) - テキスト抽出
- Web ページ - HTML を取得しテキスト変換

## 技術スタック

- [ChromaDB](https://www.trychroma.com/) - ベクトルデータベース（ローカル永続化）
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) - Anthropic の CLI エージェント
