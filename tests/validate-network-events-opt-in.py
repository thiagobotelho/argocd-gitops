"""Garante que a mudança irreversível não seja ativada por manifests padrão."""
from pathlib import Path
import subprocess
import yaml

root = Path(__file__).resolve().parents[1]
def render(path):
    return [o for o in yaml.safe_load_all(subprocess.check_output(
        ["kubectl", "kustomize", str(root / path)], text=True)) if o]

normal = render("optional")
experimental = render("optional/network-events")
bootstrap = render("bootstrap/ovn-observability")
assert len(normal) == len(experimental) == 1
assert normal[0]["metadata"] == experimental[0]["metadata"]
assert normal[0]["spec"]["source"]["path"] == "overlays/desenvolvimento"
assert experimental[0]["spec"]["source"]["path"] == "overlays/desenvolvimento-network-events"
assert not any(o["kind"] == "FeatureGate" for o in normal + experimental)
assert len(bootstrap) == 1
assert bootstrap[0]["kind"] == "FeatureGate"
assert bootstrap[0]["spec"] == {"featureSet": "TechPreviewNoUpgrade"}
for path in root.rglob("kustomization.yaml"):
    if path.parent == root / "bootstrap/ovn-observability":
        continue
    objects = render(path.parent.relative_to(root))
    assert not any(o["kind"] == "FeatureGate" for o in objects), str(path)
print("PASS: FeatureGate isolada no bootstrap; mesma Application; padrão sem NetworkEvents")
