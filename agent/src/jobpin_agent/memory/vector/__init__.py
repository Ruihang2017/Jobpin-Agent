"""The embedded local vector store (§1.4).

EN —
The large-volume, retrieval layer's storage: a ``VectorStore`` interface + a stdlib
``SqliteVectorStore`` reference implementation (brute-force cosine NN), the
``VectorRecord`` schema, and the re-embed migration tool. A production backend
(sqlite-vec / LanceDB / Chroma, chosen by the §1.12 spike) swaps in behind the same
interface. No cloud database (local-first).

中文 —
大体量检索层的存储：一个 ``VectorStore`` 接口 + 一个仅用标准库的 ``SqliteVectorStore`` 参考实现（暴力余弦近邻）、
``VectorRecord`` 模式，以及重嵌入迁移工具。生产后端（由 §1.12 spike 选定的 sqlite-vec / LanceDB / Chroma）在同一
接口背后替换。无云数据库（本地优先）。
"""
