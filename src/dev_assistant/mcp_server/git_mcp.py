"""
MCP Server для работы с Git репозиторием
Предоставляет информацию о текущей ветке, статусе, коммитах
"""
from pathlib import Path
import git
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="MCP Git Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GitRequest(BaseModel):
    repo_path: str


class GitInfo:
    """Класс для работы с Git репозиторием"""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.repo = None
        self._init_repo()

    def _init_repo(self):
        """Инициализирует Git репозиторий"""
        try:
            self.repo = git.Repo(self.repo_path)
        except git.InvalidGitRepositoryError:
            raise ValueError(f"Не найден Git репозиторий в {self.repo_path}")

    def get_current_branch(self) -> str:
        """Получает имя текущей ветки"""
        try:
            return self.repo.active_branch.name
        except Exception as e:
            return f"Error: {str(e)}"

    def get_branches(self) -> list:
        """Получает список всех веток"""
        try:
            return [branch.name for branch in self.repo.branches]
        except Exception as e:
            return []

    def get_status(self) -> dict:
        """Получает статус репозитория"""
        try:
            return {
                "branch": self.get_current_branch(),
                "is_dirty": self.repo.is_dirty(),
                "untracked_files": self.repo.untracked_files,
                "modified_files": [item.a_path for item in self.repo.index.diff(None)],
                "staged_files": [item.a_path for item in self.repo.index.diff('HEAD')]
            }
        except Exception as e:
            return {"error": str(e)}

    def get_recent_commits(self, limit: int = 5) -> list:
        """Получает последние коммиты"""
        try:
            commits = []
            for commit in self.repo.iter_commits(max_count=limit):
                commits.append({
                    "hash": commit.hexsha[:7],
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat()
                })
            return commits
        except Exception as e:
            return []

    def get_remote_info(self) -> dict:
        """Получает информацию о remote репозитории"""
        try:
            if not self.repo.remotes:
                return {"remotes": []}

            remotes = []
            for remote in self.repo.remotes:
                remotes.append({
                    "name": remote.name,
                    "url": list(remote.urls)[0] if remote.urls else None
                })
            return {"remotes": remotes}
        except Exception as e:
            return {"error": str(e)}


@app.post("/git/branch")
async def get_branch(request: GitRequest):
    """Получает текущую ветку"""
    try:
        git_info = GitInfo(request.repo_path)
        branch = git_info.get_current_branch()
        return {
            "current_branch": branch,
            "all_branches": git_info.get_branches()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/git/status")
async def get_status(request: GitRequest):
    """Получает полный статус репозитория"""
    try:
        git_info = GitInfo(request.repo_path)
        status = git_info.get_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/git/commits")
async def get_commits(request: GitRequest):
    """Получает последние коммиты"""
    try:
        git_info = GitInfo(request.repo_path)
        commits = git_info.get_recent_commits(limit=10)
        return {"commits": commits}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/git/info")
async def get_full_info(request: GitRequest):
    """Получает всю информацию о репозитории"""
    try:
        git_info = GitInfo(request.repo_path)
        return {
            "branch": git_info.get_current_branch(),
            "branches": git_info.get_branches(),
            "status": git_info.get_status(),
            "recent_commits": git_info.get_recent_commits(limit=5),
            "remotes": git_info.get_remote_info()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Проверка здоровья MCP сервера"""
    return {"status": "ok", "service": "MCP Git Server"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
