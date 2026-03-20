#!/usr/bin/env python3
import argparse
import sys

from indexer import fetch_url, get_collection, index_all_docs, index_document
from query import ask


def cmd_index(args):
    from indexer import DOCS_PATH
    print(f"Indexing {DOCS_PATH} ...")
    index_all_docs()


def cmd_query(args):
    ask(args.question, n_results=args.n_results)


def cmd_add_url(args):
    print(f"Fetching {args.url} ...")
    text = fetch_url(args.url)
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

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {"index": cmd_index, "query": cmd_query, "add-url": cmd_add_url}
    commands[args.command](args)


if __name__ == "__main__":
    main()
