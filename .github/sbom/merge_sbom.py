"""Merges the CycloneDX SBOM of the Python libraries into the CycloneDX SBOM of the published image.

Usage: python3 -I merge_sbom.py OS_SBOM PYTHON_SBOM OUTPUT

The image SBOM (operating system packages) is the base and keeps its root component, the image. The libraries of the second
SBOM are added as components, and the root of the image depends on them, because they are bundled inside the PyInstaller binary.
"""
import json
import sys


def main(os_path: str, py_path: str, out_path: str) -> None:
    with open(os_path, encoding="utf-8") as f:
        base = json.load(f)
    with open(py_path, encoding="utf-8") as f:
        libs = json.load(f)

    root_ref = base["metadata"]["component"]["bom-ref"]
    libs_root_ref = libs["metadata"]["component"]["bom-ref"]

    components = base.setdefault("components", [])
    known = {c["bom-ref"] for c in components if "bom-ref" in c}
    added = [c for c in libs.get("components", []) if c.get("bom-ref") not in known]
    components.extend(added)

    dependencies = base.setdefault("dependencies", [])
    depends_on = None
    for dep in dependencies:
        if dep["ref"] == root_ref:
            depends_on = dep.setdefault("dependsOn", [])
    if depends_on is None:
        depends_on = []
        dependencies.append({"ref": root_ref, "dependsOn": depends_on})

    added_refs = {c["bom-ref"] for c in added if "bom-ref" in c}
    for dep in libs.get("dependencies", []):
        if dep["ref"] == libs_root_ref:
            # the libraries the builder image lists become dependencies of the published image
            depends_on.extend(r for r in dep.get("dependsOn", []) if r in added_refs and r not in depends_on)
        elif dep["ref"] in added_refs:
            dependencies.append(dep)
        elif dep["ref"] in known:
            # a component that both SBOMs list: keep the edges of both
            targets = [r for r in dep.get("dependsOn", []) if r in known or r in added_refs]
            existing = next((d for d in dependencies if d["ref"] == dep["ref"]), None)
            if existing is None:
                dependencies.append({"ref": dep["ref"], "dependsOn": targets})
            else:
                merged = existing.setdefault("dependsOn", [])
                merged.extend(r for r in targets if r not in merged)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(base, f, indent=2)
        f.write("\n")
    print(f"{len(components) - len(added)} image components + {len(added)} libraries = {len(components)} components")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
