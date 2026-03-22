from indexer import get_collection


def retrieve(question, n_results=5):
    collection = get_collection()
    results = collection.query(query_texts=[question], n_results=n_results)
    contexts = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        ctx = {
            "text": results["documents"][0][i],
            "source": meta["source"],
            "distance": results["distances"][0][i],
        }
        if meta.get("theme"):
            ctx["theme"] = meta["theme"]
        if meta.get("title"):
            ctx["title"] = meta["title"]
        contexts.append(ctx)
    return contexts


def ask(question, n_results=5):
    contexts = retrieve(question, n_results)
    if not contexts:
        print("インデックスにドキュメントがありません。先に `index` を実行してください。")
        return contexts
    for ctx in contexts:
        print("---")
        print(ctx["text"])
        tags = []
        if ctx.get("theme"):
            tags.append(f"theme: {ctx['theme']}")
        if ctx.get("title"):
            tags.append(f"title: {ctx['title']}")
        tag_str = f", {', '.join(tags)}" if tags else ""
        print(f"(source: {ctx['source']}, distance: {ctx['distance']:.4f}{tag_str})")
    print("---")
    return contexts
