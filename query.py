from indexer import get_collection


def retrieve(question, n_results=5):
    collection = get_collection()
    results = collection.query(query_texts=[question], n_results=n_results)
    contexts = []
    for i in range(len(results["ids"][0])):
        contexts.append(
            {
                "text": results["documents"][0][i],
                "source": results["metadatas"][0][i]["source"],
                "distance": results["distances"][0][i],
            }
        )
    return contexts


def ask(question, n_results=5):
    contexts = retrieve(question, n_results)
    if not contexts:
        print("インデックスにドキュメントがありません。先に `index` を実行してください。")
        return
    for ctx in contexts:
        print("---")
        print(ctx["text"])
        print(f"(source: {ctx['source']}, distance: {ctx['distance']:.4f})")
    print("---")
