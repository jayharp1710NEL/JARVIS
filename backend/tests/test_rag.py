from app.rag.chunking import chunk_text
from app.rag.embeddings import HashingEmbedder, get_embedder
from app.rag.ingest import delete_indexed_file, ingest_bytes, list_indexed_files
from app.rag.loaders import UnsupportedFileType, load_bytes
from app.rag.retrieval import retrieve, to_citations


def test_chunking_overlap():
    text = "\n\n".join(f"Paragraph number {i} with some content about topic {i}." for i in range(40))
    chunks = chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) > 1
    assert all(len(c.text) <= 400 for c in chunks)


def test_hashing_embedder_is_deterministic():
    emb = HashingEmbedder(dim=128)
    a = emb.embed_one("local first ai agent")
    b = emb.embed_one("local first ai agent")
    assert (a == b).all()
    # normalized
    assert abs(float((a * a).sum()) - 1.0) < 1e-5


def test_loaders_text_and_csv():
    doc = load_bytes("data.csv", b"name,age\nAlice,30\nBob,25")
    assert "Alice" in doc.full_text
    md = load_bytes("readme.md", b"# Title\nbody")
    assert "Title" in md.full_text


def test_unsupported_file_type():
    try:
        load_bytes("image.png", b"\x89PNG")
        assert False
    except UnsupportedFileType:
        pass


def test_ingest_and_retrieve():
    content = (
        "JARVIS-LOCAL is a local-first agent.\n\n"
        "The default vector store is a numpy cosine similarity store.\n\n"
        "Memory is stored in SQLite and retrieval uses local embeddings."
    )
    res = ingest_bytes("notes.md", content.encode())
    assert res.num_chunks >= 1
    assert any(f["filename"] == "notes.md" for f in list_indexed_files())

    chunks = retrieve("what vector store does it use?", top_k=2)
    assert chunks
    assert "vector store" in chunks[0].text.lower()
    cites = to_citations(chunks)
    assert cites[0].filename == "notes.md"
    assert cites[0].chunk_id

    assert delete_indexed_file(res.file_id) is True
    assert retrieve("vector store", top_k=2) == []


def test_get_embedder_falls_back_to_hashing():
    # default config uses hashing; ensure we always get a working embedder
    emb = get_embedder()
    v = emb.embed(["hello", "world"])
    assert v.shape[0] == 2
