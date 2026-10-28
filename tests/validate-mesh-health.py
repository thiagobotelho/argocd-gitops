#!/usr/bin/env python3
"""Verifica a avaliação de saúde dos recursos Sail com LuaJIT."""
import pathlib,subprocess,tempfile,yaml
root=pathlib.Path(__file__).resolve().parents[1]
checks=yaml.safe_load((root/'base/argocd.yaml').read_text())['spec']['resourceHealthChecks']
cases=[
 ('{metadata={generation=1}}','Progressing'),
 ('{metadata={generation=2},status={observedGeneration=1,state="Healthy"}}','Progressing'),
 ('{metadata={generation=1},status={observedGeneration=1,state="Healthy"}}','Healthy'),
 ('{metadata={generation=1},status={observedGeneration=1,state="NameAlreadyExists"}}','Degraded'),
 ('{metadata={generation=1},status={state="Pending"}}','Progressing'),
 ('{metadata={generation=1},status={conditions={{type="Reconciled",status="False",reason="InvalidConfiguration"}}}}','Degraded'),
 ('{metadata={generation=1},status={state="Healthy",conditions={{type="InUse",status="False"}}}}','Healthy')]
selected=[c for c in checks if c['group']=='sailoperator.io']
assert {c['kind'] for c in selected}=={'Istio','IstioCNI','IstioRevisionTag'}
with tempfile.TemporaryDirectory() as td:
 for check in selected:
  extra=[]
  if check['kind']=='IstioRevisionTag':
   extra=[('{kind="IstioRevisionTag",metadata={generation=1},status={state="NotReferencedByAnything",istioRevision="mesh-crc",conditions={{type="Reconciled",status="True"}}}}','Healthy'),('{kind="IstioRevisionTag",metadata={generation=1},status={state="NotReferencedByAnything",conditions={{type="Reconciled",status="True"}}}}','Progressing')]
  for i,(obj,expected) in enumerate(cases+extra):
   path=pathlib.Path(td)/'check.lua'
   path.write_text('obj='+obj+'\nlocal check=function()\n'+check['check']+'\nend\nlocal hs=check()\nassert(hs.status=="'+expected+'", hs.status)\n')
   subprocess.run(['luajit',str(path)],check=True)
print('PASS: 23 casos de saúde Sail executados com LuaJIT')

rendered=[d for d in yaml.safe_load_all(subprocess.check_output(['kubectl','kustomize',str(root/'optional/service-mesh')],text=True)) if d]
assert len(rendered)==2
app=next(d for d in rendered if d["kind"]=="Application")
project=next(d for d in rendered if d["kind"]=="AppProject")
assert app["spec"]["project"]==project["metadata"]["name"]=="service-mesh"
assert project["spec"]["sourceRepos"]==["https://github.com/thiagobotelho/service-mesh-gitops.git"]
assert all(x["namespace"]!="mesh-lab" for x in project["spec"]["destinations"])
assert app['kind']=='Application' and app['metadata']['name']=='service-mesh'
assert not app['metadata'].get('finalizers')
assert app['spec']['source']['path']=='overlays/desenvolvimento'
assert app['spec']['source']['repoURL']=='https://github.com/thiagobotelho/service-mesh-gitops.git'
assert app['spec']['syncPolicy']['automated']=={'selfHeal':True,'prune':False}
print('PASS: uma Application automática de infraestrutura, sem prune, exclusão em cascata ou APIs')
