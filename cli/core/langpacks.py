from __future__ import annotations

import hashlib
import json
import locale
import shutil
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from cli.core.daemon import project_root
from cli.core.paths import app_state_dir


ENGINE_VERSION = "0.1.0"


BUILTIN_LANGUAGE_CATALOG = [
    ("af", "Afrikaans", "Latin"), ("am", "Amharic", "Ethiopic"), ("ar", "Arabic", "Arabic"),
    ("as", "Assamese", "Bengali"), ("az", "Azerbaijani", "Latin"), ("be", "Belarusian", "Cyrillic"),
    ("bg", "Bulgarian", "Cyrillic"), ("bn", "Bengali", "Bengali"), ("bo", "Tibetan", "Tibetan"),
    ("br", "Breton", "Latin"), ("bs", "Bosnian", "Latin"), ("ca", "Catalan", "Latin"),
    ("ceb", "Cebuano", "Latin"), ("cs", "Czech", "Latin"), ("cy", "Welsh", "Latin"),
    ("da", "Danish", "Latin"), ("de", "German", "Latin"), ("el", "Greek", "Greek"),
    ("eo", "Esperanto", "Latin"), ("es", "Spanish", "Latin"), ("et", "Estonian", "Latin"),
    ("eu", "Basque", "Latin"), ("fa", "Persian", "Arabic"), ("fi", "Finnish", "Latin"),
    ("fil", "Filipino", "Latin"), ("fr", "French", "Latin"), ("ga", "Irish", "Latin"),
    ("gd", "Scottish Gaelic", "Latin"), ("gl", "Galician", "Latin"), ("gu", "Gujarati", "Gujarati"),
    ("ha", "Hausa", "Latin"), ("haw", "Hawaiian", "Latin"), ("he", "Hebrew", "Hebrew"),
    ("hi", "Hindi", "Devanagari"), ("hmn", "Hmong", "Latin"), ("hr", "Croatian", "Latin"),
    ("ht", "Haitian Creole", "Latin"), ("hu", "Hungarian", "Latin"), ("hy", "Armenian", "Armenian"),
    ("id", "Indonesian", "Latin"), ("ig", "Igbo", "Latin"), ("is", "Icelandic", "Latin"),
    ("it", "Italian", "Latin"), ("ja", "Japanese", "Jpan"), ("jv", "Javanese", "Latin"),
    ("ka", "Georgian", "Georgian"), ("kk", "Kazakh", "Cyrillic"), ("km", "Khmer", "Khmer"),
    ("kn", "Kannada", "Kannada"), ("ko", "Korean", "Hangul"), ("ku", "Kurdish", "Latin"),
    ("ky", "Kyrgyz", "Cyrillic"), ("la", "Latin", "Latin"), ("lb", "Luxembourgish", "Latin"),
    ("lo", "Lao", "Lao"), ("lt", "Lithuanian", "Latin"), ("lv", "Latvian", "Latin"),
    ("mg", "Malagasy", "Latin"), ("mi", "Maori", "Latin"), ("mk", "Macedonian", "Cyrillic"),
    ("ml", "Malayalam", "Malayalam"), ("mn", "Mongolian", "Cyrillic"), ("mr", "Marathi", "Devanagari"),
    ("ms", "Malay", "Latin"), ("mt", "Maltese", "Latin"), ("my", "Burmese", "Myanmar"),
    ("ne", "Nepali", "Devanagari"), ("nl", "Dutch", "Latin"), ("no", "Norwegian", "Latin"),
    ("ny", "Chichewa", "Latin"), ("or", "Odia", "Odia"), ("pa", "Punjabi", "Gurmukhi"),
    ("pl", "Polish", "Latin"), ("ps", "Pashto", "Arabic"), ("pt", "Portuguese", "Latin"),
    ("ro", "Romanian", "Latin"), ("ru", "Russian", "Cyrillic"), ("rw", "Kinyarwanda", "Latin"),
    ("sd", "Sindhi", "Arabic"), ("si", "Sinhala", "Sinhala"), ("sk", "Slovak", "Latin"),
    ("sl", "Slovenian", "Latin"), ("sm", "Samoan", "Latin"), ("sn", "Shona", "Latin"),
    ("so", "Somali", "Latin"), ("sq", "Albanian", "Latin"), ("sr", "Serbian", "Cyrillic"),
    ("st", "Sesotho", "Latin"), ("su", "Sundanese", "Latin"), ("sv", "Swedish", "Latin"),
    ("sw", "Swahili", "Latin"), ("ta", "Tamil", "Tamil"), ("te", "Telugu", "Telugu"),
    ("tg", "Tajik", "Cyrillic"), ("th", "Thai", "Thai"), ("tk", "Turkmen", "Latin"),
    ("tl", "Tagalog", "Latin"), ("tr", "Turkish", "Latin"), ("tt", "Tatar", "Cyrillic"),
    ("ug", "Uyghur", "Arabic"), ("uk", "Ukrainian", "Cyrillic"), ("ur", "Urdu", "Arabic"),
    ("uz", "Uzbek", "Latin"), ("vi", "Vietnamese", "Latin"), ("xh", "Xhosa", "Latin"),
    ("yi", "Yiddish", "Hebrew"), ("yo", "Yoruba", "Latin"), ("zh-hant", "Chinese Traditional", "Hant"),
    ("zu", "Zulu", "Latin"),
]


class LangPackError(RuntimeError):
    pass


@dataclass(frozen=True)
class LangSpec:
    model_family: str
    language: str
    version: str | None = None


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_version(version: str) -> tuple[int, int, int]:
    parts = str(version or "0.0.0").split(".")
    nums = []
    for part in parts[:3]:
        try:
            nums.append(int(part))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def _version_in_range(version: str, min_version: str, max_version: str) -> bool:
    current = _parse_version(version)
    return _parse_version(min_version) <= current <= _parse_version(max_version)


def parse_lang_spec(value: str, default_family: str = "pp-ocrv5") -> LangSpec:
    """Parse `en`, `en@pp-ocrv5`, or `pp-ocrv5:en-1.2.0`.

    The Docker-like form is intentionally permissive because users will type it
    by hand. Only path separators are rejected later when resolving manifests.
    """
    text = str(value or "").strip()
    if not text:
        raise LangPackError("language is required")
    if ":" in text:
        family, tag = text.split(":", 1)
        if "-" in tag:
            lang, version = tag.split("-", 1)
        else:
            lang, version = tag, None
        return LangSpec(family or default_family, lang, version)
    if "@" in text:
        lang, family = text.split("@", 1)
        return LangSpec(family or default_family, lang, None)
    return LangSpec(default_family, text, None)


class LangPackDB:
    def __init__(self, path: Path | None = None):
        self.path = path or app_state_dir() / "installed_langpacks.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS installed_packs (
                    id INTEGER PRIMARY KEY,
                    language_code TEXT NOT NULL,
                    language_name TEXT NOT NULL,
                    model_family TEXT NOT NULL,
                    pack_version TEXT NOT NULL,
                    quality_tier TEXT NOT NULL,
                    installed_at REAL DEFAULT 0,
                    updated_at REAL DEFAULT 0,
                    install_source TEXT,
                    install_dir TEXT NOT NULL,
                    file_paths TEXT NOT NULL,
                    sha256_verified INTEGER DEFAULT 0,
                    UNIQUE(language_code, model_family, quality_tier)
                )
                """
            )

    def list(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM installed_packs ORDER BY model_family, language_code, quality_tier"
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, language: str, model_family: str, quality_tier: str = "standard") -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM installed_packs
                WHERE language_code = ? AND model_family = ? AND quality_tier = ?
                """,
                (language, model_family, quality_tier),
            ).fetchone()
        return dict(row) if row else None

    def upsert(self, manifest: dict, install_dir: Path, file_paths: Iterable[Path], source: str, verified: bool) -> None:
        now = time.time()
        language = manifest["language"]
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO installed_packs (
                    language_code, language_name, model_family, pack_version, quality_tier,
                    installed_at, updated_at, install_source, install_dir, file_paths, sha256_verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(language_code, model_family, quality_tier) DO UPDATE SET
                    language_name = excluded.language_name,
                    pack_version = excluded.pack_version,
                    updated_at = excluded.updated_at,
                    install_source = excluded.install_source,
                    install_dir = excluded.install_dir,
                    file_paths = excluded.file_paths,
                    sha256_verified = excluded.sha256_verified
                """,
                (
                    language["code"],
                    language.get("name") or language["code"],
                    manifest["model_family"],
                    manifest["pack_version"],
                    manifest.get("quality_tier", "standard"),
                    now,
                    now,
                    source,
                    str(install_dir),
                    json.dumps([str(p) for p in file_paths], ensure_ascii=False),
                    1 if verified else 0,
                ),
            )

    def remove(self, language: str, model_family: str, quality_tier: str = "standard") -> dict | None:
        item = self.get(language, model_family, quality_tier)
        if not item:
            return None
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM installed_packs WHERE language_code = ? AND model_family = ? AND quality_tier = ?",
                (language, model_family, quality_tier),
            )
        return item


class LangPackManager:
    def __init__(self, root: Path | None = None):
        self.root = root or project_root()
        self.resource_dir = self.root / "resources" / "langpacks"
        self.model_dir = self.root / "models" / "langpacks"
        self.db = LangPackDB()

    def index(self) -> dict:
        index = _read_json(self.resource_dir / "index.json")
        languages = list(index.get("languages", []))
        existing = {(item.get("code"), item.get("model_family")) for item in languages}
        for code, name, script in BUILTIN_LANGUAGE_CATALOG:
            key = (code, "pp-ocrv5")
            if key in existing:
                continue
            languages.append({
                "code": code,
                "name": name,
                "script": script,
                "model_family": "pp-ocrv5",
                "quality_tiers": ["standard"],
                "manifest": "pp-ocrv5/en.json",
                "generated": True,
            })
            existing.add(key)
        for locale_name in sorted(set(locale.windows_locale.values())):
            code = locale_name.replace("_", "-").lower()
            key = (code, "pp-ocrv5")
            if key in existing or len(code) < 4:
                continue
            base = code.split("-", 1)[0]
            base_entry = next((item for item in languages if item.get("code") == base), None)
            script = base_entry.get("script") if base_entry else "Locale"
            base_name = base_entry.get("name") if base_entry else base.upper()
            languages.append({
                "code": code,
                "name": f"{base_name} ({code.upper()})",
                "script": script,
                "model_family": "pp-ocrv5",
                "quality_tiers": ["standard"],
                "manifest": "pp-ocrv5/en.json",
                "generated": True,
            })
            existing.add(key)
        index["languages"] = languages
        return index

    def _index_entry(self, spec: LangSpec) -> dict:
        for entry in self.index().get("languages", []):
            if entry.get("code") == spec.language and entry.get("model_family") == spec.model_family:
                return entry
        raise LangPackError(f"language pack not found in index: {spec.model_family}:{spec.language}")

    def _manifest_path(self, spec: LangSpec) -> Path:
        return self.resource_dir / self._index_entry(spec)["manifest"]

    def manifest(self, spec: LangSpec) -> dict:
        path = self._manifest_path(spec)
        manifest = _read_json(path)
        entry = self._index_entry(spec)
        if entry.get("generated") or manifest.get("language", {}).get("code") != entry.get("code"):
            manifest = self._manifest_for_entry(manifest, entry)
        if spec.version and manifest.get("pack_version") != spec.version:
            raise LangPackError(
                f"requested {spec.language}-{spec.version}, but manifest has {manifest.get('pack_version')}"
            )
        compat = manifest.get("engine_compatibility") or {}
        min_v = compat.get("min_engine_version", "0.0.0")
        max_v = compat.get("max_engine_version", "999.999.999")
        manifest["compatibility_warning"] = None
        if not _version_in_range(ENGINE_VERSION, min_v, max_v):
            manifest["compatibility_warning"] = (
                f"language pack targets engine {min_v}..{max_v}; current engine is {ENGINE_VERSION}"
            )
        return manifest

    def _manifest_for_entry(self, base_manifest: dict, entry: dict) -> dict:
        """把基础英文 manifest 变成某个语言的候选包。

        远程仓库未必已经发布对应文件，但 GUI 需要先有完整目录和可点击的拉取入口；
        真实是否可用由下载阶段的 HTTP 状态决定。
        """
        manifest = json.loads(json.dumps(base_manifest))
        code = entry["code"]
        manifest["language"] = {
            "code": code,
            "name": entry.get("name") or code,
            "iso_639_1": code if len(code) == 2 else None,
            "script": entry.get("script") or "Unknown",
            "is_right_to_left": entry.get("script") in {"Arabic", "Hebrew"},
        }
        manifest["generated"] = bool(entry.get("generated"))
        manifest["pack_version"] = entry.get("version") or manifest.get("pack_version", "1.0.0")
        for file_info in manifest.get("files", []):
            old = file_info.get("filename", "")
            role = file_info.get("role", "model")
            suffix = "det_mobile.onnx" if role == "detection" else "rec_mobile.onnx"
            if role == "classification":
                suffix = "cls_mobile.onnx"
            file_info["filename"] = f"{code}_PP-OCRv5_{suffix}"
            file_info["sha256"] = None
            file_info["download_urls"] = [
                f"https://huggingface.co/vonishocr/pp-ocrv5-{code}/resolve/main/{file_info['filename']}",
                f"https://hf-mirror.com/vonishocr/pp-ocrv5-{code}/resolve/main/{file_info['filename']}",
                f"https://modelscope.cn/models/vonishocr/pp-ocrv5-{code}/resolve/main/{file_info['filename']}",
            ]
            file_info["source_template"] = old
        return manifest

    def list(self, include_remote: bool = True) -> list[dict]:
        installed = {
            (row["language_code"], row["model_family"], row["quality_tier"]): row
            for row in self.db.list()
        }
        rows = []
        for entry in self.index().get("languages", []):
            manifest = self.manifest(LangSpec(entry["model_family"], entry["code"]))
            key = (entry["code"], entry["model_family"], manifest.get("quality_tier", "standard"))
            inst = installed.get(key)
            if include_remote or inst:
                rows.append(self._row_from_manifest(manifest, inst))
        return rows

    def show(self, spec: LangSpec) -> dict:
        manifest = self.manifest(spec)
        installed = self.db.get(
            manifest["language"]["code"],
            manifest["model_family"],
            manifest.get("quality_tier", "standard"),
        )
        return {"manifest": manifest, "installed": installed}

    def install(self, spec: LangSpec, mirror: str | None = None, yes: bool = False, offline: bool = False) -> dict:
        manifest = self.manifest(spec)
        install_dir = self._install_dir(manifest)
        install_dir.mkdir(parents=True, exist_ok=True)

        local_hint = self._local_hint_dir(manifest)
        if local_hint and self._has_all_required(manifest, local_hint):
            file_paths = self._copy_or_reference_local(manifest, local_hint, install_dir)
            verified = self._verify_files(manifest, install_dir, repair=False)["ok"]
            self.db.upsert(manifest, install_dir, file_paths, f"local:{local_hint}", verified)
            return {"status": "installed", "source": "local", "language": manifest["language"]["code"], "path": str(install_dir)}

        if offline:
            raise LangPackError("offline mode: language pack is not available locally")
        if not yes:
            total = sum(int(f.get("size_bytes") or 0) for f in manifest.get("files", []) if f.get("required", True))
            raise LangPackError(
                f"download confirmation required for {manifest['language']['code']} ({total} bytes); rerun with --yes"
            )

        downloaded = []
        for file_info in manifest.get("files", []):
            if not file_info.get("required", True):
                continue
            downloaded.append(self._ensure_file(manifest, file_info, install_dir, mirror=mirror))

        verified = self._verify_files(manifest, install_dir, repair=False)["ok"]
        self.db.upsert(manifest, install_dir, downloaded, mirror or "auto", verified)
        return {"status": "installed", "source": mirror or "auto", "language": manifest["language"]["code"], "path": str(install_dir)}

    def remove(self, spec: LangSpec, delete_files: bool = True) -> dict:
        manifest = self.manifest(spec)
        item = self.db.remove(
            manifest["language"]["code"],
            manifest["model_family"],
            manifest.get("quality_tier", "standard"),
        )
        if not item:
            raise LangPackError(f"language pack is not installed: {spec.language}")
        install_dir = Path(item["install_dir"])
        if delete_files and install_dir.exists() and self.model_dir.resolve() in [install_dir.resolve(), *install_dir.resolve().parents]:
            shutil.rmtree(install_dir)
        return {"status": "removed", "language": spec.language, "path": str(install_dir)}

    def verify(self, spec: LangSpec | None = None, repair: bool = False) -> list[dict] | dict:
        if spec:
            manifest = self.manifest(spec)
            return self._verify_files(manifest, self._install_dir(manifest), repair=repair)
        results = []
        for row in self.list(include_remote=False):
            results.append(self.verify(LangSpec(row["model_family"], row["name"]), repair=repair))
        return results

    def _row_from_manifest(self, manifest: dict, installed: dict | None) -> dict:
        total = sum(int(f.get("size_bytes") or 0) for f in manifest.get("files", []) if f.get("required", True))
        return {
            "name": manifest["language"]["code"],
            "language": manifest["language"].get("name") or manifest["language"]["code"],
            "version": manifest.get("pack_version"),
            "installed": "yes" if installed else "no",
            "install_status": "installed" if installed else "not_installed",
            "local_available": self._local_hint_available(manifest),
            "remote_available": any(f.get("download_urls") for f in manifest.get("files", []) if f.get("required", True)),
            "generated": bool(manifest.get("generated")),
            "size_mb": round(total / (1024 * 1024), 2),
            "quality": manifest.get("quality_tier", "standard"),
            "model_family": manifest.get("model_family"),
        }

    def _install_dir(self, manifest: dict) -> Path:
        return self.model_dir / manifest["model_family"] / manifest.get("quality_tier", "standard") / manifest["language"]["code"]

    def _local_hint_dir(self, manifest: dict) -> Path | None:
        hint = manifest.get("local_model_hint")
        if not hint:
            return None
        path = self.root / "models" / Path(hint).name
        return path if path.exists() else None

    def _local_hint_available(self, manifest: dict) -> bool:
        local_hint = self._local_hint_dir(manifest)
        return bool(local_hint and self._has_all_required(manifest, local_hint))

    def _has_all_required(self, manifest: dict, base: Path) -> bool:
        for file_info in manifest.get("files", []):
            source_name = file_info.get("source_filename") or file_info["filename"]
            if file_info.get("required", True) and not (base / source_name).exists():
                return False
        return True

    def _copy_or_reference_local(self, manifest: dict, source: Path, install_dir: Path) -> list[Path]:
        paths = []
        for file_info in manifest.get("files", []):
            src = source / (file_info.get("source_filename") or file_info["filename"])
            if not src.exists():
                if file_info.get("required", True):
                    raise LangPackError(f"required local file missing: {src}")
                continue
            dst = install_dir / file_info["filename"]
            if not dst.exists() or dst.stat().st_size != src.stat().st_size:
                shutil.copy2(src, dst)
            paths.append(dst)
        return paths

    def _ensure_file(self, manifest: dict, file_info: dict, install_dir: Path, mirror: str | None) -> Path:
        target = install_dir / file_info["filename"]
        expected = file_info.get("sha256")
        if target.exists() and (not expected or _sha256(target).lower() == expected.lower()):
            return target
        urls = self._ordered_urls(file_info.get("download_urls") or [], mirror=mirror)
        if not urls:
            raise LangPackError(f"no download URL for {file_info['filename']}")
        errors = []
        for url in urls:
            try:
                self._download(url, target, expected)
                return target
            except Exception as exc:  # noqa: BLE001 - keep fallback reasons for users
                errors.append(f"{url}: {exc}")
        raise LangPackError("all mirrors failed:\n" + "\n".join(errors))

    def _ordered_urls(self, urls: list[str], mirror: str | None) -> list[str]:
        if mirror:
            selected = [url for url in urls if mirror in url]
            return selected or urls
        mirrors = sorted(self.index().get("mirrors", []), key=lambda m: int(m.get("priority") or 99))
        ordered = []
        for m in mirrors:
            ordered.extend([url for url in urls if m.get("url") and m["url"] in url])
        ordered.extend([url for url in urls if url not in ordered])
        return ordered

    def _download(self, url: str, target: Path, expected_sha: str | None) -> None:
        part = target.with_suffix(target.suffix + ".part")
        request = urllib.request.Request(url, headers={"User-Agent": "VonishOCR/0.1"})
        with urllib.request.urlopen(request, timeout=30) as response, open(part, "wb") as f:
            shutil.copyfileobj(response, f)
        if expected_sha and _sha256(part).lower() != expected_sha.lower():
            part.unlink(missing_ok=True)
            raise LangPackError("SHA256 mismatch")
        part.replace(target)

    def _verify_files(self, manifest: dict, install_dir: Path, repair: bool = False) -> dict:
        files = []
        ok = True
        for file_info in manifest.get("files", []):
            path = install_dir / file_info["filename"]
            exists = path.exists()
            expected = file_info.get("sha256")
            actual = _sha256(path) if exists else None
            file_ok = exists and (not expected or actual.lower() == expected.lower())
            if not file_ok:
                ok = False
                if repair and exists:
                    path.unlink(missing_ok=True)
            files.append({
                "file": file_info["filename"],
                "exists": exists,
                "ok": file_ok,
                "sha256": actual,
                "expected": expected,
            })
        return {
            "language": manifest["language"]["code"],
            "model_family": manifest["model_family"],
            "path": str(install_dir),
            "ok": ok,
            "files": files,
            "warning": manifest.get("compatibility_warning"),
        }
