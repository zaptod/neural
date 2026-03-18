"""
NEURAL FIGHTS - Sistema de Armas v2
Modelo simplificado com schema migrado, perfis mecanicos/visuais e
camada de compatibilidade para o runtime atual.
"""

from __future__ import annotations

from copy import deepcopy

from nucleo.armas import construir_schema_arma


def gerar_passiva_arma(_raridade):
    """Sistema legado desativado na v2 para simplificar balanceamento."""
    return None


def calcular_tamanho_arma(arma) -> float:
    """Estimativa de tamanho visual da arma em metros de jogo."""
    if arma is None:
        return 0.0

    alcance = float(getattr(arma, "alcance_efetivo", 0.0) or 0.0)
    geometria = getattr(arma, "geometria", {}) or {}
    distancia = float(geometria.get("distancia", getattr(arma, "distancia", 0.0)) or 0.0)
    comp_lamina = float(geometria.get("comp_lamina", getattr(arma, "comp_lamina", 0.0)) or 0.0)
    comp_corrente = float(geometria.get("comp_corrente", getattr(arma, "comp_corrente", 0.0)) or 0.0)

    estimativa = max(alcance, distancia / 100.0, (comp_lamina + comp_corrente) / 100.0)
    return max(0.4, estimativa)


class Arma:
    """
    Classe publica de arma.

    Mantem atributos legados (`tipo`, `raridade`, `distancia`, etc.) para o
    runtime atual, mas internamente usa o schema v2 com separacao entre:
    - familia da arma
    - perfil mecanico
    - perfil visual
    - perfil magico
    """

    def __init__(
        self,
        nome,
        tipo=None,
        dano=8.0,
        peso=4.0,
        *,
        estilo="",
        raridade="Padrão",
        habilidades=None,
        encantamentos=None,
        passiva=None,
        critico=0.0,
        velocidade_ataque=1.0,
        afinidade_elemento=None,
        durabilidade=100.0,
        durabilidade_max=100.0,
        quantidade=1,
        quantidade_orbitais=1,
        forca_arco=0.0,
        schema_version=2,
        familia=None,
        categoria=None,
        subtipo=None,
        combate=None,
        visual=None,
        magia=None,
        geometria=None,
        forma_atual=1,
        r=200,
        g=200,
        b=200,
        habilidade="Nenhuma",
        custo_mana=0.0,
        **kwargs,
    ):
        payload = {
            "schema_version": schema_version,
            "nome": nome,
            "tipo": tipo or kwargs.get("tipo_legacy", "Reta"),
            "familia": familia,
            "categoria": categoria,
            "subtipo": subtipo,
            "dano": dano,
            "peso": peso,
            "estilo": estilo,
            "raridade": raridade,
            "habilidades": deepcopy(habilidades if habilidades is not None else ([{"nome": habilidade, "custo": float(custo_mana)}] if habilidade != "Nenhuma" else [])),
            "encantamentos": deepcopy(encantamentos or []),
            "passiva": deepcopy(passiva),
            "critico": critico,
            "velocidade_ataque": velocidade_ataque,
            "afinidade_elemento": afinidade_elemento,
            "durabilidade": durabilidade,
            "durabilidade_max": durabilidade_max,
            "quantidade": quantidade,
            "quantidade_orbitais": quantidade_orbitais,
            "forca_arco": forca_arco,
            "forma_atual": forma_atual,
            "combate": deepcopy(combate or {}),
            "visual": deepcopy(visual or {}),
            "magia": deepcopy(magia or {}),
            "geometria": deepcopy(geometria or {}),
            "r": r,
            "g": g,
            "b": b,
            "habilidade": habilidade,
            "custo_mana": custo_mana,
            **kwargs,
        }
        self._schema = construir_schema_arma(payload)
        self._aplicar_schema(self._schema)

    @classmethod
    def from_dict(cls, payload: dict) -> "Arma":
        return cls(**payload)

    def _aplicar_schema(self, schema: dict) -> None:
        self.schema_version = int(schema.get("schema_version", 2))
        self.id = schema["id"]
        self.nome = schema["nome"]
        self.familia = schema["familia"]
        self.subtipo = schema.get("subtipo", "")
        self.categoria = schema["categoria"]
        self.tipo = schema["tipo_legacy"]
        self.tipo_legacy = schema["tipo_legacy"]
        self.estilo = schema.get("estilo", "")

        self.perfil_mecanico = deepcopy(schema["combate"])
        self.perfil_visual = deepcopy(schema["visual"])
        self.perfil_magico = deepcopy(schema["magia"])
        self.geometria = deepcopy(schema["geometria"])
        self.meta_legado = deepcopy(schema.get("meta_legado", {}))

        self.dano_base = float(self.perfil_mecanico["dano_base"])
        self.peso_base = float(self.perfil_mecanico["peso"])
        self.dano = self.dano_base
        self.peso = self.peso_base
        self.alcance_base = float(self.perfil_mecanico["alcance"])
        self.alcance_efetivo = float(self.perfil_mecanico["alcance"])
        self.alcance_minimo = float(self.perfil_mecanico["alcance_minimo"])
        self.arco_ataque = float(self.perfil_mecanico["arco"])
        self.startup = float(self.perfil_mecanico["startup"])
        self.tempo_ativo = float(self.perfil_mecanico["ativo"])
        self.recovery = float(self.perfil_mecanico["recovery"])
        self.critico = float(self.perfil_mecanico["critico"])
        self.velocidade_ataque = float(self.perfil_mecanico["cadencia"])
        self.escala_forca = float(self.perfil_mecanico["escala_forca"])
        self.escala_mana = float(self.perfil_mecanico["escala_mana"])
        self.projeteis_por_ataque = int(self.perfil_mecanico["projeteis_por_ataque"])
        self.velocidade_projetil = float(self.perfil_mecanico["velocidade_projetil"])
        self.spread_base = float(self.perfil_mecanico["spread"])
        self.stagger_base = float(self.perfil_mecanico["stagger"])

        self.quantidade = int(schema.get("quantidade", self.projeteis_por_ataque))
        self.quantidade_orbitais = int(schema.get("quantidade_orbitais", self.perfil_mecanico["qtd_orbitais"]))
        self.forca_arco = float(schema.get("forca_arco", self.perfil_mecanico["forca_disparo"]))
        self.forma_atual = int(schema.get("forma_atual", 1))
        self.durabilidade_max = float(schema.get("durabilidade_max", self.perfil_mecanico["durabilidade_base"]))
        self.durabilidade = min(float(schema.get("durabilidade", self.durabilidade_max)), self.durabilidade_max)

        self.r = int(self.perfil_visual["cor_base"]["r"])
        self.g = int(self.perfil_visual["cor_base"]["g"])
        self.b = int(self.perfil_visual["cor_base"]["b"])
        self.raridade = self.perfil_visual.get("acabamento", "Padrão")
        self.cor_raridade = (self.r, self.g, self.b)
        self.efeito_visual = self.perfil_visual.get("rastro")
        self.afinidade_elemento = self.perfil_magico.get("afinidade")
        self.usa_foco_magico = bool(self.perfil_magico.get("usa_foco"))

        self.habilidades = deepcopy(self.perfil_magico.get("habilidades", []))
        if self.habilidades:
            primeira = self.habilidades[0]
            if isinstance(primeira, dict):
                self.habilidade = primeira.get("nome", "Nenhuma")
                self.custo_mana = float(primeira.get("custo", self.perfil_magico.get("custo_primario", 0.0)))
            else:
                self.habilidade = str(primeira)
                self.custo_mana = float(self.perfil_magico.get("custo_primario", 0.0))
        else:
            self.habilidade = self.perfil_magico.get("skill_primaria", "Nenhuma")
            self.custo_mana = float(self.perfil_magico.get("custo_primario", 0.0))

        # v2: raridade, encantamento e passiva deixam de afetar runtime.
        self.encantamentos = []
        self.passiva = None

        # Campos de geometria legada ainda consumidos pelo runtime atual.
        self.comp_cabo = float(self.geometria.get("comp_cabo", 15.0))
        self.comp_lamina = float(self.geometria.get("comp_lamina", 50.0))
        self.largura = float(self.geometria.get("largura", 30.0))
        self.distancia = float(self.geometria.get("distancia", self.alcance_efetivo * 100.0))
        self.comp_corrente = float(self.geometria.get("comp_corrente", 0.0))
        self.comp_ponta = float(self.geometria.get("comp_ponta", 0.0))
        self.largura_ponta = float(self.geometria.get("largura_ponta", 0.0))
        self.tamanho_projetil = float(self.geometria.get("tamanho_projetil", 0.0))
        self.tamanho_arco = float(self.geometria.get("tamanho_arco", 0.0))
        self.tamanho_flecha = float(self.geometria.get("tamanho_flecha", 0.0))
        self.tamanho = float(self.geometria.get("tamanho", 8.0))
        self.distancia_max = float(self.geometria.get("distancia_max", self.alcance_efetivo))
        self.separacao = float(self.geometria.get("separacao", 0.0))
        self.forma1_cabo = float(self.geometria.get("forma1_cabo", 0.0))
        self.forma1_lamina = float(self.geometria.get("forma1_lamina", 0.0))
        self.forma2_cabo = float(self.geometria.get("forma2_cabo", 0.0))
        self.forma2_lamina = float(self.geometria.get("forma2_lamina", 0.0))

    def get_dano_total(self):
        return self.dano

    def get_slots_disponiveis(self):
        max_slots = 3 if self.usa_foco_magico else 2
        return max_slots - len(self.habilidades)

    def adicionar_habilidade(self, nome_skill, custo):
        if self.get_slots_disponiveis() <= 0:
            return False
        self.habilidades.append({"nome": nome_skill, "custo": float(custo)})
        if len(self.habilidades) == 1:
            self.habilidade = nome_skill
            self.custo_mana = float(custo)
        self.perfil_magico["habilidades"] = deepcopy(self.habilidades)
        self.perfil_magico["skill_primaria"] = self.habilidade
        self.perfil_magico["custo_primario"] = self.custo_mana
        return True

    def adicionar_encantamento(self, _nome_enc):
        return False

    def trocar_forma(self):
        if self.familia == "hibrida":
            self.forma_atual = 2 if self.forma_atual == 1 else 1

    def to_dict(self):
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "nome": self.nome,
            "familia": self.familia,
            "subtipo": self.subtipo,
            "categoria": self.categoria,
            "tipo": self.tipo,
            "tipo_legacy": self.tipo_legacy,
            "estilo": self.estilo,
            "dano": self.dano_base,
            "peso": self.peso_base,
            "critico": self.critico,
            "velocidade_ataque": self.velocidade_ataque,
            "afinidade_elemento": self.afinidade_elemento,
            "quantidade": self.quantidade,
            "quantidade_orbitais": self.quantidade_orbitais,
            "forca_arco": self.forca_arco,
            "durabilidade": self.durabilidade,
            "durabilidade_max": self.durabilidade_max,
            "forma_atual": self.forma_atual,
            "r": self.r,
            "g": self.g,
            "b": self.b,
            "raridade": self.raridade,
            "habilidades": deepcopy(self.habilidades),
            "habilidade": self.habilidade,
            "custo_mana": self.custo_mana,
            "encantamentos": [],
            "passiva": None,
            "combate": deepcopy(self.perfil_mecanico),
            "visual": deepcopy(self.perfil_visual),
            "magia": deepcopy(self.perfil_magico),
            "geometria": deepcopy(self.geometria),
            "comp_cabo": self.comp_cabo,
            "comp_lamina": self.comp_lamina,
            "largura": self.largura,
            "distancia": self.distancia,
            "comp_corrente": self.comp_corrente,
            "comp_ponta": self.comp_ponta,
            "largura_ponta": self.largura_ponta,
            "tamanho_projetil": self.tamanho_projetil,
            "tamanho_arco": self.tamanho_arco,
            "tamanho_flecha": self.tamanho_flecha,
            "tamanho": self.tamanho,
            "distancia_max": self.distancia_max,
            "separacao": self.separacao,
            "forma1_cabo": self.forma1_cabo,
            "forma1_lamina": self.forma1_lamina,
            "forma2_cabo": self.forma2_cabo,
            "forma2_lamina": self.forma2_lamina,
            "meta_legado": deepcopy(self.meta_legado),
        }


def validar_arma_personagem(arma, personagem):
    """Valida se a arma e apropriada para o tamanho do personagem."""
    if arma is None or personagem is None:
        return {
            "valido": True,
            "mensagem": "Sem arma equipada",
            "sugestao": None,
            "proporcao": 0,
        }

    tamanho_arma = calcular_tamanho_arma(arma)
    tamanho_char = personagem.tamanho / 10.0
    if tamanho_char <= 0:
        tamanho_char = 1.0

    proporcao = tamanho_arma / tamanho_char
    resultado = {
        "proporcao": proporcao,
        "tamanho_arma": tamanho_arma,
        "tamanho_char": tamanho_char,
    }

    if proporcao < 0.2:
        resultado["valido"] = False
        resultado["mensagem"] = f"Arma muito pequena ({proporcao:.1%} do personagem)"
        resultado["sugestao"] = "Aumente o alcance ou o corpo visual da arma"
        resultado["nivel"] = "critico"
    elif proporcao < 0.4:
        resultado["valido"] = True
        resultado["mensagem"] = f"Arma pequena ({proporcao:.1%} do personagem)"
        resultado["sugestao"] = "Funciona, mas pode parecer leve demais"
        resultado["nivel"] = "aviso"
    elif proporcao > 3.0:
        resultado["valido"] = False
        resultado["mensagem"] = f"Arma muito grande ({proporcao:.1%} do personagem)"
        resultado["sugestao"] = "Reduza o alcance ou o corpo visual da arma"
        resultado["nivel"] = "critico"
    elif proporcao > 1.5:
        resultado["valido"] = True
        resultado["mensagem"] = f"Arma grande ({proporcao:.1%} do personagem)"
        resultado["sugestao"] = "Pode funcionar, mas tende ao exagero visual"
        resultado["nivel"] = "aviso"
    else:
        resultado["valido"] = True
        resultado["mensagem"] = f"Proporcao ideal ({proporcao:.1%} do personagem)"
        resultado["sugestao"] = None
        resultado["nivel"] = "ok"

    return resultado
