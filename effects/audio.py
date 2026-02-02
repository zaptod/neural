"""
NEURAL FIGHTS - Sistema de Áudio v1.0
Gerenciador de sons para golpes, magias e efeitos de combate.
"""

import pygame
import os
import random
from typing import Dict, List, Optional


class AudioManager:
    """
    Gerenciador central de áudio do jogo.
    Sistema procedural que gera sons sintetizados se arquivos não existirem.
    """
    
    _instance = None
    
    def __init__(self):
        self.enabled = True
        self.master_volume = 0.7
        self.sfx_volume = 0.8
        self.music_volume = 0.5
        
        # Cache de sons carregados
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.sound_groups: Dict[str, List[pygame.mixer.Sound]] = {}
        
        # Diretório de sons
        self.sound_dir = "sounds"
        if not os.path.exists(self.sound_dir):
            os.makedirs(self.sound_dir, exist_ok=True)
        
        # Inicializa mixer do pygame
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(32)  # 32 canais simultâneos
        except:
            print("Aviso: Sistema de áudio não disponível")
            self.enabled = False
            return
        
        # Carrega/gera sons
        self._setup_sounds()
    
    @classmethod
    def get_instance(cls):
        """Singleton"""
        if cls._instance is None:
            cls._instance = AudioManager()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset singleton"""
        if cls._instance:
            cls._instance.stop_all()
        cls._instance = None
    
    def _setup_sounds(self):
        """Configura biblioteca de sons"""
        
        # === GOLPES FÍSICOS ===
        self._register_sound_group("punch", [
            "punch_light", "punch_medium", "punch_heavy"
        ])
        self._register_sound_group("kick", [
            "kick_light", "kick_heavy", "kick_spin"
        ])
        self._register_sound_group("slash", [
            "slash_light", "slash_heavy", "slash_critical"
        ])
        self._register_sound_group("stab", [
            "stab_quick", "stab_deep"
        ])
        self._register_sound_group("impact", [
            "impact_flesh", "impact_heavy", "impact_critical"
        ])
        
        # === MAGIAS E PROJÉTEIS ===
        self._register_sound_group("fireball", [
            "fireball_cast", "fireball_fly", "fireball_impact"
        ])
        self._register_sound_group("ice", [
            "ice_cast", "ice_shard", "ice_impact"
        ])
        self._register_sound_group("lightning", [
            "lightning_charge", "lightning_bolt", "lightning_impact"
        ])
        self._register_sound_group("energy", [
            "energy_charge", "energy_blast", "energy_impact"
        ])
        self._register_sound_group("beam", [
            "beam_charge", "beam_fire", "beam_end"
        ])
        
        # === SKILLS ESPECIAIS ===
        self._register_sound_group("dash", [
            "dash_whoosh", "dash_impact"
        ])
        self._register_sound_group("teleport", [
            "teleport_out", "teleport_in"
        ])
        self._register_sound_group("buff", [
            "buff_activate", "buff_pulse"
        ])
        self._register_sound_group("heal", [
            "heal_cast", "heal_complete"
        ])
        self._register_sound_group("shield", [
            "shield_up", "shield_block", "shield_break"
        ])
        
        # === MOVIMENTOS ===
        self._register_sound_group("jump", [
            "jump_start", "jump_land"
        ])
        self._register_sound_group("footstep", [
            "step_1", "step_2", "step_3", "step_4"
        ])
        self._register_sound_group("dodge", [
            "dodge_whoosh", "dodge_slide"
        ])
        
        # === AMBIENTE ===
        self._register_sound_group("wall_hit", [
            "wall_impact_light", "wall_impact_heavy"
        ])
        self._register_sound_group("ground_slam", [
            "ground_impact"
        ])
        
        # === UI E FEEDBACK ===
        self._register_sound_group("ui", [
            "ui_select", "ui_confirm", "ui_back"
        ])
        
        # Sons individuais importantes
        self._register_sound("ko_impact")
        self._register_sound("combo_hit")
        self._register_sound("counter_hit")
        self._register_sound("perfect_block")
        self._register_sound("stagger")
    
    def _register_sound_group(self, group_name: str, sound_names: List[str]):
        """Registra um grupo de sons variantes"""
        sounds = []
        for name in sound_names:
            full_name = f"{group_name}_{name}" if not name.startswith(group_name) else name
            sound = self._load_or_generate_sound(full_name)
            if sound:
                sounds.append(sound)
                self.sounds[full_name] = sound
        
        if sounds:
            self.sound_groups[group_name] = sounds
    
    def _register_sound(self, name: str):
        """Registra um som individual"""
        sound = self._load_or_generate_sound(name)
        if sound:
            self.sounds[name] = sound
    
    def _load_or_generate_sound(self, name: str) -> Optional[pygame.mixer.Sound]:
        """Carrega som do disco ou gera proceduralmente"""
        if not self.enabled:
            return None
        
        # Tenta carregar arquivo
        for ext in ['.wav', '.ogg', '.mp3']:
            filepath = os.path.join(self.sound_dir, f"{name}{ext}")
            if os.path.exists(filepath):
                try:
                    return pygame.mixer.Sound(filepath)
                except:
                    pass
        
        # Gera som procedural (silencioso por padrão)
        # Em produção, você substituiria por sons reais
        return self._generate_procedural_sound(name)
    
    def _generate_procedural_sound(self, name: str) -> Optional[pygame.mixer.Sound]:
        """
        Gera sons procedurais simples.
        Nota: Sons reais melhoram muito a experiência!
        """
        try:
            import numpy as np
            
            sample_rate = 44100
            duration = 0.1  # 100ms padrão
            
            # Diferentes perfis de som baseados no nome
            if "punch" in name or "kick" in name or "impact" in name:
                # Som de impacto: onda curta com decay rápido
                duration = 0.08
                freq = random.randint(80, 150)
                t = np.linspace(0, duration, int(sample_rate * duration))
                wave = np.sin(2 * np.pi * freq * t)
                # Envelope de decay exponencial
                envelope = np.exp(-t * 30)
                wave = wave * envelope
                # Adiciona ruído
                noise = np.random.normal(0, 0.3, len(wave))
                wave = wave * 0.7 + noise * 0.3
            
            elif "slash" in name or "stab" in name:
                # Som de corte: swoosh com freq variável
                duration = 0.12
                t = np.linspace(0, duration, int(sample_rate * duration))
                freq_start = random.randint(200, 400)
                freq_end = random.randint(100, 200)
                freq = np.linspace(freq_start, freq_end, len(t))
                wave = np.sin(2 * np.pi * freq * t)
                envelope = np.exp(-t * 15)
                wave = wave * envelope
            
            elif "fire" in name or "explosion" in name:
                # Som de fogo: ruído filtrado
                duration = 0.15
                wave = np.random.normal(0, 0.5, int(sample_rate * duration))
                # Filtro passa-baixa simples
                for i in range(1, len(wave)):
                    wave[i] = wave[i] * 0.7 + wave[i-1] * 0.3
                t = np.linspace(0, duration, len(wave))
                envelope = np.exp(-t * 10)
                wave = wave * envelope
            
            elif "ice" in name or "frost" in name:
                # Som cristalino
                duration = 0.12
                t = np.linspace(0, duration, int(sample_rate * duration))
                wave = np.sin(2 * np.pi * 2000 * t) + np.sin(2 * np.pi * 3000 * t)
                envelope = np.exp(-t * 20)
                wave = wave * envelope * 0.5
            
            elif "lightning" in name or "electric" in name:
                # Som elétrico: ruído de alta frequência
                duration = 0.1
                wave = np.random.normal(0, 0.6, int(sample_rate * duration))
                t = np.linspace(0, duration, len(wave))
                envelope = 1 - t / duration
                wave = wave * envelope
            
            elif "energy" in name or "beam" in name:
                # Som de energia: tom sustentado
                duration = 0.2
                t = np.linspace(0, duration, int(sample_rate * duration))
                freq = random.randint(300, 600)
                wave = np.sin(2 * np.pi * freq * t)
                # Vibrato
                vibrato = np.sin(2 * np.pi * 5 * t) * 0.1
                wave = wave * (1 + vibrato)
                envelope = 1 - (t / duration) * 0.5
                wave = wave * envelope
            
            elif "dash" in name or "whoosh" in name:
                # Som de movimento rápido
                duration = 0.15
                t = np.linspace(0, duration, int(sample_rate * duration))
                freq = np.linspace(400, 200, len(t))
                wave = np.sin(2 * np.pi * freq * t)
                noise = np.random.normal(0, 0.2, len(wave))
                wave = wave * 0.6 + noise * 0.4
                envelope = 1 - t / duration
                wave = wave * envelope
            
            elif "shield" in name or "block" in name:
                # Som metálico
                duration = 0.1
                t = np.linspace(0, duration, int(sample_rate * duration))
                wave = (np.sin(2 * np.pi * 800 * t) + 
                       np.sin(2 * np.pi * 1200 * t) +
                       np.sin(2 * np.pi * 1600 * t))
                envelope = np.exp(-t * 25)
                wave = wave * envelope * 0.4
            
            elif "heal" in name or "buff" in name:
                # Som mágico positivo
                duration = 0.2
                t = np.linspace(0, duration, int(sample_rate * duration))
                wave = (np.sin(2 * np.pi * 440 * t) + 
                       np.sin(2 * np.pi * 550 * t) +
                       np.sin(2 * np.pi * 660 * t))
                envelope = 1 - (t / duration) * 0.3
                wave = wave * envelope * 0.3
            
            else:
                # Som genérico
                duration = 0.1
                t = np.linspace(0, duration, int(sample_rate * duration))
                wave = np.sin(2 * np.pi * 440 * t)
                envelope = np.exp(-t * 20)
                wave = wave * envelope * 0.5
            
            # Normaliza e converte para int16
            wave = wave / np.max(np.abs(wave)) * 0.7  # Limita a 70% do volume máximo
            wave = (wave * 32767).astype(np.int16)
            
            # Cria som estéreo
            stereo_wave = np.column_stack((wave, wave))
            
            # Cria Sound do pygame
            sound = pygame.sndarray.make_sound(stereo_wave)
            return sound
            
        except ImportError:
            # numpy não disponível, retorna som silencioso
            return None
        except Exception as e:
            print(f"Erro ao gerar som procedural '{name}': {e}")
            return None
    
    # =========================================================================
    # API PÚBLICA
    # =========================================================================
    
    def play(self, sound_name: str, volume: float = 1.0, pan: float = 0.0):
        """
        Toca um som.
        
        Args:
            sound_name: Nome do som ou grupo
            volume: Volume (0.0 a 1.0)
            pan: Panorâmica (-1.0 esquerda, 0.0 centro, 1.0 direita)
        """
        if not self.enabled or not sound_name:
            return
        
        # Tenta tocar do grupo primeiro (variação aleatória)
        if sound_name in self.sound_groups:
            sounds = self.sound_groups[sound_name]
            sound = random.choice(sounds)
        elif sound_name in self.sounds:
            sound = self.sounds[sound_name]
        else:
            return
        
        if sound:
            final_volume = volume * self.sfx_volume * self.master_volume
            
            # Aplica volume e pan
            if pan != 0.0:
                # Pan: -1 (esquerda) a 1 (direita)
                left = final_volume * (1 - max(0, pan))
                right = final_volume * (1 + min(0, pan))
                sound.set_volume(min(1.0, left + right))
            else:
                sound.set_volume(final_volume)
            
            sound.play()
    
    def play_positional(self, sound_name: str, pos_x: float, listener_x: float, 
                       max_distance: float = 20.0, volume: float = 1.0):
        """
        Toca som com posicionamento espacial baseado na distância e pan.
        
        Args:
            sound_name: Nome do som
            pos_x: Posição X da fonte do som
            listener_x: Posição X do ouvinte (câmera)
            max_distance: Distância máxima de audição
            volume: Volume base
        """
        if not self.enabled:
            return
        
        # Calcula distância
        distance = abs(pos_x - listener_x)
        
        # Atenuação por distância
        if distance > max_distance:
            return  # Muito longe
        
        distance_volume = 1.0 - (distance / max_distance)
        
        # Pan baseado na posição
        pan = (pos_x - listener_x) / max_distance
        pan = max(-1.0, min(1.0, pan))  # Clamp
        
        self.play(sound_name, volume * distance_volume, pan)
    
    def play_attack(self, attack_type: str, pos_x: float = 0, listener_x: float = 0):
        """Toca som de ataque baseado no tipo"""
        sound_map = {
            "SOCO": "punch",
            "CHUTE": "kick",
            "ESPADADA": "slash",
            "MACHADADA": "slash",
            "FACADA": "stab",
            "ARCO": "energy",  # Som de arco
            "MAGIA": "energy",
        }
        
        sound = sound_map.get(attack_type, "punch")
        if pos_x != 0:
            self.play_positional(sound, pos_x, listener_x, volume=0.7)
        else:
            self.play(sound, volume=0.7)
    
    def play_impact(self, damage: float, pos_x: float = 0, listener_x: float = 0, 
                   is_critical: bool = False, is_counter: bool = False):
        """Toca som de impacto baseado no dano"""
        if is_counter:
            sound = "counter_hit"
            volume = 1.0
        elif is_critical:
            sound = "impact_critical"
            volume = 0.9
        elif damage > 50:
            sound = "impact_heavy"
            volume = 0.8
        else:
            sound = "impact"
            volume = 0.6
        
        if pos_x != 0:
            self.play_positional(sound, pos_x, listener_x, volume=volume)
        else:
            self.play(sound, volume=volume)
    
    def play_skill(self, skill_type: str, skill_name: str = "", 
                   pos_x: float = 0, listener_x: float = 0, phase: str = "cast"):
        """
        Toca som de skill baseado no tipo.
        
        Args:
            skill_type: PROJETIL, BEAM, AREA, DASH, BUFF, etc
            skill_name: Nome da skill (para sons específicos)
            pos_x: Posição X
            listener_x: Posição do ouvinte
            phase: "cast", "fly", "impact", "active"
        """
        sound = None
        volume = 0.7
        
        # Mapeia tipo de skill para som
        if skill_type == "PROJETIL":
            if "fogo" in skill_name.lower() or "fire" in skill_name.lower():
                sound = f"fireball_{phase}" if phase in ["cast", "fly", "impact"] else "fireball_cast"
            elif "gelo" in skill_name.lower() or "ice" in skill_name.lower():
                sound = f"ice_{phase}" if phase in ["cast", "impact"] else "ice_cast"
            elif "raio" in skill_name.lower() or "lightning" in skill_name.lower():
                sound = f"lightning_{phase}" if phase in ["charge", "bolt", "impact"] else "lightning_bolt"
            else:
                sound = f"energy_{phase}" if phase in ["charge", "blast", "impact"] else "energy_blast"
        
        elif skill_type == "BEAM":
            if phase == "cast":
                sound = "beam_charge"
            elif phase == "active":
                sound = "beam_fire"
            else:
                sound = "beam_end"
        
        elif skill_type == "AREA":
            if "fogo" in skill_name.lower():
                sound = "fireball_impact"
                volume = 1.0
            elif "gelo" in skill_name.lower():
                sound = "ice_impact"
            else:
                sound = "energy_impact"
                volume = 0.9
        
        elif skill_type == "DASH":
            if phase == "cast":
                sound = "dash_whoosh"
            else:
                sound = "dash_impact"
        
        elif skill_type == "BUFF":
            if "cura" in skill_name.lower() or "heal" in skill_name.lower():
                sound = "heal_cast" if phase == "cast" else "heal_complete"
            elif "escudo" in skill_name.lower() or "shield" in skill_name.lower():
                sound = "shield_up"
            else:
                sound = "buff_activate"
        
        elif skill_type == "TELEPORT":
            sound = "teleport_out" if phase == "cast" else "teleport_in"
        
        if sound:
            if pos_x != 0:
                self.play_positional(sound, pos_x, listener_x, volume=volume)
            else:
                self.play(sound, volume=volume)
    
    def play_movement(self, movement_type: str, pos_x: float = 0, listener_x: float = 0):
        """Toca som de movimento"""
        sound_map = {
            "jump": "jump_start",
            "land": "jump_land",
            "dodge": "dodge_whoosh",
            "footstep": "footstep",
        }
        
        sound = sound_map.get(movement_type)
        if sound:
            volume = 0.3 if movement_type == "footstep" else 0.5
            if pos_x != 0:
                self.play_positional(sound, pos_x, listener_x, volume=volume)
            else:
                self.play(sound, volume=volume)
    
    def play_special(self, event_type: str, volume: float = 0.8):
        """Toca sons de eventos especiais"""
        special_sounds = {
            "ko": "ko_impact",
            "combo": "combo_hit",
            "perfect_block": "perfect_block",
            "stagger": "stagger",
            "wall_hit": "wall_hit",
            "ground_slam": "ground_slam",
        }
        
        sound = special_sounds.get(event_type)
        if sound:
            self.play(sound, volume=volume)
    
    def play_ui(self, ui_action: str):
        """Toca sons de UI"""
        sound_map = {
            "select": "ui_select",
            "confirm": "ui_confirm",
            "back": "ui_back",
        }
        
        sound = sound_map.get(ui_action)
        if sound:
            self.play(sound, volume=0.5)
    
    def set_master_volume(self, volume: float):
        """Define volume mestre (0.0 a 1.0)"""
        self.master_volume = max(0.0, min(1.0, volume))
    
    def set_sfx_volume(self, volume: float):
        """Define volume de efeitos sonoros (0.0 a 1.0)"""
        self.sfx_volume = max(0.0, min(1.0, volume))
    
    def stop_all(self):
        """Para todos os sons"""
        if self.enabled:
            pygame.mixer.stop()
    
    def toggle_enable(self):
        """Liga/desliga áudio"""
        self.enabled = not self.enabled
        if not self.enabled:
            self.stop_all()


# Atalhos globais
def play_sound(sound_name: str, volume: float = 1.0):
    """Atalho para tocar som"""
    AudioManager.get_instance().play(sound_name, volume)

def play_attack_sound(attack_type: str, pos_x: float = 0, listener_x: float = 0):
    """Atalho para som de ataque"""
    AudioManager.get_instance().play_attack(attack_type, pos_x, listener_x)

def play_impact_sound(damage: float, pos_x: float = 0, listener_x: float = 0, 
                     is_critical: bool = False, is_counter: bool = False):
    """Atalho para som de impacto"""
    AudioManager.get_instance().play_impact(damage, pos_x, listener_x, is_critical, is_counter)

def play_skill_sound(skill_type: str, skill_name: str = "", 
                    pos_x: float = 0, listener_x: float = 0, phase: str = "cast"):
    """Atalho para som de skill"""
    AudioManager.get_instance().play_skill(skill_type, skill_name, pos_x, listener_x, phase)
