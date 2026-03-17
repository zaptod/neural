# Relatorio de Remake Visual: Armas e Magias

## Objetivo
Elevar a leitura dramatica do combate sem mudar o balanceamento base.

## O que foi implementado no runtime
- Areas magicas agora mostram telegraph, sigilo, aneis de perigo e nucleo de impacto.
- Beams ficaram mais agressivos visualmente, com filamentos laterais, flare de origem/destino e sem gerar particulas no `draw`.
- Projetis magicos receberam silhueta por elemento, wake direcional e trilha energetica mais forte.
- Orbes magicos agora comunicam melhor carga, disparo e risco residual.
- Armas ganharam presenca de impacto perto da ponta, faíscas do sistema avancado e trilha avancada convertida corretamente para tela.

## Problemas de linguagem visual encontrados
- Muitas magias diferentes pareciam apenas “circulos com glow”.
- O perigo real de beam e area nao ficava claro no primeiro frame.
- Parte do pipeline de arma mais rico existia, mas nao chegava ao renderer principal.
- O render ainda misturava logica visual com mutacao de estado, especialmente em beam.

## Direcao visual aplicada
- Toda magia deve ter 4 fases legiveis:
  1. aviso
  2. carga
  3. impacto
  4. remanescencia perigosa
- Cada familia elemental precisa ter uma silhueta propria:
  - `FOGO`: cometa, cauda, calor e nucleo incandescente
  - `GELO`: cristal, lasca e ponta perfurante
  - `RAIO`: geometria quebrada e ramificacoes bruscas
  - `LUZ`: estrela, lança e julgamento vertical
  - `TREVAS`/`VOID`: ausencia, sução e distorcao
  - `ARCANO`: runas, orbitas e geometria ritual
  - `NATUREZA`: espinho, semente e crescimento hostil
  - `SANGUE`: pressão, gotejamento e impacto organico

## Melhoras futuras recomendadas
- Trocar parte das formas atuais por sprites VFX dedicados por elemento.
- Adicionar pós-processamento simples por impacto:
  - chromatic aberration curta
  - screen tint por elemento
  - bloom seletivo para núcleos magicos
- Criar atlas de frames para 3 habilidades “assinatura” por elemento.
- Redesenhar modelos base de armas com silhueta mais forte:
  - `Reta`: mais diferenciação entre espada, lança, machado e maça
  - `Dupla`: pares assimetricos e leitura de mão dominante
  - `Corrente`: peso, tensão e atraso visual na ponta
  - `Magica`: catalisadores menos genéricos e mais rituais
  - `Orbital`: entidades orbitais com identidade própria, nao só bolas brilhantes
- Separar o pipeline de “telegraph” do pipeline de “impacto” para skills futuras.

## Proxima etapa recomendada
Implementar sprites e keyframes dedicados para as skills mais importantes do roster, começando por:
- feitiços de beam
- explosoes em area
- magias de invocacao
- armas `Corrente`, `Magica` e `Transformavel`
