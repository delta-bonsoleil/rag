#!/usr/bin/env python3
import argparse
import sys

from indexer import DOCS_PATH, fetch_url, get_collection, index_agent_memory, index_all_docs, index_document
from query import ask


def cmd_index(args):
    print(f"Indexing {DOCS_PATH} ...")
    index_all_docs()


def cmd_index_memory(args):
    index_agent_memory(args.path or None)


def cmd_query(args):
    ask(args.question, n_results=args.n_results)


def cmd_query_memory(args):
    collection_name = f"{args.agent}-{args.type}"
    print(f"Querying [{collection_name}] ...")
    ask(args.question, n_results=args.n_results, collection_name=collection_name)


def cmd_add_url(args):
    print(f"Fetching {args.url} ...")
    try:
        text = fetch_url(args.url)
    except Exception as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Fetched ({len(text)} chars)")
    collection = get_collection()
    n = index_document(text, args.url, "web", collection)
    print(f"Indexed {n} chunks")


def main():
    parser = argparse.ArgumentParser(description="RAG CLI - ChromaDB + Claude")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("index", help="Index all docs in workspace/docs/")

    p_query = sub.add_parser("query", help="Ask a question")
    p_query.add_argument("question", help="Question to ask")
    p_query.add_argument("--n-results", type=int, default=5, help="Number of chunks to retrieve")

    p_url = sub.add_parser("add-url", help="Fetch and index a web page")
    p_url.add_argument("url", help="URL to fetch")

    p_index_mem = sub.add_parser("index-memory", help="Index agent-memory into per-agent collections")
    p_index_mem.add_argument("--path", default=None, help="Path to agent-memory root (default: ~/.claude/agent-memory)")

    p_query_mem = sub.add_parser("query-memory", help="Query agent memory collection")
    p_query_mem.add_argument("question", help="Question to ask")
    p_query_mem.add_argument("--agent", required=True, help="Agent name (e.g. mephi)")
    p_query_mem.add_argument("--type", choices=["diary", "memory"], default="diary", help="Memory type (default: diary)")
    p_query_mem.add_argument("--n-results", type=int, default=5, help="Number of chunks to retrieve")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "index": cmd_index,
        "query": cmd_query,
        "add-url": cmd_add_url,
        "index-memory": cmd_index_memory,
        "query-memory": cmd_query_memory,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
