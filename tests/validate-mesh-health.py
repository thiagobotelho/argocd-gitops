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
  for i,(obj,expected) in enumerate(cases):
   path=pathlib.Path(td)/'check.lua'
   path.write_text('obj='+obj+'\nlocal check=function()\n'+check['check']+'\nend\nlocal hs=check()\nassert(hs.status=="'+expected+'", hs.status)\n')
   subprocess.run(['luajit',str(path)],check=True)
print('PASS: 21 casos de saúde Sail executados com LuaJIT')
