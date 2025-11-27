import re
from pathlib import Path

from rag_indexer import OllamaRAG, load_documents_from_folder

QUESTIONS = [
    "Какие подходы к разбиению текста на чанки перечислены и каковы их плюсы и минусы?",
    "Почему важно использовать overlap при разбиении текста на чанки и какие ошибки бывают при чанкинге?",
    "Что такое Retrieval-Augmented Generation (RAG) и из каких основных компонентов он состоит?",
    "Зачем использовать RAG в корпоративных приложениях и какие преимущества это даёт?",
    "Какие ключевые функциональные требования предъявляются к поисковому чат-боту для сотрудников компании?",
]


def build_or_load_index(
        docs_folder: str = "/Users/fehty/PycharmProjects/ai-agent/documents/",
        index_path: str = "rag_index",
        similarity_threshold: float = 0.8,
) -> OllamaRAG:
    """
    Пытается загрузить существующий индекс.
    Если индекс не найден — строит его по txt/md/py/pdf в docs_folder и сохраняет.
    """
    rag = OllamaRAG(similarity_threshold=similarity_threshold)

    index_dir = Path(index_path)
    vectors_path = index_dir / "vectors.faiss"
    data_path = index_dir / "data.pkl"

    if vectors_path.exists() and data_path.exists():
        print(f"✓ Найден существующий индекс в '{index_path}', загружаю...")
        rag.load(index_path)
        return rag

    print(f"⚠ Индекс '{index_path}' не найден, строю новый по документам из '{docs_folder}'...")

    docs = load_documents_from_folder(docs_folder)
    if not docs:
        raise RuntimeError(f"В папке '{docs_folder}' не найдено ни одного поддерживаемого документа")

    rag.add_documents(docs)
    rag.save(index_path)
    return rag


def has_citations(answer: str) -> bool:
    """Простейшая проверка: есть ли в ответе ссылки вида [1], [2], ..."""
    return re.search(r"\[\d+\]", answer) is not None


def main():
    docs_folder = "/Users/fehty/PycharmProjects/ai-agent/documents/"
    index_path = "rag_index"

    if not Path(docs_folder).exists():
        print(f"⚠ Папка '{docs_folder}' не существует. Создай её и положи туда 1.txt, 2.txt, 3.txt.")
        return

    rag = build_or_load_index(
        docs_folder=docs_folder,
        index_path=index_path,
        similarity_threshold=0.8,
    )

    print("\n" + "=" * 80)
    print("Тестирование RAG на 5 вопросах (проверка обязательных ссылок на источники)")
    print("=" * 80)

    for i, q in enumerate(QUESTIONS, start=1):
        print("\n" + "-" * 80)
        print(f"[Вопрос {i}] {q}")
        print("-" * 80)

        try:
            result = rag.answer_with_rag(
                question=q,
                model="llama3",
                top_k=5,
                max_context_chars=8000,
                min_score=rag.similarity_threshold,
            )
        except Exception as e:
            print(f"❌ Ошибка при запросе к LLM: {e}")
            continue

        answer = result["answer"]
        print("\nОтвет модели:")
        print(answer)

        ok = has_citations(answer)
        print("\nПроверка ссылок:")
        print(f"Содержит ли ответ ссылки вида [N]? -> {'ДА' if ok else 'НЕТ'}")

        if result["chunks"]:
            print("\nИспользованные источники (по данным ретривера):")
            for ch in result["chunks"]:
                meta = ch["metadata"]
                ref_id = ch.get("ref_id", "?")
                print(
                    f"  [{ref_id}] {meta['source']} "
                    f"(чанк {meta['chunk_id'] + 1}/{meta['total_chunks']}, score={ch['score']:.4f})"
                )
        else:
            print("\nРетраивер не вернул ни одного чанка (контекст пустой).")

    print("\n" + "=" * 80)
    print("Тестирование завершено.")
    print("=" * 80)


if __name__ == "__main__":
    main()
