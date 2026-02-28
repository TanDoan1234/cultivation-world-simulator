from __future__ import annotations
from typing import TYPE_CHECKING

from src.i18n import t
from src.classes.action import InstantAction
from src.classes.action.targeting_mixin import TargetingMixin
from src.classes.event import Event
from src.systems.battle import decide_battle, get_effective_strength_pair
from src.utils.resolution import resolve_query

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

class Attack(InstantAction, TargetingMixin):
    # ID Đa ngôn ngữ
    ACTION_NAME_ID = "attack_action_name"
    DESC_ID = "attack_description"
    REQUIREMENTS_ID = "attack_requirements"
    STORY_PROMPT_ID = "attack_story_prompt"
    
    # Các hằng số không cần dịch
    EMOJI = "⚔️"
    PARAMS = {"avatar_name": "AvatarName"}
    
    # Chiến đấu là đại sự (ghi nhớ dài hạn)
    IS_MAJOR: bool = True
    
    @classmethod
    def get_story_prompt(cls) -> str:
        """Lấy gợi ý kể chuyện đã dịch"""
        return t(cls.STORY_PROMPT_ID)

    def _execute(self, avatar_name: str) -> None:
        """
        Thực hiện tấn công
        """
        from src.classes.core.avatar import Avatar
        target = resolve_query(avatar_name, self.world, expected_types=[Avatar]).obj
        if target is None:
            return
        winner, loser, loser_damage, winner_damage = decide_battle(self.avatar, target)
        # Áp dụng sát thương cho cả hai bên
        loser.hp.reduce(loser_damage)
        winner.hp.reduce(winner_damage)
        
        # Tăng độ thuần thục binh khí cho cả hai (kinh nghiệm chiến đấu)
        import random
        proficiency_gain = random.uniform(1.0, 3.0)
        self.avatar.increase_weapon_proficiency(proficiency_gain)
        if target is not None:
            target.increase_weapon_proficiency(proficiency_gain)
        
        self._last_result = (winner, loser, loser_damage, winner_damage)

    def can_start(self, avatar_name: str) -> tuple[bool, str]:
        if not avatar_name:
            return False, t("Missing target parameter")
            
        from src.classes.core.avatar import Avatar
        target = resolve_query(avatar_name, self.world, expected_types=[Avatar]).obj
        if target is None:
            return False, t("Target does not exist")
        if target.is_dead:
            return False, t("Target is already dead")
            
        return True, ""

    def start(self, avatar_name: str) -> Event:
        from src.classes.core.avatar import Avatar
        target = resolve_query(avatar_name, self.world, expected_types=[Avatar]).obj
        target_name = target.name if target is not None else avatar_name
        # Hiển thị lực chiến quy đổi của hai bên (dựa trên đối thủ, bao gồm cả khắc chế)
        s_att, s_def = get_effective_strength_pair(self.avatar, target)
        rel_ids = [self.avatar.id]
        if target is not None:
            try:
                rel_ids.append(target.id)
            except Exception:
                pass
        content = t("{attacker} initiates battle against {target} (Power: {attacker} {att_power} vs {target} {def_power})",
                   attacker=self.avatar.name, target=target_name, 
                   att_power=int(s_att), def_power=int(s_def))
        event = Event(self.world.month_stamp, content, related_avatars=rel_ids, is_major=True)
        # Ghi lại nội dung sự kiện bắt đầu để dùng cho việc tạo cốt truyện
        self._start_event_content = event.content
        return event

    # InstantAction đã triển khai xong step

    async def finish(self, avatar_name: str) -> list[Event]:
        res = self._last_result
        if not (isinstance(res, tuple) and len(res) == 4):
            return []
        
        from src.classes.core.avatar import Avatar
        target = resolve_query(avatar_name, self.world, expected_types=[Avatar]).obj
        start_text = getattr(self, '_start_event_content', "")
        
        from src.systems.battle import handle_battle_finish
        return await handle_battle_finish(
            self.world,
            self.avatar,
            target,
            res,
            start_text,
            self.get_story_prompt(),
            check_loot=True
        )
