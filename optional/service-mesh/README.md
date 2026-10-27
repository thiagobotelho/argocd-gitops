# Service Mesh opcional para CRC

Applications fora do App-of-Apps base e fora do agregador optional existente. Sem sync automático e sem finalizer de exclusão em cascata. Criar as Applications não inicia o laboratório; cada sync exige revisão manual.

Sequência didática: mesh-apps-lab cenário 01 e 02 antes do Operator; depois Operator → aprovação específica de InstallPlan → CSV/CRDs → plano de controle → readiness real → cenários 03–06 → monitores e dashboard. Não depender de waves entre Applications independentes.

Um único Application mesh-apps-lab deve alternar spec.source.path e sincronizar com prune. Não criar uma Application por cenário. Se houver workloads preexistentes com os mesmos nomes, revise sua adoção antes do primeiro sync. [Guia completo](https://github.com/thiagobotelho/service-mesh-gitops/blob/main/docs/INSTALACAO-CRC.md).

Tracing: substituir a fonte do Application service-mesh-control-plane por optional/tracing somente após validação do Collector existente; nunca criar dois gerenciadores para o mesmo Istio.

