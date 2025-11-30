import re
from pathlib import Path
from typing import List, Dict

from rag_indexer import OllamaRAG, load_documents_from_folder

HISTORY_TURNS_TO_USE = 5
EXIT_COMMANDS = {"exit", "quit", "выход"}


def build_or_load_index(
        docs_folder: str = "./documents",
        index_path: str = "rag_index",
        similarity_threshold: float = 0.8,
) -> OllamaRAG:
    rag = OllamaRAG(similarity_threshold=similarity_threshold)

    index_dir = Path(index_path)
    if (index_dir / "vectors.faiss").exists() and (index_dir / "data.pkl").exists():
        print(f"✓ Загружаю существующий индекс '{index_path}'...")
        rag.load(index_path)
        return rag

    print(f"⚠ Индекс не найден, создаю новый...")

    docs = load_documents_from_folder(docs_folder)
    rag.add_documents(docs)
    rag.save(index_path)
    return rag


def format_history(history: List[Dict[str, str]], max_chars: int = 2000) -> str:
    if not history:
        return "История диалога пуста."

    recent = history[-HISTORY_TURNS_TO_USE:]
    parts = ["История диалога (последние реплики):"]

    for turn in recent:
        role = "Пользователь" if turn["role"] == "user" else "Ассистент"
        text = turn["content"].strip()
        if len(text) > 400:
            text = text[:400] + "..."
        parts.append(f"{role}: {text}")

    result = "\n".join(parts)
    return result[-max_chars:]


def has_citations(answer: str) -> bool:
    return re.search(r"\[\d+\]", answer) is not None


def main():
    docs_folder = "./documents"
    index_path = "rag_index"

    rag = build_or_load_index(docs_folder, index_path)

    chat_history: List[Dict[str, str]] = []

    print("\n" + "=" * 80)
    print("Мини-чат с памятью на RAG")
    print("=" * 80)
    print("Введите вопрос. Для выхода: exit / quit / выход\n")

    while True:
        user_input = input("Ты: ").strip()
        if not user_input:
            continue

        if user_input.lower() in EXIT_COMMANDS:
            print("Ассистент: До встречи!")
            break

        chat_history.append({"role": "user", "content": user_input})

        history_block = format_history(chat_history)

        question = (
            f"{history_block}\n\n"
            f"Текущий вопрос пользователя: {user_input}\n\n"
            "Ответь, учитывая историю диалога и контекст документов."
        )

        try:
            result = rag.answer_with_rag(
                question=question,
                model="llama3",
                top_k=5,
                max_context_chars=8000,
                min_score=rag.similarity_threshold,
            )
        except Exception as e:
            # здесь ЛЮБАЯ ошибка от эмбеддингов/LLM не роняет чат
            error_text = f"❌ Ошибка при запросе к модели/эмбеддингам: {e}"
            print("\nАссистент:")
            print(error_text)

            # при желании можем тоже сохранять в историю
            chat_history.append({"role": "assistant", "content": error_text})
            print("\n" + "-" * 80 + "\n")
            continue

        answer = result["answer"]
        print("\nАссистент:")
        print(answer)

        print("\nИсточники:")
        if result["chunks"]:
            for ch in result["chunks"]:
                meta = ch["metadata"]
                print(
                    f"  [{ch['ref_id']}] {meta['source']} "
                    f"(чанк {meta['chunk_id'] + 1}/{meta['total_chunks']}), score={ch['score']:.4f}"
                )
        else:
            print("  Контекст пустой.")

        chat_history.append({"role": "assistant", "content": answer})

        print("\n" + "-" * 80 + "\n")


if __name__ == "__main__":
    main()
