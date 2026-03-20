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

CHROMA_PATH = os.environ.get("CHROMA_PATH", str(Path(__file__).resolve().parent.parent / ".chromadb"))
DOCS_PATH = os.environ.get("DOCS_PATH", str(Path(__file__).resolve().parent.parent / "docs"))
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "docs")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "50"))


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME)


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
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
                # Split long paragraphs
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

    # Apply overlap
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:]
            overlapped.append(prev_tail + " " + chunks[i])
        chunks = overlapped

    return chunks


def load_markdown(path):
    text = Path(path).read_text(encoding="utf-8")
    # Strip YAML front matter
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
    # Remove scripts and styles
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    return converter.handle(str(soup))


def make_id(source, chunk_index):
    h = hashlib.md5(source.encode()).hexdigest()[:12]
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


def index_all_docs():
    collection = get_collection()
    docs_path = Path(DOCS_PATH)
    total_docs = 0
    total_chunks = 0

    for path in sorted(docs_path.rglob("*")):
        if path.suffix == ".md":
            text = load_markdown(path)
            n = index_document(text, str(path), "markdown", collection)
        elif path.suffix == ".pdf":
            text = load_pdf(path)
            n = index_document(text, str(path), "pdf", collection)
        else:
            continue
        total_docs += 1
        total_chunks += n
        print(f"  {path.name}: {n} chunks")

    print(f"Indexed {total_docs} document(s) ({total_chunks} chunks total)")
    return total_docs, total_chunks
