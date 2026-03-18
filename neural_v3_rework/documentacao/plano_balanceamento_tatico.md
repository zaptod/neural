# Plano De Balanceamento Tatico

## Objetivo
Parar de balancear o projeto por personagem isolado e passar a balancear por pacotes taticos:

- personalidade
- arma
- kit de skills
- papel no time
- desempenho por modo de combate

O alvo final e suportar bem tres cenarios principais:

1. `1v1`
2. `grupo vs grupo`
3. `grupo vs horda`

O projeto precisa continuar bom para video, mas tambem precisa funcionar para missoes, dungeons, hordas, escolta, defesa de ponto e composicoes cooperativas.

## Filosofia
Cada elemento deve ser bom individualmente, mas o balanceamento oficial deve ser feito em tres camadas:

1. `peca individual`
Personalidade, familia de arma e skill precisam ser legiveis e uteis sozinhas.

2. `pacote tatico`
O conjunto precisa cumprir um papel claro, como defensor, curandeiro ou assassino.

3. `ecossistema`
Os pacotes precisam coexistir bem nos tres modos de teste.

## Ordem Oficial De Iteracao
Este e o ciclo padrao de trabalho para qualquer pacote novo ou rebalanceado:

1. Definir o papel tatico.
2. Escolher arquitipos e tracos que reforcam esse papel.
3. Escolher familias de arma compativeis.
4. Escolher classes de magia compativeis.
5. Montar um pacote-base.
6. Testar o pacote em `1v1`.
7. Testar o pacote em `grupo vs grupo`.
8. Testar o pacote em `grupo vs horda`.
9. Coletar metricas.
10. Ajustar primeiro `funcao` e `ritmo`.
11. Ajustar depois `janela`, `alcance`, `recuperacao`, `cooldown`, `custo`.
12. Ajustar dano e cura por ultimo.
13. Repetir o ciclo.

## Regras De Balanceamento
Nao usar so dano como alavanca principal.

Prioridade de ajuste:

1. `funcao`
O pacote cumpre o papel dele?

2. `ritmo`
Entra cedo demais? demora demais? spamma demais?

3. `janela`
Tem contra-jogo? fica exposto? consegue ser punido?

4. `espacamento`
Alcance, zona morta, mobilidade e setup estao coerentes?

5. `custo`
Mana, cooldown, recovery e compromisso estao no lugar certo?

6. `numeros`
Dano, cura, escudo e burst.

## Papeis Taticos Oficiais
Os papeis-base do projeto devem ser tratados como a fonte principal de composicao:

- `defensor`
- `curandeiro`
- `suporte_controle`
- `atirador`
- `assassino`
- `duelista`
- `bruiser`
- `invocador`
- `controlador_de_area`
- `limpador_de_horda`

Os detalhes taticos de cada papel estao em [papeis_taticos.json](c:/Users/birul/Desktop/new/neural/neural_v3_rework/dados/papeis_taticos.json).

## Personalidade Como Modificador, Nao Como Papel
Personalidade nao deve substituir o papel. Ela deve modular:

- distancia preferida
- agressividade
- uso de skill
- tolerancia a risco
- tendencia a perseguir
- disciplina de mana
- reacao emocional
- cooperacao

Exemplo:

- `defensor + protetor` segura linha e prioriza cobertura.
- `defensor + calculista` joga mais no tempo e no contra-ataque.
- `defensor + berserker` vira um frontline mais instavel e agressivo.

## Modos Oficiais De Teste
### 1v1
Serve para validar:

- arma
- skill
- personalidade
- legibilidade
- burst e sustain

Metricas minimas:

- win rate por papel
- win rate por familia de arma
- tempo medio de luta
- dano total
- dano de arma
- dano de skill
- taxa de acerto
- uso de mana
- uso de cura
- variedade de acoes

### Grupo vs Grupo
Serve para validar:

- sinergia
- frontline e backline
- foco de alvo
- valor de cura
- valor de controle
- protecao de aliados
- composicao

Metricas minimas:

- win rate por composicao
- sobrevivencia por papel
- curas efetivas
- escudos efetivos
- interrupcoes de skill
- tempo de pressao no centro
- overkill e desperdicio

### Grupo vs Horda
Serve para validar:

- limpeza de area
- sustentacao
- controle de corredor
- protecao do suporte
- gasto de recursos
- consistencia em combate longo

Metricas minimas:

- tempo ate wipe
- total de inimigos abatidos
- dano recebido por papel
- custo de mana por onda
- eficiencia de cura
- uptime de controle
- capacidade de segurar gargalo

## Metas De Sucesso
### Individual
Uma familia de arma ou skill esta pronta quando:

- tem identidade propria
- tem ponto forte claro
- tem ponto fraco claro
- e legivel para quem assiste
- funciona sem bug
- nao domina todos os contextos

### Pacote Tatico
Um pacote esta pronto quando:

- cumpre o papel dele
- tem fraquezas coerentes
- nao depende de spam burro
- gera lutas interessantes
- funciona melhor com composicoes certas do que sozinho em qualquer cenario

### Ecossistema
O ecossistema esta saudavel quando:

- existe variedade real de vencedores
- nenhuma familia domina todos os modos
- nenhum papel e inutil
- o jogo continua dramatico sem virar caos ilegivel

## Foco Das Proximas Iteracoes
Ordem recomendada a partir de agora:

1. estabilizar os `papeis taticos`
2. montar `templates de composicao`
3. criar bateria automatizada dos tres modos
4. medir win rate e tempo medio por papel
5. rebalancear sustain e tempo de aproximacao
6. rebalancear horda e inimigos burros
7. so depois refinar os 500 personagens como variacoes dos templates

## Regra Pratica
Nao balancear 500 personagens manualmente.

Balancear:

- familias de arma
- familias de skill
- arquitipos
- tracos dominantes
- papeis taticos
- composicoes-base

Os 500 personagens devem ser derivados desses blocos.
