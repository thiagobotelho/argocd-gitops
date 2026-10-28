"""Impede concessões globais ou fora dos projetos no bootstrap OIDC."""
from pathlib import Path
import copy
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[1]
NAMESPACES = {'grafana', 'zabbix', 'tempo', 'pyroscope', 'observability', 'observability-apps'}
GROUP_ROLES = {'openshift-viewers': 'view', 'openshift-project-admins': 'admin'}


def validate(objects):
    seen = set()
    for obj in objects:
        assert obj['kind'] == 'RoleBinding', 'Somente vínculos limitados por namespace'
        namespace = obj['metadata'].get('namespace')
        assert namespace in NAMESPACES, 'Namespace não autorizado'
        role = obj['roleRef']
        assert role['kind'] == 'ClusterRole' and role['apiGroup'] == 'rbac.authorization.k8s.io'
        subjects = obj['subjects']
        assert len(subjects) == 1 and subjects[0]['kind'] == 'Group'
        group = subjects[0]['name']
        assert group in GROUP_ROLES and role['name'] == GROUP_ROLES[group], 'Grupo/papel não autorizado'
        assert (namespace, group) not in seen, 'Vínculo duplicado'
        seen.add((namespace, group))
    assert seen == {(n, g) for n in NAMESPACES for g in GROUP_ROLES}


objects = [o for o in yaml.safe_load_all(subprocess.check_output(['kubectl', 'kustomize', str(ROOT/'bootstrap/openshift-access')], text=True)) if o]
validate(objects)
print('PASS: vínculos por namespace, sem concessão global')
for name, mutate in [
    ('vínculo global', lambda o: o[0].update(kind='ClusterRoleBinding')),
    ('namespace privilegiado', lambda o: o[0]['metadata'].update(namespace='openshift-gitops')),
    ('papel cluster-admin', lambda o: o[0]['roleRef'].update(name='cluster-admin')),
    ('associação a usuário', lambda o: o[0]['subjects'][0].update(kind='User')),
]:
    bad = copy.deepcopy(objects); mutate(bad)
    try:
        validate(bad)
    except AssertionError:
        print('PASS: rejeitado', name)
    else:
        raise AssertionError(name)

global_objects = [o for o in yaml.safe_load_all(subprocess.check_output(['kubectl', 'kustomize', str(ROOT/'bootstrap/openshift-access/cluster-admin')], text=True)) if o]
assert len(global_objects) == 1
binding = global_objects[0]
assert binding['kind'] == 'ClusterRoleBinding'
assert binding['roleRef'] == {'apiGroup': 'rbac.authorization.k8s.io', 'kind': 'ClusterRole', 'name': 'cluster-admin'}
assert binding['subjects'] == [{'kind': 'Group', 'apiGroup': 'rbac.authorization.k8s.io', 'name': 'openshift-cluster-admins'}]
print('PASS: concessão global isolada e exclusiva ao grupo administrativo')
cr = yaml.safe_load((ROOT/'base/argocd.yaml').read_text())
assert cr['spec']['rbac']['defaultPolicy'] == 'role:readonly'
assert 'g, openshift-cluster-admins, role:admin' in cr['spec']['rbac']['policy']
assert cr['spec']['sso']['provider'] == 'dex' and cr['spec']['sso']['dex']['openShiftOAuth'] is True
print('PASS: administração Argo pelo grupo SSO; padrão readonly preservado')
