# RAG ドキュメント検索

workspace/docs/ にナレッジベースのmarkdownファイルが蓄積されている。
ユーザーの質問がこのナレッジに関連しそうな場合、以下の手順で検索して回答に活用すること。

## 検索手順

### ステップ1: クエリ拡張
RAGはembeddingベースの検索のため、短い・曖昧なクエリでは精度が低くなる。
検索前に必ずクエリを拡張すること：

- 短いクエリ（〜10文字）は30〜60文字程度に拡張する
- 同義語・関連語を追加する（例: 「AI教育」→「AI技術 教育改革 個別最適化 学習アルゴリズム」）
- ナレッジベースで使われる特徴的な語彙を含める：
  記号創発、守破離、ダーウィニズム、Buddhism、レコンキスタ、転送世代、煩悩駆動開発、
  クオリア、オートマトン、フロー理論、ニューロダイバーシティ、マイクロサービス、
  バージョンアップ、OSS、玄同 など
- 必要に応じて複数の異なるクエリで検索する

### ステップ2: 検索実行

```bash
cd /home/delta/workspace/rag && .venv/bin/python rag_cli.py query "拡張したクエリ" --n-results 5
```

### ステップ3: 結果の評価
- distance < 0.8: 高精度ヒット。信頼してよい
- distance 0.8〜1.0: 関連性あり。文脈を確認して判断
- distance > 1.0: 精度低。参考程度。別クエリで再検索を検討

## note記事のテーマ構造
docs/note_articles/ にはテーマ別にnote記事が格納されている：
ai_technology, buddhism, children_rights, education, lotus_sutra,
makiguchi, politics, self_exploration, tao_te_ching, theravada

各チャンクにはtheme, titleメタデータが付与されており、検索結果に表示される。

## インデックスの更新

会話の最初にRAGを使う前に、workspace/docs/ 内のファイルの更新日時とChromaDBの更新日時を比較し、
docsの方が新しければインデックスを再構築すること:

```bash
# docsがChromaDBより新しいか確認
[ "$(find /home/delta/workspace/docs -name '*.md' -newer /home/delta/workspace/.chromadb/chroma.sqlite3 2>/dev/null)" ] && echo "NEEDS_REINDEX" || echo "UP_TO_DATE"
```

NEEDS_REINDEXの場合のみ実行:

```bash
cd /home/delta/workspace/rag && .venv/bin/python rag_cli.py index
```

## Webページの追加

```bash
cd /home/delta/workspace/rag && .venv/bin/python rag_cli.py add-url "URL"
```

## エージェント記憶（海馬）

`~/.claude/agent-memory/` 配下の diary / memory をエージェントごとのコレクションにインデックスする。

### インデックス更新

```bash
cd /home/delta/workspace/rag && .venv/bin/python rag_cli.py index-memory
```

コレクション名: `{name}-diary` / `{name}-memory`（例: `mephi-diary`, `delta-memory`）

### エージェント記憶の検索

```bash
cd /home/delta/workspace/rag && .venv/bin/python rag_cli.py query-memory "クエリ" --agent mephi --type diary
```

- `--agent`: エージェント名（mephi / alice / delta 等）
- `--type`: `diary`（エピソード記憶）または `memory`（活動ログ）
