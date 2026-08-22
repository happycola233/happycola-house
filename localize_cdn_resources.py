# -*- coding: utf-8 -*-
"""
将 AnZhiYu 主题依赖的第三方静态资源镜像到本地 `source/pluginsSrc/`。

目标：
1. 资源清单不再手写维护，而是直接读取当前主题包里的 `plugins.yml`。
2. 下载 CSS 后，继续补齐其中 `url(...)` 引用的字体 / 图片资源。
3. 刷新已有 CSS 子资源，并用内容哈希为字体 / 图片 URL 添加缓存版本。
4. 写入一份 manifest，记录本地镜像对应的主题版本、来源 URL、目标路径和 SHA-256。
5. 提供 `validate` 模式，检查：
   - 当前主题需要的资源是否都存在于 `source/pluginsSrc/`
   - CSS 依赖资源是否缺失
   - 本地 manifest 是否已经和当前主题版本 / 资源清单及实际文件内容同步

典型用法：
    python localize_cdn_resources.py download
    python localize_cdn_resources.py validate
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import sys
from pathlib import Path
from urllib import error, request
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlsplit, urlunsplit


BASE_URL = "https://cdn.cbd.int"
THEME_PACKAGE_NAME = "hexo-theme-anzhiyu"
THEME_FALLBACK_DIR = "anzhiyu"
MANIFEST_NAME = ".anzhiyu-local-cdn-manifest.json"
MANIFEST_SCHEMA_VERSION = 2
TARGET_SUBDIR = ("source", "pluginsSrc")
CSS_URL_PATTERN = re.compile(r"url\(([^)]+)\)")
FALLBACK_PROVIDERS = ("cbd", "jsdelivr", "unpkg", "elemecdn", "onmicrosoft", "anheyu")
OPTIONAL_SVG_FONT_SUFFIXES = (".woff2", ".woff", ".ttf", ".eot")
TEXT_HASH_SUFFIXES = frozenset(
    {".css", ".html", ".js", ".json", ".map", ".mjs", ".svg", ".txt", ".xml"}
)

# 这些资源不走主题 plugins.yml，而是你当前配置里显式引用的本地路径。
# 保持这个列表很小，风险远低于手写整份第三方清单。
EXTRA_RESOURCES = [
    {
        "id": "fontawesome_animation_css",
        "url": "https://npm.elemecdn.com/hexo-butterfly-tag-plugins-plus@1.0.17/lib/assets/font-awesome-animation.min.css",
        "relative": "font-awesome-animation/font-awesome-animation.min.css",
    },
    {
        "id": "swiper_css",
        "name": "anzhiyu-theme-static",
        "file": "swiper/swiper.min.css",
        "version": "1.0.0",
    },
    {
        "id": "swiper_js",
        "name": "anzhiyu-theme-static",
        "file": "swiper/swiper.min.js",
        "version": "1.0.0",
    },
]


class UnsafePathError(RuntimeError):
    """目标路径越过 target_root 时抛出。"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mirror AnZhiYu CDN resources into source/pluginsSrc.")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("download", "validate"),
        default="download",
        help="download: 下载并刷新本地镜像；validate: 校验本地镜像与当前主题是否一致。",
    )
    parser.add_argument(
        "--theme-dir",
        help="主题目录。默认自动从 node_modules/hexo-theme-anzhiyu 或 themes/anzhiyu 推断。",
    )
    parser.add_argument(
        "--target-root",
        help="镜像输出目录。默认是 <hexo根目录>/source/pluginsSrc。",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="单个文件下载超时时间（秒），默认 30。",
    )
    return parser.parse_args()


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def resolve_theme_dir(base_dir: Path, theme_dir_arg: str | None) -> Path:
    candidates = []

    if theme_dir_arg:
        candidates.append(Path(theme_dir_arg))

    env_theme_dir = os.environ.get("ANZHIYU_THEME_DIR")
    if env_theme_dir:
        candidates.append(Path(env_theme_dir))

    candidates.append(base_dir / "node_modules" / THEME_PACKAGE_NAME)
    candidates.append(base_dir / "themes" / THEME_FALLBACK_DIR)

    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(
        "找不到主题目录。请确认已安装主题，或使用 --theme-dir 指定。"
    )


def resolve_target_root(base_dir: Path, target_root_arg: str | None) -> Path:
    if target_root_arg:
        return Path(target_root_arg).resolve()
    return (base_dir / Path(*TARGET_SUBDIR)).resolve()


def load_theme_version(theme_dir: Path) -> str:
    package_json = theme_dir / "package.json"
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
        return str(data.get("version", "unknown"))
    except Exception as exc:
        raise RuntimeError(f"无法读取主题版本：{package_json} ({exc})") from exc


def load_theme_plugins(theme_dir: Path) -> dict[str, dict[str, str]]:
    plugins_yml = theme_dir / "plugins.yml"
    if not plugins_yml.exists():
        raise FileNotFoundError(f"找不到主题 plugins.yml：{plugins_yml}")

    plugins: dict[str, dict[str, str]] = {}
    current_id: str | None = None
    current: dict[str, str] = {}

    for raw_line in plugins_yml.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if not raw_line.startswith(" "):
            if current_id and {"name", "file", "version"} <= current.keys():
                plugins[current_id] = current
            current_id = stripped[:-1] if stripped.endswith(":") else stripped
            current = {}
            continue

        if current_id is None:
            continue

        match = re.match(r"\s+([A-Za-z0-9_]+):\s*(.*?)\s*$", raw_line)
        if not match:
            continue

        key, value = match.groups()
        current[key] = strip_quotes(value)

    if current_id and {"name", "file", "version"} <= current.keys():
        plugins[current_id] = current

    if not plugins:
        raise RuntimeError(f"未能从 {plugins_yml} 解析出任何插件配置。")

    return plugins


def load_project_section_settings(base_dir: Path) -> dict[str, dict[str, str]]:
    config_path = base_dir / "_config.anzhiyu.yml"
    if not config_path.exists():
        return {}

    sections: dict[str, dict[str, str]] = {}
    current_section: str | None = None

    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        top_level = re.match(r"^([A-Za-z0-9_]+):\s*$", raw_line)
        if top_level:
            current_section = top_level.group(1)
            sections.setdefault(current_section, {})
            continue

        if current_section is None:
            continue

        nested = re.match(r"^\s{2}([A-Za-z0-9_]+):\s*(.*?)\s*$", raw_line)
        if nested:
            key, value = nested.groups()
            sections[current_section][key] = strip_quotes(value)
            continue

        if raw_line and not raw_line.startswith(" "):
            current_section = None

    return sections


def is_section_enabled(section_settings: dict[str, dict[str, str]], section: str) -> bool:
    if section not in section_settings:
        return True

    value = section_settings.get(section, {}).get("enable", "")
    if not value:
        return True
    return value.lower() == "true"


def filter_resources_for_project(
    resources: list[dict[str, str]],
    section_settings: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    disabled_features = {
        "mathjax": {"mathjax"},
        "katex": {"katex", "katex_copytex"},
        "mermaid": {"mermaid"},
    }

    optional_disabled_ids: set[str] = set()
    for section, resource_ids in disabled_features.items():
        if not is_section_enabled(section_settings, section):
            optional_disabled_ids.update(resource_ids)

    return [resource for resource in resources if resource["id"] not in optional_disabled_ids]


def build_url(name: str, version: str, file_path: str) -> str:
    file_path = file_path.lstrip("/")
    return f"{BASE_URL}/{name}@{version}/{file_path}"


def build_fallback_urls(name: str, version: str, file_path: str) -> list[str]:
    file_path = normalize_path_fragment(file_path)
    version_tag = f"@{version}" if version else ""
    min_file = re.sub(r"(?<!\.min)\.(js|css)$", r".min.\1", file_path)

    provider_map = {
        "cbd": f"https://cdn.cbd.int/{name}{version_tag}/{file_path}",
        "jsdelivr": f"https://cdn.jsdelivr.net/npm/{name}{version_tag}/{min_file}",
        "unpkg": f"https://unpkg.com/{name}{version_tag}/{file_path}",
        "elemecdn": f"https://npm.elemecdn.com/{name}{version_tag}/{file_path}",
        "onmicrosoft": f"https://npm.onmicrosoft.cn/{name}{version_tag}/{file_path}",
        "anheyu": f"https://cdn.anheyu.com/npm/{name}{version_tag}/{min_file}",
    }
    return [provider_map[provider] for provider in FALLBACK_PROVIDERS]


def normalize_path_fragment(path_fragment: str) -> str:
    return path_fragment.lstrip("/").replace("\\", "/")


def ensure_within_root(candidate: Path, target_root: Path, context: str) -> Path:
    resolved_root = target_root.resolve(strict=False)
    resolved_candidate = candidate.resolve(strict=False)

    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise UnsafePathError(
            f"{context}: {resolved_candidate} 越过了目标根目录 {resolved_root}"
        ) from exc

    return resolved_candidate


def make_resource(resource_id: str, spec: dict[str, str]) -> dict[str, str]:
    if "url" in spec:
        relative = normalize_path_fragment(spec["relative"])
        remote_url = spec["url"]
        name = spec.get("name", "")
        file_path = spec.get("file", relative)
        version = spec.get("version", "")
        fallback_urls = build_fallback_urls(name, version, file_path) if name and version and file_path else [remote_url]
    else:
        name = spec["name"]
        file_path = normalize_path_fragment(spec["file"])
        version = spec["version"]
        relative = normalize_path_fragment(f"{name}/{file_path}")
        remote_url = build_url(name, version, file_path)
        fallback_urls = build_fallback_urls(name, version, file_path)

    return {
        "id": resource_id,
        "name": name,
        "file": file_path,
        "version": version,
        "relative": relative,
        "remote_url": remote_url,
        "fallback_urls": list(dict.fromkeys([remote_url, *fallback_urls])),
    }


def build_resource_list(theme_plugins: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    resources = []

    for resource_id in sorted(theme_plugins.keys()):
        resources.append(make_resource(resource_id, theme_plugins[resource_id]))

    for extra in EXTRA_RESOURCES:
        resources.append(make_resource(extra["id"], extra))

    return resources


def build_local_path(target_root: Path, relative: str) -> Path:
    candidate = target_root / Path(*normalize_path_fragment(relative).split("/"))
    return ensure_within_root(candidate, target_root, f"主资源路径 {relative}")


def download_file(urls: str | list[str], dest: Path, timeout: int = 30) -> str | None:
    if isinstance(urls, str):
        urls = [urls]

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_dest = dest.with_suffix(dest.suffix + ".codex-download")

    for url in urls:
        try:
            print(f"-> {url}")
            with request.urlopen(url, timeout=timeout) as response, tmp_dest.open("wb") as handle:
                handle.write(response.read())
            os.replace(tmp_dest, dest)
            print(f"   Saved to {dest}")
            return url
        except error.HTTPError as exc:
            print(f"   [HTTP {exc.code}] Failed to download {url}")
        except error.URLError as exc:
            print(f"   [URL Error] Failed to download {url}: {exc.reason}")
        except Exception as exc:  # pragma: no cover - 兜底日志
            print(f"   [Error] Failed to download {url}: {exc}")
        finally:
            if tmp_dest.exists():
                tmp_dest.unlink(missing_ok=True)

    return None


def file_sha256(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_HASH_SUFFIXES:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def read_text_with_fallback(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def build_css_asset_urls(
    remote_css_url: str,
    raw_path: str,
    resource: dict[str, str] | None = None,
) -> list[str]:
    parsed_raw = urlparse(raw_path)
    sanitized_path = parsed_raw.path
    candidates = []

    if sanitized_path:
        candidates.append(urljoin(remote_css_url, sanitized_path))
    candidates.append(urljoin(remote_css_url, raw_path))

    if resource and sanitized_path and not sanitized_path.startswith("/"):
        css_file = normalize_path_fragment(resource.get("file", ""))
        asset_file = posixpath.normpath(
            posixpath.join(posixpath.dirname(css_file), sanitized_path)
        )
        if asset_file not in ("", ".", "..") and not asset_file.startswith("../"):
            name = resource.get("name", "")
            version = resource.get("version", "")
            if name:
                candidates.extend(build_fallback_urls(name, version, asset_file))

    return list(dict.fromkeys(candidates))


def is_optional_missing_css_asset(path: Path) -> bool:
    if path.suffix.lower() != ".svg":
        return False

    stem = path.with_suffix("")
    return any(stem.with_suffix(ext).exists() for ext in OPTIONAL_SVG_FONT_SUFFIXES)


def iter_css_assets(
    local_css_path: Path,
    remote_css_url: str,
    target_root: Path,
    resource: dict[str, str] | None = None,
):
    try:
        text = read_text_with_fallback(local_css_path)
    except Exception as exc:
        print(f"   [CSS] Cannot read {local_css_path}: {exc}")
        return

    css_dir = ensure_within_root(
        local_css_path.parent,
        target_root,
        f"CSS 基路径 {local_css_path.parent}",
    )

    for match in CSS_URL_PATTERN.finditer(text):
        raw = match.group(1).strip().strip('\'"')
        if not raw or raw.startswith(("data:", "http://", "https://", "//")):
            continue

        asset_urls = build_css_asset_urls(remote_css_url, raw, resource)
        asset_path = urlparse(raw).path
        candidate = Path(os.path.normpath(os.path.join(css_dir, asset_path)))
        dest = ensure_within_root(
            candidate,
            target_root,
            f"CSS 资源路径 {raw} from {local_css_path}",
        )
        yield asset_urls, dest


def download_css_assets(
    local_css_path: Path,
    remote_css_url: str,
    target_root: Path,
    timeout: int,
    resource: dict[str, str],
) -> int:
    print(f"   [CSS] Scan assets in {local_css_path}")
    failed = 0
    seen: set[Path] = set()
    for asset_urls, dest_path in iter_css_assets(
        local_css_path,
        remote_css_url,
        target_root,
        resource,
    ):
        if dest_path in seen:
            continue
        seen.add(dest_path)
        action = "refresh" if dest_path.exists() else "download"
        print(f"   [CSS asset {action}] {asset_urls[0]}")
        if download_file(asset_urls, dest_path, timeout=timeout) is None:
            if is_optional_missing_css_asset(dest_path):
                print(f"   [CSS asset optional] Skip missing legacy SVG font {dest_path}")
                continue
            failed += 1
    return failed


def rewrite_css_asset_urls_with_hashes(local_css_path: Path, target_root: Path) -> int:
    """为本地 CSS 子资源追加内容哈希，避免浏览器继续使用旧字体/图片缓存。"""
    text = read_text_with_fallback(local_css_path)
    css_dir = ensure_within_root(
        local_css_path.parent,
        target_root,
        f"CSS 基路径 {local_css_path.parent}",
    )
    hash_cache: dict[Path, str] = {}
    rewritten = 0

    def replace_url(match: re.Match[str]) -> str:
        nonlocal rewritten

        token = match.group(1)
        leading = token[: len(token) - len(token.lstrip())]
        trailing = token[len(token.rstrip()) :]
        wrapped = token.strip()
        quote = wrapped[0] if len(wrapped) >= 2 and wrapped[0] == wrapped[-1] and wrapped[0] in ("'", '"') else ""
        raw = wrapped[1:-1] if quote else wrapped

        if not raw or raw.startswith(("data:", "http://", "https://", "//")):
            return match.group(0)

        asset_path = urlparse(raw).path
        candidate = Path(os.path.normpath(os.path.join(css_dir, asset_path)))
        dest = ensure_within_root(
            candidate,
            target_root,
            f"CSS 资源路径 {raw} from {local_css_path}",
        )
        if not dest.exists():
            return match.group(0)

        if dest not in hash_cache:
            hash_cache[dest] = file_sha256(dest)[:12]

        parts = urlsplit(raw)
        query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "local_v"]
        query.append(("local_v", hash_cache[dest]))
        versioned = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
        value = f"{quote}{versioned}{quote}" if quote else versioned
        rewritten += 1
        return f"url({leading}{value}{trailing})"

    updated = CSS_URL_PATTERN.sub(replace_url, text)
    if updated != text:
        local_css_path.write_text(updated, encoding="utf-8")
        print(f"   [CSS cache] Added content hashes to {rewritten} local asset URL(s)")
    return rewritten


def manifest_path(target_root: Path) -> Path:
    return target_root / MANIFEST_NAME


def relative_to_target(path: Path, target_root: Path) -> str:
    resolved = ensure_within_root(path, target_root, f"manifest 文件路径 {path}")
    return resolved.relative_to(target_root.resolve(strict=False)).as_posix()


def collect_css_asset_records(
    local_css_path: Path,
    remote_css_url: str,
    target_root: Path,
    resource: dict[str, str],
) -> list[dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for asset_urls, asset_path in iter_css_assets(
        local_css_path,
        remote_css_url,
        target_root,
        resource,
    ):
        if not asset_path.exists() and is_optional_missing_css_asset(asset_path):
            continue

        relative = relative_to_target(asset_path, target_root)
        record: dict[str, object] = {
            "relative": relative,
            "source_urls": asset_urls,
        }
        if asset_path.exists():
            record["sha256"] = file_sha256(asset_path)
        records[relative] = record

    return [records[key] for key in sorted(records)]


def write_manifest(
    target_root: Path,
    theme_dir: Path,
    theme_version: str,
    resources: list[dict[str, str]],
) -> None:
    manifest_resources: dict[str, dict[str, object]] = {}
    for resource in resources:
        dest = build_local_path(target_root, resource["relative"])
        entry: dict[str, object] = {
            "name": resource["name"],
            "file": resource["file"],
            "version": resource["version"],
            "relative": resource["relative"],
            "remote_url": resource["remote_url"],
            "fallback_urls": resource["fallback_urls"],
            "sha256": file_sha256(dest),
        }
        if dest.suffix.lower() == ".css":
            entry["css_assets"] = collect_css_asset_records(
                dest,
                resource["remote_url"],
                target_root,
                resource,
            )
        manifest_resources[resource["id"]] = entry

    payload = {
        "generator": "localize_cdn_resources.py",
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "theme_package": THEME_PACKAGE_NAME,
        "theme_dir": str(theme_dir),
        "theme_version": theme_version,
        "resource_count": len(resources),
        "resources": manifest_resources,
    }

    target_root.mkdir(parents=True, exist_ok=True)
    manifest = manifest_path(target_root)
    manifest.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"\nManifest written to {manifest}")


def load_manifest(target_root: Path) -> dict | None:
    manifest = manifest_path(target_root)
    if not manifest.exists():
        return None

    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"无法读取 manifest：{manifest} ({exc})") from exc


def download_resources(
    resources: list[dict[str, str]],
    target_root: Path,
    timeout: int,
) -> tuple[int, int]:
    success = 0
    failed = 0

    for resource in resources:
        print(f"\n[{resource['id']}]")
        dest = build_local_path(target_root, resource["relative"])

        used_url = download_file(resource["fallback_urls"], dest, timeout=timeout)
        if used_url is not None:
            success += 1
            if dest.suffix.lower() == ".css":
                css_failed = download_css_assets(
                    dest,
                    used_url,
                    target_root,
                    timeout,
                    resource,
                )
                failed += css_failed
                if css_failed == 0:
                    rewrite_css_asset_urls_with_hashes(dest, target_root)
        else:
            failed += 1

    return success, failed


def validate_resources(
    resources: list[dict[str, str]],
    target_root: Path,
    theme_version: str,
) -> int:
    missing_files: list[str] = []
    missing_css_assets: list[str] = []
    stale_manifest: list[str] = []
    hash_mismatches: list[str] = []
    path_risks: list[str] = []

    manifest = load_manifest(target_root)
    manifest_resources = (manifest or {}).get("resources", {})
    should_check_manifest_entries = manifest is not None

    if manifest is None:
        stale_manifest.append(
            f"缺少 {MANIFEST_NAME}，无法确认本地镜像是否已经和当前主题同步。"
        )
    else:
        manifest_schema = manifest.get("schema_version")
        if manifest_schema != MANIFEST_SCHEMA_VERSION:
            stale_manifest.append(
                f"manifest schema={manifest_schema or '∅'}，当前应为 {MANIFEST_SCHEMA_VERSION}。"
            )

        manifest_theme_version = str(manifest.get("theme_version", ""))
        if manifest_theme_version != theme_version:
            stale_manifest.append(
                f"manifest 主题版本为 {manifest_theme_version or 'unknown'}，当前主题版本为 {theme_version}。"
            )

        manifest_count = manifest.get("resource_count")
        if manifest_count != len(resources):
            stale_manifest.append(
                f"manifest resource_count={manifest_count or '∅'}，当前应为 {len(resources)}。"
            )

    for resource in resources:
        resource_id = resource["id"]
        manifest_entry = manifest_resources.get(resource_id) if should_check_manifest_entries else None
        try:
            dest = build_local_path(target_root, resource["relative"])
        except UnsafePathError as exc:
            path_risks.append(f"{resource_id}: {exc}")
            continue

        if should_check_manifest_entries:
            if manifest_entry is None:
                stale_manifest.append(f"{resource_id}: manifest 未记录该资源。")
            else:
                for field in ("relative", "remote_url", "version"):
                    expected = resource[field]
                    actual = str(manifest_entry.get(field, ""))
                    if actual != expected:
                        stale_manifest.append(
                            f"{resource_id}: manifest {field}={actual or '∅'}，当前应为 {expected or '∅'}。"
                        )
                        break
                else:
                    expected_fallbacks = resource["fallback_urls"]
                    actual_fallbacks = manifest_entry.get("fallback_urls", [])
                    if actual_fallbacks != expected_fallbacks:
                        stale_manifest.append(
                            f"{resource_id}: manifest fallback_urls 已过期。"
                        )

        if not dest.exists():
            missing_files.append(f"{resource_id}: 缺少 {dest}")
            continue

        if manifest_entry is not None:
            recorded_hash = str(manifest_entry.get("sha256", ""))
            if not recorded_hash:
                stale_manifest.append(f"{resource_id}: manifest 缺少主文件 sha256。")
            else:
                actual_hash = file_sha256(dest)
                if actual_hash != recorded_hash:
                    hash_mismatches.append(
                        f"{resource_id}: {dest} 哈希不匹配（manifest={recorded_hash}, actual={actual_hash}）。"
                    )

        if dest.suffix.lower() == ".css":
            actual_css_assets: dict[str, str] = {}
            try:
                for asset_urls, asset_dest in iter_css_assets(
                    dest,
                    resource["remote_url"],
                    target_root,
                    resource,
                ):
                    if not asset_dest.exists():
                        if is_optional_missing_css_asset(asset_dest):
                            continue
                        missing_css_assets.append(
                            f"{resource_id}: CSS 依赖缺少 {asset_dest} (from {asset_urls[0]})"
                        )
                        continue

                    relative = relative_to_target(asset_dest, target_root)
                    actual_css_assets[relative] = file_sha256(asset_dest)
            except UnsafePathError as exc:
                path_risks.append(f"{resource_id}: {exc}")
                continue

            if manifest_entry is not None:
                manifest_css_assets = manifest_entry.get("css_assets")
                if not isinstance(manifest_css_assets, list):
                    stale_manifest.append(f"{resource_id}: manifest 缺少 css_assets 清单。")
                    continue

                recorded_css_assets: dict[str, str] = {}
                for item in manifest_css_assets:
                    if not isinstance(item, dict) or not item.get("relative"):
                        stale_manifest.append(f"{resource_id}: manifest 含无效的 CSS 子资源记录。")
                        continue
                    recorded_css_assets[str(item["relative"])] = str(item.get("sha256", ""))

                for relative, actual_hash in actual_css_assets.items():
                    if relative not in recorded_css_assets:
                        stale_manifest.append(
                            f"{resource_id}: manifest 未记录 CSS 子资源 {relative}。"
                        )
                        continue

                    recorded_hash = recorded_css_assets[relative]
                    if not recorded_hash:
                        stale_manifest.append(
                            f"{resource_id}: CSS 子资源 {relative} 缺少 sha256。"
                        )
                    elif recorded_hash != actual_hash:
                        hash_mismatches.append(
                            f"{resource_id}: CSS 子资源 {relative} 哈希不匹配"
                            f"（manifest={recorded_hash}, actual={actual_hash}）。"
                        )

                for relative in sorted(recorded_css_assets.keys() - actual_css_assets.keys()):
                    stale_manifest.append(
                        f"{resource_id}: manifest 仍记录 CSS 已不再引用的子资源 {relative}。"
                    )

    if path_risks:
        print("[unsafe paths]")
        for item in path_risks:
            print(f"  - {item}")

    if stale_manifest:
        print("[manifest]")
        for item in stale_manifest:
            print(f"  - {item}")

    if missing_files:
        print("[missing files]")
        for item in missing_files:
            print(f"  - {item}")

    if missing_css_assets:
        print("[missing css assets]")
        for item in missing_css_assets:
            print(f"  - {item}")

    if hash_mismatches:
        print("[hash mismatches]")
        for item in hash_mismatches:
            print(f"  - {item}")

    if not (
        path_risks
        or stale_manifest
        or missing_files
        or missing_css_assets
        or hash_mismatches
    ):
        print("Validation passed. 本地镜像与当前主题资源清单一致。")
        return 0

    print("\nValidation failed.")
    print("建议先执行：python localize_cdn_resources.py download")
    return 1


def main() -> int:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    theme_dir = resolve_theme_dir(base_dir, args.theme_dir)
    target_root = resolve_target_root(base_dir, args.target_root)
    theme_version = load_theme_version(theme_dir)
    theme_plugins = load_theme_plugins(theme_dir)
    section_settings = load_project_section_settings(base_dir)
    resources = filter_resources_for_project(
        build_resource_list(theme_plugins),
        section_settings,
    )

    print(f"Theme dir   : {theme_dir}")
    print(f"Theme ver   : {theme_version}")
    print(f"Target root : {target_root}")
    print(f"Resources   : {len(resources)}")

    if args.mode == "validate":
        return validate_resources(resources, target_root, theme_version)

    try:
        success, failed = download_resources(resources, target_root, timeout=args.timeout)
    except UnsafePathError as exc:
        print(f"\n[unsafe path] {exc}")
        print("已中止下载，避免写出 target_root 之外。")
        return 2

    if failed == 0:
        write_manifest(target_root, theme_dir, theme_version, resources)
    else:
        print("\nManifest not updated because some downloads failed.")

    print("\nDone.")
    print(f"Success: {success}, Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
