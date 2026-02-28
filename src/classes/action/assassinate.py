from __future__ import annotations
from typing import TYPE_CHECKING
import random

from src.i18n import t
from src.classes.action import InstantAction
from src.classes.action.cooldown import cooldown_action
from src.classes.action.targeting_mixin import TargetingMixin
from src.classes.event import Event
from src.systems.battle import decide_battle, get_assassination_success_rate
from src.classes.story_teller import StoryTeller
from src.classes.death import handle_death
from src.classes.death_reason import DeathReason, DeathType
from src.classes.kill_and_grab import kill_and_grab

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


@cooldown_action
class Assassinate(InstantAction, TargetingMixin):
    # ID Đa ngôn ngữ
    ACTION_NAME_ID = "assassinate_action_name"
    DESC_ID = "assassinate_description"
    REQUIREMENTS_ID = "assassinate_requirements"
    
    # Các hằng số không cần dịch
    EMOJI = "🗡️"
    PARAMS = {"avatar_name": "AvatarName"}
    ACTION_CD_MONTHS = 12
    
    # ID gợi ý kể chuyện (LLM Prompt)
    STORY_PROMPT_SUCCESS_ID = "assassinate_story_prompt_success"
    STORY_PROMPT_FAIL_ID = "assassinate_story_prompt_fail"
    
    # Ám sát là đại sự (ghi nhớ dài hạn)
    IS_MAJOR: bool = True
    
    @classmethod
    def get_story_prompt_success(cls) -> str:
        """Lấy gợi ý kể chuyện khi thành công đã dịch"""
        return t(cls.STORY_PROMPT_SUCCESS_ID)
    
    @classmethod
    def get_story_prompt_fail(cls) -> str:
        """Lấy gợi ý kể chuyện khi thất bại đã dịch"""
        return t(cls.STORY_PROMPT_FAIL_ID)

    def _execute(self, avatar_name: str) -> None:
        """
        Thực hiện ám sát
        """
        target = self.find_avatar_by_name(avatar_name)
        if target is None:
            return
            
        # Phán định ám sát có thành công hay không
        success_rate = get_assassination_success_rate(self.avatar, target)
        is_success = random.random() < success_rate
        
        self._is_assassinate_success = is_success
        
        if is_success:
            # Ám sát thành công, mục tiêu tử vong ngay lập tức
            target.hp.current = 0
            self._last_result = None # Không cần kết quả chiến đấu
        else:
            # Ám sát thất bại, chuyển sang chiến đấu thông thường
            winner, loser, loser_damage, winner_damage = decide_battle(self.avatar, target)
            # Áp dụng sát thương cho cả hai bên
            loser.hp.reduce(loser_damage)
            winner.hp.reduce(winner_damage)
            
            # Tăng độ thuần thục binh khí (vì đã nổ ra chiến đấu)
            proficiency_gain = random.uniform(1.0, 3.0)
            self.avatar.increase_weapon_proficiency(proficiency_gain)
            target.increase_weapon_proficiency(proficiency_gain)
            
            self._last_result = (winner, loser, loser_damage, winner_damage)

    def can_start(self, avatar_name: str) -> tuple[bool, str]:
        # Lưu ý: Decorator cooldown_action sẽ ghi đè phương thức này và kiểm tra CD trước khi gọi phương thức này
        _, ok, reason = self.validate_target_avatar(avatar_name)
        return ok, reason

    def start(self, avatar_name: str) -> Event:
        target = self.find_avatar_by_name(avatar_name)
        target_name = target.name if target is not None else avatar_name
        
        content = t("{avatar} lurks in the shadows, attempting to assassinate {target}...", 
                   avatar=self.avatar.name, target=target_name)
        event = Event(self.world.month_stamp, content, related_avatars=[self.avatar.id, target.id] if target else [self.avatar.id], is_major=True)
        self._start_event_content = event.content
        return event

    async def finish(self, avatar_name: str) -> list[Event]:
        target = self.find_avatar_by_name(avatar_name)
        if target is None:
            return []
            
        rel_ids = [self.avatar.id, target.id]
        
        if getattr(self, '_is_assassinate_success', False):
            # --- Ám sát thành công ---
            result_text = t("{avatar} assassinated successfully! {target} fell without any defense.",
                           avatar=self.avatar.name, target=target.name)
            
            # Giết người đoạt bảo (Kill and Grab)
            loot_text = await kill_and_grab(self.avatar, target)
            result_text += loot_text
            
            result_event = Event(self.world.month_stamp, result_text, related_avatars=rel_ids, is_major=True)
            
            # Tạo cốt truyện
            story = await StoryTeller.tell_story(
                self._start_event_content, 
                result_event.content, 
                self.avatar, 
                target, 
                prompt=self.get_story_prompt_success(),
                allow_relation_changes=True
            )
            story_event = Event(self.world.month_stamp, story, related_avatars=rel_ids, is_story=True)
            
            # Xử lý tử vong và dọn dẹp
            handle_death(self.world, target, DeathReason(DeathType.BATTLE, killer_name=self.avatar.name))
            
            return [result_event, story_event]
            
        else:
            # --- Ám sát thất bại, chuyển sang chiến đấu ---
            res = getattr(self, '_last_result', None)
            if not (isinstance(res, tuple) and len(res) == 4):
                return [] 
                
            start_text = getattr(self, '_start_event_content', "")
            
            from src.systems.battle import handle_battle_finish
            return await handle_battle_finish(
                self.world,
                self.avatar,
                target,
                res,
                start_text,
                self.get_story_prompt_fail(),
                prefix=t("Assassination failed! Both sides engaged in fierce battle."),
                check_loot=True
            )
