#!/usr/bin/env python3
"""Synchronize ROS 2 manifests from root CMake project metadata.

The synchronizer preserves package names, dependencies, non-website URLs, and
file modes. It only owns release metadata shared with the standalone project.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Sequence
import xml.etree.ElementTree as ET


_STRICT_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


@dataclass(frozen=True)
class ProjectMetadata:
    """Project-owned values exported by a metadata-only CMake configure."""

    project_name: str
    version: str
    description: str
    homepage_url: str
    maintainer_name: str
    maintainer_email: str
    license: str


class PackageRole(Enum):
    """Role-specific description suffixes for ROS 2 packages."""

    SHIM = "ROS 2 colcon shim package."
    INTERFACES = "ROS 2 message and service interfaces."
    BRIDGE = "ROS 2 bridge package."
    SPINUP = "ROS 2 launch and runtime assets."
    GENERIC = "ROS 2 package."


@dataclass(frozen=True)
class ManifestDocument:
    """Parsed manifest and filesystem state needed for a safe update."""

    path: Path
    mode: int
    original_bytes: bytes
    tree: ET.ElementTree
    leading_nodes: tuple[str, ...]
    trailing_nodes: tuple[str, ...]
    package_name: str


@dataclass(frozen=True)
class ManifestUpdate:
    """Prepared atomic replacement for one package manifest."""

    path: Path
    mode: int
    original_bytes: bytes
    updated_bytes: bytes


def _read_cache_value(cache_text_: str, key_: str) -> str:
    prefix_ = f"{key_}:"
    for line_ in cache_text_.splitlines():
        if not line_.startswith(prefix_):
            continue
        _, separator_, value_ = line_.partition("=")
        if separator_ and value_:
            return value_
        break
    raise ValueError(f"Missing or empty CMake metadata field: {key_}")


def _configure_project_metadata(project_root_: Path, version_: str) -> ProjectMetadata:
    cmake_executable_ = shutil.which("cmake")
    if cmake_executable_ is None:
        raise RuntimeError("cmake was not found on PATH")

    with tempfile.TemporaryDirectory(prefix="ros2_project_metadata_") as build_directory_:
        result_ = subprocess.run(
            [
                cmake_executable_,
                "-S",
                str(project_root_),
                "-B",
                build_directory_,
                "-DPROJECT_METADATA_ONLY=ON",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result_.returncode != 0:
            raise RuntimeError(
                "Metadata-only CMake configure failed:\n"
                f"stdout:\n{result_.stdout}\n"
                f"stderr:\n{result_.stderr}"
            )
        cache_text_ = (Path(build_directory_) / "CMakeCache.txt").read_text(
            encoding="utf-8"
        )

    cache_version_ = _read_cache_value(cache_text_, "CMAKE_PROJECT_VERSION")
    if cache_version_ != version_:
        raise ValueError(
            f"Resolved CMake version {cache_version_!r} does not match "
            f"requested ROS version {version_!r}"
        )

    metadata_ = ProjectMetadata(
        project_name=_read_cache_value(cache_text_, "CMAKE_PROJECT_NAME"),
        version=version_,
        description=_read_cache_value(cache_text_, "CMAKE_PROJECT_DESCRIPTION"),
        homepage_url=_read_cache_value(cache_text_, "CMAKE_PROJECT_HOMEPAGE_URL"),
        maintainer_name=_read_cache_value(cache_text_, "PROJECT_MAINTAINER_NAME"),
        maintainer_email=_read_cache_value(cache_text_, "PROJECT_MAINTAINER_EMAIL"),
        license=_read_cache_value(cache_text_, "PROJECT_LICENSE"),
    )
    if not _STRICT_VERSION_RE.fullmatch(metadata_.version):
        raise ValueError(
            f"ROS package version must be strict X.Y.Z, got {metadata_.version!r}"
        )
    if "@" not in metadata_.maintainer_email:
        raise ValueError("PROJECT_MAINTAINER_EMAIL must contain '@'")
    return metadata_


def _read_outer_xml_nodes(path_: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    leading_nodes_: list[str] = []
    trailing_nodes_: list[str] = []
    depth_ = 0
    root_seen_ = False
    root_closed_ = False

    for event_, element_ in ET.iterparse(
        path_, events=("start", "end", "comment", "pi")
    ):
        if event_ == "start":
            root_seen_ = True
            depth_ += 1
        elif event_ == "end":
            depth_ -= 1
            if root_seen_ and depth_ == 0:
                root_closed_ = True
        elif depth_ == 0:
            serialized_node_ = ET.tostring(element_, encoding="unicode")
            if root_closed_:
                trailing_nodes_.append(serialized_node_)
            elif not root_seen_:
                leading_nodes_.append(serialized_node_)

    return tuple(leading_nodes_), tuple(trailing_nodes_)


def _read_manifest(path_: Path) -> ManifestDocument:
    leading_nodes_, trailing_nodes_ = _read_outer_xml_nodes(path_)
    parser_ = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    tree_ = ET.parse(path_, parser=parser_)
    root_ = tree_.getroot()
    if root_.tag != "package":
        raise ValueError(f"Expected <package> root in {path_}")

    name_element_ = root_.find("name")
    package_name_ = (
        "" if name_element_ is None or name_element_.text is None else name_element_.text.strip()
    )
    if not package_name_:
        raise ValueError(f"Missing package name in {path_}")

    return ManifestDocument(
        path=path_,
        mode=stat.S_IMODE(path_.stat().st_mode),
        original_bytes=path_.read_bytes(),
        tree=tree_,
        leading_nodes=leading_nodes_,
        trailing_nodes=trailing_nodes_,
        package_name=package_name_,
    )


def _normalized_project_name(project_name_: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", project_name_.lower()).strip("_")


def _package_role(package_name_: str, project_name_: str) -> PackageRole:
    if package_name_ == _normalized_project_name(project_name_):
        return PackageRole.SHIM
    if package_name_.endswith("_interfaces"):
        return PackageRole.INTERFACES
    if package_name_.endswith("_ros"):
        return PackageRole.BRIDGE
    if package_name_.endswith("_spinup"):
        return PackageRole.SPINUP
    return PackageRole.GENERIC


def _require_element(root_: ET.Element, tag_: str, path_: Path) -> ET.Element:
    element_ = root_.find(tag_)
    if element_ is None:
        raise ValueError(f"Missing <{tag_}> in {path_}")
    return element_


def _set_website_url(root_: ET.Element, homepage_url_: str, path_: Path) -> None:
    website_elements_ = [
        url_ for url_ in root_.findall("url") if url_.get("type") == "website"
    ]
    if website_elements_:
        for website_element_ in website_elements_:
            website_element_.text = homepage_url_
        return

    license_element_ = _require_element(root_, "license", path_)
    children_ = list(root_)
    insert_index_ = children_.index(license_element_) + 1
    website_element_ = ET.Element("url", {"type": "website"})
    website_element_.text = homepage_url_
    website_element_.tail = license_element_.tail
    license_element_.tail = "\n  "
    root_.insert(insert_index_, website_element_)


def _serialize_manifest(document_: ManifestDocument) -> bytes:
    root_text_ = ET.tostring(document_.tree.getroot(), encoding="unicode")
    sections_ = [
        '<?xml version="1.0"?>',
        *document_.leading_nodes,
        root_text_,
        *document_.trailing_nodes,
    ]
    return ("\n".join(sections_).rstrip() + "\n").encode("utf-8")


def _build_update(
    document_: ManifestDocument,
    metadata_: ProjectMetadata,
) -> ManifestUpdate:
    root_ = document_.tree.getroot()
    role_ = _package_role(document_.package_name, metadata_.project_name)
    _require_element(root_, "version", document_.path).text = metadata_.version
    description_base_ = metadata_.description.rstrip().removesuffix(".")
    _require_element(root_, "description", document_.path).text = (
        f"{description_base_}: {role_.value}"
    )
    maintainer_element_ = _require_element(root_, "maintainer", document_.path)
    maintainer_element_.text = metadata_.maintainer_name
    maintainer_element_.set("email", metadata_.maintainer_email)
    _require_element(root_, "license", document_.path).text = metadata_.license
    _set_website_url(root_, metadata_.homepage_url, document_.path)
    return ManifestUpdate(
        path=document_.path,
        mode=document_.mode,
        original_bytes=document_.original_bytes,
        updated_bytes=_serialize_manifest(document_),
    )


def _write_update(update_: ManifestUpdate) -> bool:
    if update_.updated_bytes == update_.original_bytes:
        return False

    temporary_path_: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{update_.path.name}.",
            dir=update_.path.parent,
            delete=False,
        ) as temporary_file_:
            temporary_file_.write(update_.updated_bytes)
            temporary_file_.flush()
            os.fsync(temporary_file_.fileno())
            temporary_path_ = Path(temporary_file_.name)
        os.chmod(temporary_path_, update_.mode)
        os.replace(temporary_path_, update_.path)
        temporary_path_ = None
    finally:
        if temporary_path_ is not None:
            temporary_path_.unlink(missing_ok=True)
    return True


def synchronize_package_metadata(
    project_root_: Path,
    ros2_directory_: Path,
    version_: str,
) -> int:
    """Synchronize immediate ROS 2 package manifests from root metadata."""

    metadata_ = _configure_project_metadata(project_root_.resolve(), version_)
    manifest_paths_ = sorted(ros2_directory_.resolve().glob("*/package.xml"))
    if not manifest_paths_:
        raise ValueError(f"No immediate package.xml files found under {ros2_directory_}")

    documents_ = [_read_manifest(path_) for path_ in manifest_paths_]
    package_names_ = [document_.package_name for document_ in documents_]
    if len(set(package_names_)) != len(package_names_):
        raise ValueError("Duplicate ROS package names found in immediate manifests")

    updates_ = [_build_update(document_, metadata_) for document_ in documents_]
    for update_ in updates_:
        _write_update(update_)
    return len(updates_)


def _parse_arguments(arguments_: Sequence[str] | None) -> argparse.Namespace:
    parser_ = argparse.ArgumentParser(description=__doc__)
    parser_.add_argument("--project-root", required=True, type=Path)
    parser_.add_argument("--ros2-dir", required=True, type=Path)
    parser_.add_argument("--version", required=True)
    return parser_.parse_args(arguments_)


def main(arguments_: Sequence[str] | None = None) -> int:
    """Run metadata synchronization and return a process exit code."""

    parsed_arguments_ = _parse_arguments(arguments_)
    try:
        synchronized_count_ = synchronize_package_metadata(
            parsed_arguments_.project_root,
            parsed_arguments_.ros2_dir,
            parsed_arguments_.version,
        )
    except (ET.ParseError, OSError, RuntimeError, ValueError) as error_:
        print(f"[ERROR] {error_}", file=sys.stderr)
        return 1
    print(f"Synchronized {synchronized_count_} ROS 2 package manifests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
