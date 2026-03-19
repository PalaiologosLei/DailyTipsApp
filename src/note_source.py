from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen
import zipfile


class NoteSourceError(RuntimeError):
    pass


@dataclass(slots=True)
class GitHubRepoSpec:
    owner: str
    repo: str
    branch: str | None
    subpath: str


@dataclass(slots=True)
class MaterializedNotesSource:
    notes_dir: Path
    description: str
    cleanup_dir: Path | None = None

    def cleanup(self) -> None:
        if self.cleanup_dir and self.cleanup_dir.exists():
            shutil.rmtree(self.cleanup_dir, ignore_errors=True)


def materialize_notes_source(
    repo_dir: Path, notes_dir: Path | None, github_url: str | None
) -> MaterializedNotesSource:
    if notes_dir is not None and github_url is not None:
        raise NoteSourceError("Choose either a local notes directory or a GitHub URL, not both.")
    if notes_dir is None and github_url is None:
        raise NoteSourceError("A notes source is required.")

    if notes_dir is not None:
        return MaterializedNotesSource(notes_dir=notes_dir, description=f"local directory: {notes_dir}")

    assert github_url is not None
    return _download_github_repo(repo_dir, github_url)


def parse_github_url(url: str) -> GitHubRepoSpec:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.netloc != "github.com":
        raise NoteSourceError("GitHub URL must look like https://github.com/owner/repo")

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise NoteSourceError("GitHub URL must include both owner and repository name.")

    owner, repo = parts[0], parts[1]
    branch: str | None = None
    subpath = ""

    if len(parts) >= 4 and parts[2] == "tree":
        branch = parts[3]
        subpath = "/".join(parts[4:])
    elif len(parts) > 2:
        raise NoteSourceError("Supported GitHub URLs are repository root URLs or /tree/<branch>/<path> URLs.")

    return GitHubRepoSpec(owner=owner, repo=repo, branch=branch, subpath=subpath)


def _download_github_repo(repo_dir: Path, github_url: str) -> MaterializedNotesSource:
    spec = parse_github_url(github_url)
    temp_root = repo_dir / ".tmp_downloads"
    temp_root.mkdir(parents=True, exist_ok=True)

    repo_key = f"{spec.owner}_{spec.repo}"
    download_root = temp_root / repo_key
    if download_root.exists():
        shutil.rmtree(download_root)
    download_root.mkdir(parents=True, exist_ok=True)

    archive_path = download_root / "repo.zip"

    branches = [spec.branch] if spec.branch else ["main", "master"]
    last_error: Exception | None = None

    for branch in branches:
        try:
            _download_archive(spec.owner, spec.repo, branch, archive_path)
            extracted_root = _extract_archive(archive_path, download_root)
            notes_dir = extracted_root / spec.subpath if spec.subpath else extracted_root
            if not notes_dir.exists():
                raise NoteSourceError(f"Requested subpath does not exist in repository: {spec.subpath}")
            description = f"github repository: {spec.owner}/{spec.repo}@{branch}"
            if spec.subpath:
                description = f"{description}/{spec.subpath}"
            return MaterializedNotesSource(
                notes_dir=notes_dir,
                description=description,
                cleanup_dir=download_root,
            )
        except Exception as error:
            last_error = error

    raise NoteSourceError(f"Unable to download GitHub repository: {last_error}")


def _download_archive(owner: str, repo: str, branch: str, archive_path: Path) -> None:
    url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
    try:
        with urlopen(url) as response:
            archive_path.write_bytes(response.read())
    except HTTPError as error:
        raise NoteSourceError(f"GitHub archive request failed with status {error.code} for branch '{branch}'.") from error
    except URLError as error:
        raise NoteSourceError(f"Could not reach GitHub: {error.reason}") from error


def _extract_archive(archive_path: Path, download_root: Path) -> Path:
    with zipfile.ZipFile(archive_path) as zip_file:
        zip_file.extractall(download_root)

    extracted_dirs = [path for path in download_root.iterdir() if path.is_dir()]
    if not extracted_dirs:
        raise NoteSourceError("Downloaded archive did not contain a repository directory.")
    return extracted_dirs[0]
