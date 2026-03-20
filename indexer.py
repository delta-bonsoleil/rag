import hashlib
import os
import re
from pathlib import Path

import chromadb
import html2text
import pdfplumber
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()


def _safe_int(value, default):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


CHROMA_PATH = os.environ.get("CHROMA_PATH", str(Path(__file__).resolve().parent.parent / ".chromadb"))
DOCS_PATH = os.environ.get("DOCS_PATH", str(Path(__file__).resolve().parent.parent / "docs"))
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "docs")
CHUNK_SIZE = _safe_int(os.environ.get("CHUNK_SIZE"), 500)
CHUNK_OVERLAP = _safe_int(os.environ.get("CHUNK_OVERLAP"), 50)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def get_collection():
    return _get_client().get_or_create_collection(name=COLLECTION_NAME)


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    if not text or not text.strip():
        return []

    paragraphs = re.split(r"\n\n+", text.strip())
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) <= chunk_size:
                current = para
            else:
                words = para.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= chunk_size:
                        current = f"{current} {word}" if current else word
                    else:
                        if current:
                            chunks.append(current)
                        current = word
    if current:
        chunks.append(current)

    # Apply overlap at word boundary
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            words = prev.split()
            tail_words = []
            tail_len = 0
            for w in reversed(words):
                if tail_len + len(w) + 1 > overlap:
                    break
                tail_words.insert(0, w)
                tail_len += len(w) + 1
            if tail_words:
                overlapped.append(" ".join(tail_words) + " " + chunks[i])
            else:
                overlapped.append(chunks[i])
        chunks = overlapped

    return chunks


def load_markdown(path):
    text = Path(path).read_text(encoding="utf-8")
    text = re.sub(r"^---.*?---\n", "", text, count=1, flags=re.DOTALL)
    return text


def load_pdf(path):
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
    return "\n\n".join(pages)


def fetch_url(url):
    resp = requests.get(url, timeout=30, headers={"User-Agent": "RAG-Indexer/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    return converter.handle(str(soup))


def make_id(source, chunk_index):
    h = hashlib.sha256(source.encode()).hexdigest()[:24]
    return f"{h}::chunk_{chunk_index}"


def index_document(text, source, doc_type, collection=None):
    if collection is None:
        collection = get_collection()
    chunks = chunk_text(text)
    if not chunks:
        return 0
    ids = [make_id(source, i) for i in range(len(chunks))]
    metadatas = [
        {"source": source, "doc_type": doc_type, "chunk_index": i}
        for i in range(len(chunks))
    ]
    collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
    return len(chunks)


def _get_indexed_sources(collection):
    """コレクション内の全ソースを取得"""
    result = collection.get(include=["metadatas"])
    sources = set()
    for meta in result["metadatas"]:
        sources.add(meta["source"])
    return sources


def _delete_source(collection, source):
    """指定ソースのチャンクを全削除"""
    result = collection.get(where={"source": source})
    if result["ids"]:
        collection.delete(ids=result["ids"])
    return len(result["ids"])


def index_all_docs():
    collection = get_collection()
    docs_path = Path(DOCS_PATH)
    total_docs = 0
    total_chunks = 0
    errors = []
    indexed_sources = set()

    for path in sorted(docs_path.rglob("*")):
        if path.suffix not in (".md", ".pdf"):
            continue
        try:
            if path.suffix == ".md":
                text = load_markdown(path)
                n = index_document(text, str(path), "markdown", collection)
            else:
                text = load_pdf(path)
                n = index_document(text, str(path), "pdf", collection)
            total_docs += 1
            total_chunks += n
            indexed_sources.add(str(path))
            print(f"  {path.name}: {n} chunks")
        except Exception as e:
            errors.append((path, e))
            print(f"  {path.name}: ERROR - {e}")

    # 削除されたドキュメントのチャンクを掃除
    existing_sources = _get_indexed_sources(collection)
    doc_sources = {s for s in existing_sources if s.startswith(str(docs_path))}
    stale = doc_sources - indexed_sources
    for source in stale:
        n = _delete_source(collection, source)
        print(f"  Removed stale: {source} ({n} chunks)")

    print(f"Indexed {total_docs} document(s) ({total_chunks} chunks total)")
    if errors:
        print(f"  {len(errors)} error(s) occurred:")
        for path, e in errors:
            print(f"    {path}: {e}")

    return total_docs, total_chunks
