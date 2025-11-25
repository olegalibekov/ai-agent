# search.py - Скрипт для поиска по существующему индексу

from rag_indexer import OllamaRAG


def main():
    """Поиск по существующему индексу"""
    print("=" * 80)
    print("RAG Поиск")
    print("=" * 80)

    # Загрузка индекса
    index_path = input("\nПуть к индексу (по умолчанию 'rag_index'): ").strip()
    if not index_path:
        index_path = 'rag_index'

    rag = OllamaRAG()

    try:
        rag.load(index_path)
    except Exception as e:
        print(f"\n❌ Ошибка загрузки индекса: {e}")
        print("Сначала создайте индекс с помощью rag_indexer.py")
        return

    # Интерактивный поиск
    print("\n" + "=" * 80)
    print("Поиск по документам")
    print("=" * 80)

    while True:
        query = input("\nВаш вопрос (или 'exit' для выхода): ").strip()
        if query.lower() in ['exit', 'quit', 'выход']:
            break

        if not query:
            continue

        results = rag.search(query, top_k=1)

        print("\n" + "-" * 80)
        print(f"Найдено {len(results)} релевантных чанков:")
        print("-" * 80)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. [{result['metadata']['source']}] "
                  f"Чанк {result['metadata']['chunk_id'] + 1}/{result['metadata']['total_chunks']}")
            print(f"   Релевантность: {result['score']:.4f}")
            print(f"   {result['text'][:300]}...")


if __name__ == '__main__':
    main()