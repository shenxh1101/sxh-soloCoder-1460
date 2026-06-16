import json
import os
import uuid
from typing import List, Optional

from models import Project


DATA_FILE = "projects.json"


class ProjectRepository:
    def __init__(self, data_dir: str = "."):
        self.data_file = os.path.join(data_dir, DATA_FILE)

    def _load_all(self) -> List[dict]:
        if not os.path.exists(self.data_file):
            return []
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _save_all(self, projects: List[dict]) -> None:
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)

    def get_all(self) -> List[Project]:
        data = self._load_all()
        return [Project.from_dict(d) for d in data]

    def get_by_id(self, project_id: str) -> Optional[Project]:
        projects = self._load_all()
        for d in projects:
            if d["id"] == project_id:
                return Project.from_dict(d)
        return None

    def add(self, project: Project) -> None:
        projects = self._load_all()
        projects.append(project.to_dict())
        self._save_all(projects)

    def update(self, project: Project) -> bool:
        projects = self._load_all()
        for i, d in enumerate(projects):
            if d["id"] == project.id:
                projects[i] = project.to_dict()
                self._save_all(projects)
                return True
        return False

    def delete(self, project_id: str) -> bool:
        projects = self._load_all()
        new_projects = [d for d in projects if d["id"] != project_id]
        if len(new_projects) != len(projects):
            self._save_all(new_projects)
            return True
        return False

    def generate_id(self) -> str:
        return str(uuid.uuid4())[:8]
