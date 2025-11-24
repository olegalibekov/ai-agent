# example_usage.py - Пример использования в коде

from rag_indexer import OllamaRAG, load_documents_from_folder


def example_build_index():
    """Пример создания индекса"""
    # Инициализация
    rag = OllamaRAG()

    # Загрузка документов
    documents = load_documents_from_folder('./documents')

    # Индексация
    rag.add_documents(documents)

    # Сохранение
    rag.save('my_index')

    print("✓ Индекс создан и сохранён")


def example_search():
    """Пример поиска"""
    # Загрузка индекса
    rag = OllamaRAG()
    rag.load('my_index')

    # Поиск
    results = rag.search('как работает RAG?', top_k=3)

    # Вывод результатов
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['metadata']['source']}")
        print(f"   Score: {result['score']:.4f}")
        print(f"   {result['text'][:200]}...")


def example_manual_documents():
    """Пример с ручным добавлением документов"""
    rag = OllamaRAG()

    # Документы напрямую
    documents = [
        {
            'text': 'RAG это Retrieval-Augmented Generation...',
            'source': 'manual_doc_1'
        },
        {
            'text': 'Embeddings представляют текст в виде векторов...',
            'source': 'manual_doc_2'
        }
    ]

    rag.add_documents(documents)
    rag.save('manual_index')


if __name__ == '__main__':
    # Раскомментируйте нужный пример

    # example_build_index()
    # example_search()
    example_manual_documents()